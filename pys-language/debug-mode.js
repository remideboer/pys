'use strict';

const PYS_DEBUG_SESSION_NAME = 'Debug PYS';
const PYTHON_DEBUG_SESSION_NAME = 'Debug PYS (Transpiled Python)';

function debugModeOptions(mode = 'pys') {
  if (mode === 'python') {
    return {
      mode,
      sessionName: PYTHON_DEBUG_SESSION_NAME,
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
    sessionName === PYTHON_DEBUG_SESSION_NAME
  );
}

module.exports = {
  PYS_DEBUG_SESSION_NAME,
  PYTHON_DEBUG_SESSION_NAME,
  debugModeOptions,
  isPysDebugSession,
};
