const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const cp = require('node:child_process');
const test = require('node:test');

const {
  buildIdeProcessSpec,
  buildWorkspaceIdeProcessSpec,
  buildRunEnv,
  resolveWorkspaceFile,
  runJsonProcess,
} = require('../ide-process');

const python = process.platform === 'win32' ? 'python' : 'python3';

function writeModule(root, body) {
  const pkg = path.join(root, 'transpiler');
  fs.mkdirSync(pkg, { recursive: true });
  fs.writeFileSync(path.join(pkg, '__init__.py'), '', 'utf8');
  fs.writeFileSync(path.join(pkg, 'ide.py'), body, 'utf8');
}

test('isolated IDE invocation selects bundled module, not workspace shadow', () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'pys ide isolation '));
  const extensionPath = path.join(temp, 'extension');
  const workspacePath = path.join(temp, 'workspace');
  const marker = path.join(temp, 'workspace-shadow-ran');
  const source = path.join(workspacePath, 'file with spaces.pys');

  writeModule(
    path.join(extensionPath, 'bundled'),
    "import json,sys\nprint(json.dumps({'origin':'bundled','arg':sys.argv[1]}))\n",
  );
  writeModule(
    workspacePath,
    `from pathlib import Path\nPath(${JSON.stringify(marker)}).write_text('ran')\n`,
  );
  fs.writeFileSync(source, 'print(1)\n', 'utf8');

  const spec = buildIdeProcessSpec(
    extensionPath,
    workspacePath,
    [source],
    { ...process.env, PYTHONPATH: workspacePath, PYTHONHOME: workspacePath },
  );
  const result = cp.spawnSync(python, spec.args, {
    ...spec.options,
    encoding: 'utf8',
  });

  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(JSON.parse(result.stdout.trim()), {
    origin: 'bundled',
    arg: source,
  });
  assert.equal(fs.existsSync(marker), false);
  assert.equal(spec.options.cwd, extensionPath);
  assert.equal(spec.options.env.PYTHONPATH, undefined);
  assert.equal(spec.options.env.PYTHONHOME, undefined);
  assert.equal(spec.options.env.PYS_WORKSPACE_ROOT, path.resolve(workspacePath));
});

test('IDE arguments remain separate argv values', () => {
  const spec = buildIdeProcessSpec(
    'C:\\trusted extension',
    'C:\\workspace',
    ['C:\\workspace\\file with spaces.pys', 'Thing.method'],
    {},
  );

  assert.equal(spec.args[0], '-I');
  assert.equal(spec.args.at(-2), 'C:\\workspace\\file with spaces.pys');
  assert.equal(spec.args.at(-1), 'Thing.method');
});

test('Run and Debug environment carries the workspace dependency boundary', () => {
  const env = buildRunEnv(
    'C:\\extension\\bundled',
    'C:\\workspace',
    { PATH: 'safe', PYTHONPATH: 'existing' },
  );

  assert.equal(env.PYS_WORKSPACE_ROOT, path.resolve('C:\\workspace'));
  assert.equal(
    env.PYTHONPATH,
    `C:\\extension\\bundled${path.delimiter}existing`,
  );
});

test('workspace file containment accepts nested files and rejects lexical escapes', () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'pys containment '));
  const workspace = path.join(temp, 'workspace');
  const nested = path.join(workspace, 'src', 'main.pys');
  const outside = path.join(temp, 'outside.pys');
  fs.mkdirSync(path.dirname(nested), { recursive: true });
  fs.writeFileSync(nested, 'print(1)\n');
  fs.writeFileSync(outside, 'print(2)\n');

  assert.equal(resolveWorkspaceFile(workspace, nested), fs.realpathSync.native(nested));
  const spec = buildWorkspaceIdeProcessSpec(
    path.join(temp, 'extension'),
    workspace,
    nested,
  );
  assert.equal(spec.args.at(-1), fs.realpathSync.native(nested));
  assert.equal(resolveWorkspaceFile(workspace, outside), null);
  assert.equal(resolveWorkspaceFile(workspace, path.join(workspace, '..', 'outside.pys')), null);
  assert.equal(resolveWorkspaceFile(workspace, path.join(workspace, 'missing.pys')), null);
});

