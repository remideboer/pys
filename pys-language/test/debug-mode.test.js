const test = require('node:test');
const assert = require('node:assert/strict');

const {
  PYS_DEBUG_SESSION_NAME,
  PYTHON_DEBUG_SESSION_NAME,
  JS_DEBUG_SESSION_NAME,
  debugModeOptions,
  isPysDebugSession,
} = require('../debug-mode');

test('default debug mode stays in mapped PYS code', () => {
  assert.deepEqual(debugModeOptions(), {
    mode: 'pys',
    sessionName: PYS_DEBUG_SESSION_NAME,
    justMyCode: true,
    stopOnEntry: false,
    remapSource: true,
    revealGenerated: false,
    pysOnlyStepping: true,
  });
});

test('transpiled Python mode reveals internals and stops on entry', () => {
  assert.deepEqual(debugModeOptions('python'), {
    mode: 'python',
    sessionName: PYTHON_DEBUG_SESSION_NAME,
    justMyCode: false,
    stopOnEntry: true,
    remapSource: false,
    revealGenerated: true,
    pysOnlyStepping: false,
  });
});

test('both PYS debugger session names are recognized', () => {
  assert.equal(isPysDebugSession(PYS_DEBUG_SESSION_NAME), true);
  assert.equal(isPysDebugSession(PYTHON_DEBUG_SESSION_NAME), true);
  assert.equal(isPysDebugSession(JS_DEBUG_SESSION_NAME), true);
  assert.equal(isPysDebugSession('Python: Current File'), false);
});

test('transpiled JavaScript advanced mode uses JS session name', () => {
  assert.deepEqual(debugModeOptions('python', 'javascript'), {
    mode: 'python',
    sessionName: JS_DEBUG_SESSION_NAME,
    justMyCode: false,
    stopOnEntry: true,
    remapSource: false,
    revealGenerated: true,
    pysOnlyStepping: false,
  });
});

test('extension manifest contributes the explicit Python-depth command', () => {
  const manifest = require('../package.json');
  const commands = new Set(manifest.contributes.commands.map((item) => item.command));
  assert.equal(commands.has('pys.debugTranspiledFile'), true);
  assert.equal(
    manifest.activationEvents.includes('onCommand:pys.debugTranspiledFile'),
    true,
  );
  const editorCommands = new Set(
    manifest.contributes.menus['editor/context'].map((item) => item.command),
  );
  assert.equal(editorCommands.has('pys.debugTranspiledFile'), true);
});

test('extension manifest contributes the session-local PYS stepping toolbar toggle', () => {
  const manifest = require('../package.json');
  const commands = new Set(manifest.contributes.commands.map((item) => item.command));
  assert.equal(commands.has('pys.enablePysOnlyStepping'), true);
  assert.equal(commands.has('pys.disablePysOnlyStepping'), true);
  assert.equal(
    manifest.activationEvents.includes('onCommand:pys.enablePysOnlyStepping'),
    true,
  );
  assert.equal(
    manifest.activationEvents.includes('onCommand:pys.disablePysOnlyStepping'),
    true,
  );

  const toolbar = manifest.contributes.menus['debug/toolBar'];
  const enable = toolbar.find(
    (item) => item.command === 'pys.enablePysOnlyStepping',
  );
  const disable = toolbar.find(
    (item) => item.command === 'pys.disablePysOnlyStepping',
  );
  assert.match(enable.when, /pys\.debugSessionActive/);
  assert.match(enable.when, /!pys\.debug\.pysOnlyStepping/);
  assert.match(disable.when, /pys\.debugSessionActive/);
  assert.match(disable.when, /pys\.debug\.pysOnlyStepping/);
});
