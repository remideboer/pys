'use strict';

/**
 * Display name for the shared Run File / Run Project / Run Main terminal.
 * @param {string} emitTarget
 * @returns {string}
 */
function runTerminalName(emitTarget) {
  return emitTarget === 'javascript' ? 'Run PYS (Node)' : 'Run PYS';
}

/**
 * Prefer the active terminal when it already is the named run terminal;
 * otherwise the first open terminal with that name; otherwise null (caller creates).
 * @param {ReadonlyArray<{ name: string }>} terminals
 * @param {{ name: string } | null | undefined} activeTerminal
 * @param {string} name
 * @returns {{ name: string } | null}
 */
function pickRunTerminal(terminals, activeTerminal, name) {
  if (activeTerminal && activeTerminal.name === name) {
    return activeTerminal;
  }
  const list = terminals || [];
  for (let i = 0; i < list.length; i += 1) {
    if (list[i] && list[i].name === name) {
      return list[i];
    }
  }
  return null;
}

module.exports = {
  pickRunTerminal,
  runTerminalName,
};
