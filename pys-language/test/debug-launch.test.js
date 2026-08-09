const test = require('node:test');
const assert = require('node:assert/strict');
const {
  buildLaunchConfig,
  buildNodeLaunchConfig,
  buildPythonLaunchConfig,
  debugAdapterTypes,
  NODE_ADAPTER,
  PYTHON_ADAPTER,
} = require('../debug-launch');

const debugModePys = {
  sessionName: 'Debug PYS',
  justMyCode: true,
  stopOnEntry: false,
};

const debugModeAdvanced = {
  sessionName: 'Debug PYS (Transpiled JavaScript)',
  justMyCode: false,
  stopOnEntry: true,
};

test('debugAdapterTypes lists python and pwa-node', () => {
  assert.deepEqual(debugAdapterTypes(), [PYTHON_ADAPTER, NODE_ADAPTER]);
});

test('buildPythonLaunchConfig uses debugpy fields', () => {
  const cfg = buildPythonLaunchConfig({
    prepared: {
      main: 'C:\\tmp\\demo.py',
      cwd: 'C:\\ws',
      python: 'C:\\Python\\python.exe',
    },
    debugMode: debugModePys,
    runEnv: { FOO: '1' },
    cwd: 'C:\\ws',
  });
  assert.equal(cfg.type, 'python');
  assert.equal(cfg.program, 'C:\\tmp\\demo.py');
  assert.equal(cfg.python, 'C:\\Python\\python.exe');
  assert.equal(cfg.justMyCode, true);
});

test('buildNodeLaunchConfig uses pwa-node and runtimeExecutable', () => {
  const cfg = buildNodeLaunchConfig({
    prepared: {
      main: 'C:\\tmp\\demo.mjs',
      cwd: 'C:\\ws',
      runtimeExecutable: 'C:\\nodejs\\node.exe',
    },
    debugMode: debugModePys,
    runEnv: {},
    cwd: 'C:\\ws',
  });
  assert.equal(cfg.type, 'pwa-node');
  assert.equal(cfg.program, 'C:\\tmp\\demo.mjs');
  assert.equal(cfg.runtimeExecutable, 'C:\\nodejs\\node.exe');
  assert.ok(cfg.skipFiles.length > 0);
});

test('buildLaunchConfig picks adapter from prepared.target', () => {
  const py = buildLaunchConfig({
    prepared: { target: 'python', main: 'a.py', python: 'py' },
    debugMode: debugModePys,
    runEnv: {},
    cwd: '.',
  });
  assert.equal(py.type, 'python');

  const js = buildLaunchConfig({
    prepared: {
      target: 'javascript',
      main: 'a.mjs',
      runtimeExecutable: 'node',
    },
    debugMode: debugModeAdvanced,
    runEnv: {},
    cwd: '.',
  });
  assert.equal(js.type, 'pwa-node');
  assert.equal(js.stopOnEntry, true);
  assert.deepEqual(js.skipFiles, []);
});
