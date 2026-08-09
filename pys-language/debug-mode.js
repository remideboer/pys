'use strict';

const PYS_DEBUG_SESSION_NAME = 'Debug PYS';
const PYTHON_DEBUG_SESSION_NAME = 'Debug PYS (Transpiled Python)';
const JS_DEBUG_SESSION_NAME = 'Debug PYS (Transpiled JavaScript)';

/**
 * @param {string} [mode] 'pys' (mapped) or 'python'/'generated' (advanced)
 * @param {string} [target] emit target: 'python' | 'javascript'
 */
function debugModeOptions(mode = 'pys', target = 'python') {
  if (mode === 'python' || mode === 'generated') {
    const isJs = target === 'javascript';
    return {
      mode: 'python',
      sessionName: isJs ? JS_DEBUG_SESSION_NAME : PYTHON_DEBUG_SESSION_NAME,
      justMyCode: false,
      stopOnEntry: true,
      remapSource: false,
      revealGenerated: true,
      pysOnlyStepping: false,
    };
  }
  return {
    mode: 'pys',
    sessionName: PYS_DEBUG_SESSION_NAME,
    justMyCode: true,
    stopOnEntry: false,
    remapSource: true,
    revealGenerated: false,
    pysOnlyStepping: true,
  };
}

function isPysDebugSession(sessionName) {
  return (
    sessionName === PYS_DEBUG_SESSION_NAME ||
    sessionName === PYTHON_DEBUG_SESSION_NAME ||
    sessionName === JS_DEBUG_SESSION_NAME
  );
}

module.exports = {
  PYS_DEBUG_SESSION_NAME,
  PYTHON_DEBUG_SESSION_NAME,
  JS_DEBUG_SESSION_NAME,
  debugModeOptions,
  isPysDebugSession,
};
