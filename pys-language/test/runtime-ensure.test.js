'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const {
  STABLE_NODE_VERSIONS,
  STABLE_PYTHON_VERSIONS,
  installPlan,
  probeCommand,
  probeNode,
  probePython,
  resolveToolchainNeeds,
  stableVersionsFor,
  terminalInstallLine,
} = require('../runtime-ensure');

test('resolveToolchainNeeds always requires python; node only for javascript', () => {
  assert.deepEqual(resolveToolchainNeeds('python'), { python: true, node: false });
  assert.deepEqual(resolveToolchainNeeds('javascript'), { python: true, node: true });
  assert.deepEqual(resolveToolchainNeeds(''), { python: true, node: false });
});

test('stable version catalogs expose curated ids', () => {
  assert.ok(STABLE_PYTHON_VERSIONS.some((v) => v.id === '3.12'));
  assert.ok(STABLE_NODE_VERSIONS.some((v) => v.id === '20'));
  assert.equal(stableVersionsFor('python'), STABLE_PYTHON_VERSIONS);
  assert.equal(stableVersionsFor('node'), STABLE_NODE_VERSIONS);
});

test('probeCommand returns first successful absolute path on Windows', () => {
  const calls = [];
  const spawnSync = (cmd, args) => {
    calls.push([cmd, ...args]);
    if (cmd === 'where' && args[0] === 'python3') {
      return { status: 0, stdout: 'C:\\Python\\python3.exe\n' };
    }
    return { status: 1, stdout: '' };
  };
  assert.equal(
    probeCommand(['python', 'python3'], { spawnSync, platform: 'win32' }),
    'C:\\Python\\python3.exe',
  );
  assert.deepEqual(calls[0], ['where', 'python']);
  assert.deepEqual(calls[1], ['where', 'python3']);
});

test('probeCommand skips WindowsApps Store stub', () => {
  const spawnSync = (cmd, args) => {
    if (cmd === 'where' && args[0] === 'python') {
      return {
        status: 0,
        stdout:
          'C:\\Users\\me\\AppData\\Local\\Microsoft\\WindowsApps\\python.exe\r\n'
          + 'C:\\Users\\me\\AppData\\Local\\Programs\\Python\\Python311\\python.exe\r\n',
      };
    }
    return { status: 1, stdout: '' };
  };
  assert.equal(
    probeCommand(['python'], { spawnSync, platform: 'win32' }),
    'C:\\Users\\me\\AppData\\Local\\Programs\\Python\\Python311\\python.exe',
  );
});

test('probePython / probeNode order by platform', () => {
  const seen = [];
  const spawnSync = (cmd, args) => {
    seen.push(args[0]);
    return { status: 1, stdout: '' };
  };
  assert.equal(probePython({ spawnSync, platform: 'win32' }), null);
  assert.deepEqual(seen, ['python', 'python3', 'py']);
  seen.length = 0;
  assert.equal(probeNode({ spawnSync, platform: 'linux' }), null);
  assert.deepEqual(seen, ['node']);
});

test('installPlan uses winget on Windows and brew when available on macOS', () => {
  const win = installPlan('python', '3.12', 'win32');
  assert.equal(win.mode, 'winget');
  assert.match(win.command, /winget install.*Python\.Python\.3\.12/);

  const brew = installPlan('node', '22', 'darwin', { brewAvailable: true });
  assert.equal(brew.mode, 'brew');
  assert.match(brew.command, /brew install node@22/);

  const noBrew = installPlan('node', '22', 'darwin', { brewAvailable: false });
  assert.equal(noBrew.mode, 'docs');
  assert.equal(noBrew.command, null);

  const linux = installPlan('python', '3.11', 'linux');
  assert.equal(linux.mode, 'docs');
  assert.match(linux.hint, /apt install python3/);
});

test('terminalInstallLine prefers command then platform openers', () => {
  assert.equal(
    terminalInstallLine({ mode: 'winget', command: 'winget install X', docsUrl: 'https://x', hint: '' }),
    'winget install X',
  );
  assert.match(
    terminalInstallLine(
      { mode: 'docs', command: null, docsUrl: 'https://nodejs.org', hint: 'go' },
      'win32',
    ),
    /start .*nodejs\.org/,
  );
});