test('workspace file containment rejects symlink or junction escapes', (t) => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'pys link containment '));
  const workspace = path.join(temp, 'workspace');
  const outsideDir = path.join(temp, 'outside');
  const outside = path.join(outsideDir, 'outside.pys');
  fs.mkdirSync(workspace);
  fs.mkdirSync(outsideDir);
  fs.writeFileSync(outside, 'print(2)\n');

  const linkedDir = path.join(workspace, 'linked');
  try {
    fs.symlinkSync(
      outsideDir,
      linkedDir,
      process.platform === 'win32' ? 'junction' : 'dir',
    );
  } catch (error) {
    t.skip(`symlinks unavailable: ${error.message}`);
    return;
  }
  assert.equal(resolveWorkspaceFile(workspace, path.join(linkedDir, 'outside.pys')), null);
  assert.equal(
    buildWorkspaceIdeProcessSpec(
      path.join(temp, 'extension'),
      workspace,
      path.join(linkedDir, 'outside.pys'),
    ),
    null,
  );
});

test('Windows containment is case-insensitive through realpath', {
  skip: process.platform !== 'win32',
}, () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'pys case containment '));
  const workspace = path.join(temp, 'Workspace');
  const source = path.join(workspace, 'main.pys');
  fs.mkdirSync(workspace);
  fs.writeFileSync(source, 'print(1)\n');
  assert.equal(
    resolveWorkspaceFile(workspace.toUpperCase(), source.toLowerCase()),
    fs.realpathSync.native(source),
  );
});

function runNodeFixture(source, settings = {}) {
  return runJsonProcess(
    process.execPath,
    ['-e', source],
    { cwd: os.tmpdir(), env: process.env },
    settings,
  );
}

test('bounded helper runner writes settings.stdin to the child', async () => {
  const parsed = await runNodeFixture(
    "let data=''; process.stdin.on('data',c=>data+=c); process.stdin.on('end',()=>process.stdout.write(JSON.stringify({got:data})))",
    { stdin: 'hello-buffer' },
  );
  assert.deepEqual(parsed, { got: 'hello-buffer' });
});

test('bounded helper runner parses exactly one JSON document', async () => {
  const parsed = await runNodeFixture(
    "process.stderr.write('note'); process.stdout.write(JSON.stringify({ok:true,value:42}))",
  );
  assert.deepEqual(parsed, { ok: true, value: 42 });

  await assert.rejects(
    runNodeFixture("process.stdout.write('{} trailing')"),
    (error) => error.code === 'INVALID_JSON',
  );
});

test('bounded helper runner times out and caps output', async () => {
  await assert.rejects(
    runNodeFixture('setInterval(() => {}, 1000)', { timeoutMs: 100 }),
    (error) => error.code === 'TIMEOUT',
  );
  await assert.rejects(
    runNodeFixture("process.stdout.write('x'.repeat(4096)); setInterval(() => {}, 1000)", {
      maxOutputBytes: 1024,
      timeoutMs: 1000,
    }),
    (error) => error.code === 'OUTPUT_LIMIT',
  );
});

test('bounded helper runner cancels stale requests', async () => {
  const controller = new AbortController();
  const stale = runNodeFixture('setInterval(() => {}, 1000)', {
    signal: controller.signal,
    timeoutMs: 2000,
  });
  controller.abort();
  await assert.rejects(stale, (error) => error.code === 'CANCELLED');

  const latest = await runNodeFixture("process.stdout.write('{\"version\":2}')");
  assert.deepEqual(latest, { version: 2 });
});

test('timeout terminates a spawned grandchild process tree', {
  timeout: 5000,
}, async () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'pys helper tree '));
  const pidFile = path.join(temp, 'grandchild.pid');
  const source = [
    "const cp=require('child_process'),fs=require('fs')",
    `const child=cp.spawn(process.execPath,['-e','setInterval(()=>{},1000)'],{stdio:'ignore'})`,
    `fs.writeFileSync(${JSON.stringify(pidFile)},String(child.pid))`,
    'setInterval(()=>{},1000)',
  ].join(';');

  await assert.rejects(
    runNodeFixture(source, { timeoutMs: 300 }),
    (error) => error.code === 'TIMEOUT',
  );
  const pid = Number(fs.readFileSync(pidFile, 'utf8'));
  let alive = true;
  for (let attempt = 0; attempt < 20 && alive; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 50));
    try {
      process.kill(pid, 0);
    } catch (_error) {
      alive = false;
    }
  }
  assert.equal(alive, false, `grandchild ${pid} survived helper timeout`);
});
