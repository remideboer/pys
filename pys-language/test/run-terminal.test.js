'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const {
  pickRunTerminal,
  runTerminalName,
} = require('../run-terminal');

test('runTerminalName uses Node label for javascript target', () => {
  assert.equal(runTerminalName('python'), 'Run PYS');
  assert.equal(runTerminalName('javascript'), 'Run PYS (Node)');
});

test('pickRunTerminal prefers active when name matches', () => {
  const active = { name: 'Run PYS' };
  const other = { name: 'Run PYS' };
  const picked = pickRunTerminal([other, active], active, 'Run PYS');
  assert.equal(picked, active);
});

test('pickRunTerminal finds by name when active is unrelated', () => {
  const run = { name: 'Run PYS' };
  const active = { name: 'powershell' };
  const picked = pickRunTerminal([{ name: 'Install Python' }, run], active, 'Run PYS');
  assert.equal(picked, run);
});

test('pickRunTerminal returns null when missing', () => {
  const picked = pickRunTerminal(
    [{ name: 'powershell' }],
    { name: 'powershell' },
    'Run PYS',
  );
  assert.equal(picked, null);
});

test('pickRunTerminal keeps python and node run terminals distinct', () => {
  const py = { name: 'Run PYS' };
  const node = { name: 'Run PYS (Node)' };
  assert.equal(pickRunTerminal([py, node], null, 'Run PYS (Node)'), node);
  assert.equal(pickRunTerminal([py, node], null, 'Run PYS'), py);
});
