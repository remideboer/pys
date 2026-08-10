const fs = require('fs');
const path = require('path');
const cp = require('child_process');

const DEFAULT_TIMEOUT_MS = 5_000;
const DEFAULT_MAX_OUTPUT_BYTES = 1024 * 1024;

const IDE_BOOTSTRAP = [
  'import runpy,sys',
  'root=sys.argv.pop(1)',
  'sys.path.insert(0,root)',
  "runpy.run_module('transpiler.ide',run_name='__main__')",
].join(';');

/**
 * Build an isolated Python invocation for automatic IDE analysis.
 *
 * Python's -I flag ignores PYTHONPATH, user site packages, and the current
 * directory. The bootstrap then adds only the extension-owned bundled root.
 */
function buildIdeProcessSpec(extensionPath, workspacePath, ideArgs, baseEnv = process.env) {
  const env = { ...baseEnv };
  delete env.PYTHONPATH;
  delete env.PYTHONHOME;
  env.PYS_WORKSPACE_ROOT = path.resolve(workspacePath);

  return {
    args: [
      '-I',
      '-c',
      IDE_BOOTSTRAP,
      path.join(extensionPath, 'bundled'),
      ...ideArgs,
    ],
    options: {
      cwd: extensionPath,
      env,
    },
  };
}

function buildWorkspaceIdeProcessSpec(
  extensionPath,
  workspacePath,
  sourcePath,
  extraArgs = [],
  baseEnv = process.env,
) {
  const containedSource = resolveWorkspaceFile(workspacePath, sourcePath);
  if (!containedSource) {
    return null;
  }
  return buildIdeProcessSpec(
    extensionPath,
    workspacePath,
    [containedSource, ...extraArgs],
    baseEnv,
  );
}

function buildRunEnv(bundledRoot, workspacePath, baseEnv = process.env) {
  const env = { ...baseEnv };
  const existing = env.PYTHONPATH || '';
  env.PYTHONPATH = existing
    ? `${bundledRoot}${path.delimiter}${existing}`
    : bundledRoot;
  env.PYS_WORKSPACE_ROOT = path.resolve(workspacePath);
  return env;
}

function isPathInside(candidate, root) {
  const relative = path.relative(root, candidate);
  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
}

/**
 * Return the canonical target only when both its lexical and real paths are
 * inside the canonical workspace. Fail closed for missing/broken links.
 */
function resolveWorkspaceFile(workspaceRoot, candidate, fsModule = fs) {
  const lexicalRoot = path.resolve(workspaceRoot);
  const lexicalTarget = path.resolve(candidate);
  if (!isPathInside(lexicalTarget, lexicalRoot)) {
    return null;
  }
  try {
    const realpath = fsModule.realpathSync.native || fsModule.realpathSync;
    const realRoot = realpath(lexicalRoot);
    const realTarget = realpath(lexicalTarget);
    return isPathInside(realTarget, realRoot) ? realTarget : null;
  } catch (_error) {
    return null;
  }
}

function killProcessTree(child) {
  if (!child || !child.pid) {
    return;
  }
  if (process.platform === 'win32') {
    try {
      cp.spawn('taskkill', ['/pid', String(child.pid), '/T', '/F'], {
        stdio: 'ignore',
        windowsHide: true,
      }).unref();
    } catch (_error) {
      child.kill();
    }
    return;
  }
  try {
    process.kill(-child.pid, 'SIGKILL');
  } catch (_error) {
    try {
      child.kill('SIGKILL');
    } catch (_ignored) {
      // Process already exited.
    }
  }
}

function cancellationSubscription(signal, cancel) {
  if (!signal) {
    return { dispose() {} };
  }
  if (signal.aborted || signal.isCancellationRequested) {
    cancel();
    return { dispose() {} };
  }
  if (typeof signal.addEventListener === 'function') {
    signal.addEventListener('abort', cancel, { once: true });
    return {
      dispose() {
        signal.removeEventListener('abort', cancel);
      },
    };
  }
  if (typeof signal.onCancellationRequested === 'function') {
    return signal.onCancellationRequested(cancel);
  }
  return { dispose() {} };
}

