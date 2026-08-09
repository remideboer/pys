/**
 * Thin launch adapters for PYS debug sessions.
 *
 * Shared prepare_debug JSON + MapRegistry stay target-neutral; only the
 * VS Code launch config differs (debugpy vs js-debug / pwa-node).
 */
'use strict';

const PYTHON_ADAPTER = 'python';
const NODE_ADAPTER = 'pwa-node';

function debugAdapterTypes() {
  return [PYTHON_ADAPTER, NODE_ADAPTER];
}

/**
 * @param {{
 *   prepared: object,
 *   debugMode: object,
 *   runEnv: object,
 *   cwd: string,
 * }} opts
 */
function buildPythonLaunchConfig(opts) {
  const { prepared, debugMode, runEnv, cwd } = opts;
  const launchConfig = {
    name: debugMode.sessionName,
    type: PYTHON_ADAPTER,
    request: 'launch',
    program: prepared.main,
    cwd: prepared.cwd || cwd,
    env: runEnv,
    console: 'integratedTerminal',
    justMyCode: debugMode.justMyCode,
    stopOnEntry: debugMode.stopOnEntry,
  };
  if (prepared.python) {
    launchConfig.python = prepared.python;
  }
  return launchConfig;
}

/**
 * @param {{
 *   prepared: object,
 *   debugMode: object,
 *   runEnv: object,
 *   cwd: string,
 * }} opts
 */
function buildNodeLaunchConfig(opts) {
  const { prepared, debugMode, runEnv, cwd } = opts;
  return {
    name: debugMode.sessionName,
    type: NODE_ADAPTER,
    request: 'launch',
    program: prepared.main,
    runtimeExecutable: prepared.runtimeExecutable,
    cwd: prepared.cwd || cwd,
    env: runEnv,
    console: 'integratedTerminal',
    // Approximate justMyCode: skip Node internals + deps when staying in PYS.
    skipFiles: debugMode.justMyCode
      ? ['<node_internals>/**', '**/node_modules/**']
      : [],
    stopOnEntry: debugMode.stopOnEntry,
  };
}

/**
 * Pick adapter from prepare_debug `target` (fallback: emitTarget).
 * @param {{
 *   prepared: object,
 *   debugMode: object,
 *   runEnv: object,
 *   cwd: string,
 *   emitTarget?: string,
 * }} opts
 */
function buildLaunchConfig(opts) {
  const target =
    (opts.prepared && opts.prepared.target) || opts.emitTarget || 'python';
  if (target === 'javascript') {
    return buildNodeLaunchConfig(opts);
  }
  return buildPythonLaunchConfig(opts);
}

module.exports = {
  PYTHON_ADAPTER,
  NODE_ADAPTER,
  debugAdapterTypes,
  buildPythonLaunchConfig,
  buildNodeLaunchConfig,
  buildLaunchConfig,
};
