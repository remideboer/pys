'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const {
  normalizedRelativeMain,
  readProjectMain,
  setProjectMain,
} = require('../project-main');

test('setProjectMain adds and replaces project main without losing sections', () => {
  const created = setProjectMain('[source_roots]\nsrc = "src"\n', 'src/app.pys');
  assert.equal(readProjectMain(created), 'src/app.pys');
  assert.match(created, /\[source_roots\]/);

  const replaced = setProjectMain(
    '[project]\nname = "demo"\nmain = "old.pys"\n\n[source_roots]\nsrc = "src"\n',
    'src/new.pys',
  );
  assert.equal(readProjectMain(replaced), 'src/new.pys');
  assert.equal((replaced.match(/^main\s*=/gm) || []).length, 1);
  assert.match(replaced, /name = "demo"/);
});

test('normalizedRelativeMain rejects paths outside the project', () => {
  const root = process.platform === 'win32' ? 'C:\\project' : '/project';
  const nested = process.platform === 'win32'
    ? 'C:\\project\\src\\app.pys'
    : '/project/src/app.pys';
  const outside = process.platform === 'win32'
    ? 'C:\\other\\app.pys'
    : '/other/app.pys';

  assert.equal(normalizedRelativeMain(root, nested), 'src/app.pys');
  assert.throws(() => normalizedRelativeMain(root, outside), /inside the project/);
});

test('extension manifest exposes entrypoint command and result language support', () => {
  const extensionRoot = path.resolve(__dirname, '..');
  const manifest = JSON.parse(
    fs.readFileSync(path.join(extensionRoot, 'package.json'), 'utf8'),
  );
  const commands = manifest.contributes.commands.map((entry) => entry.command);
  assert.equal(manifest.version, '0.0.79');
  assert.ok(commands.includes('pys.setAsEntrypoint'));

  const grammar = fs.readFileSync(
    path.join(extensionRoot, 'syntaxes', 'pys.tmLanguage.json'),
    'utf8',
  );
  assert.match(grammar, /propagate/);
  assert.match(grammar, /result/);
  assert.match(grammar, /nullable/);
  assert.match(grammar, /parseFloat/);
  assert.match(grammar, /\binput\b/);
  assert.match(grammar, /toBin/);
  assert.match(grammar, /toHex/);

  const extension = fs.readFileSync(
    path.join(extensionRoot, 'extension.js'),
    'utf8',
  );
  assert.match(extension, /diagnostic\.code === 'pys\.entrypoint-conflict'/);
  assert.match(extension, /Set this file as entrypoint/);
  assert.match(extension, /CodeActionKind\.QuickFix/);
  assert.match(extension, /Make type nullable/);
  assert.match(extension, /Surround with null check/);
  assert.match(extension, /'nullable'/);
});