function processError(code, message) {
  const error = new Error(message);
  error.code = code;
  return error;
}

/**
 * Run a helper process and parse exactly one bounded JSON document.
 */
function runJsonProcess(command, args, options, settings = {}) {
  const timeoutMs = settings.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const maxOutputBytes = settings.maxOutputBytes ?? DEFAULT_MAX_OUTPUT_BYTES;
  const spawnFn = settings.spawnFn || cp.spawn;
  const killTreeFn = settings.killTreeFn || killProcessTree;
  const spawnOptions = {
    ...options,
    detached: process.platform !== 'win32',
    windowsHide: true,
  };

  return new Promise((resolve, reject) => {
    let settled = false;
    let stdoutBytes = 0;
    let stderrBytes = 0;
    const stdout = [];
    const stderr = [];
    let child;
    let timer;
    let cancellation = { dispose() {} };

    const finish = (error, value, kill = false) => {
      if (settled) {
        return;
      }
      settled = true;
      if (timer) {
        clearTimeout(timer);
      }
      cancellation.dispose();
      if (kill && child) {
        killTreeFn(child);
      }
      if (error) {
        reject(error);
      } else {
        resolve(value);
      }
    };

    try {
      child = spawnFn(command, args, spawnOptions);
    } catch (error) {
      finish(error);
      return;
    }

    if (settings.stdin != null) {
      child.stdin.on('error', () => {});
      child.stdin.end(String(settings.stdin), 'utf8');
    } else {
      child.stdin.end();
    }

    const collect = (chunks, streamName) => (chunk) => {
      const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
      if (streamName === 'stdout') {
        stdoutBytes += buffer.length;
        if (stdoutBytes > maxOutputBytes) {
          finish(
            processError('OUTPUT_LIMIT', `IDE helper stdout exceeded ${maxOutputBytes} bytes.`),
            null,
            true,
          );
          return;
        }
      } else {
        stderrBytes += buffer.length;
        if (stderrBytes > maxOutputBytes) {
          finish(
            processError('OUTPUT_LIMIT', `IDE helper stderr exceeded ${maxOutputBytes} bytes.`),
            null,
            true,
          );
          return;
        }
      }
      chunks.push(buffer);
    };

    child.stdout.on('data', collect(stdout, 'stdout'));
    child.stderr.on('data', collect(stderr, 'stderr'));
    child.on('error', (error) => finish(error));
    child.on('close', () => {
      if (settled) {
        return;
      }
      const text = Buffer.concat(stdout).toString('utf8').trim();
      if (!text) {
        const detail = Buffer.concat(stderr).toString('utf8').trim();
        finish(processError('EMPTY_OUTPUT', detail || 'IDE helper returned no JSON.'));
        return;
      }
      try {
        finish(null, JSON.parse(text));
      } catch (_error) {
        finish(processError('INVALID_JSON', 'IDE helper returned malformed or trailing output.'));
      }
    });

    timer = setTimeout(() => {
      finish(
        processError('TIMEOUT', `IDE helper exceeded ${timeoutMs} ms.`),
        null,
        true,
      );
    }, timeoutMs);
    timer.unref?.();

    cancellation = cancellationSubscription(settings.signal, () => {
      finish(processError('CANCELLED', 'IDE helper cancelled.'), null, true);
    });
  });
}

module.exports = {
  DEFAULT_MAX_OUTPUT_BYTES,
  DEFAULT_TIMEOUT_MS,
  IDE_BOOTSTRAP,
  buildIdeProcessSpec,
  buildWorkspaceIdeProcessSpec,
  buildRunEnv,
  isPathInside,
  killProcessTree,
  resolveWorkspaceFile,
  runJsonProcess,
};
