const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const {
  applyEditsToText,
  applySelectedEdits,
  buildLineDiff,
} = require('../refactor-preview');

test('refactor.js module file exists and exports registerRefactoring', () => {
  const src = fs.readFileSync(path.join(__dirname, '..', 'refactor.js'), 'utf8');
  assert.match(src, /function registerRefactoring/);
  assert.match(src, /registerRenameProvider/);
  assert.match(src, /CodeActionKind\.RefactorExtract/);
  assert.match(src, /loadEditSources/);
});

test('refactor modal helpers are centered webview dialogs', () => {
  const modal = fs.readFileSync(path.join(__dirname, '..', 'refactor-modal.js'), 'utf8');
  assert.match(modal, /showModalInput/);
  assert.match(modal, /showModalPreview/);
  assert.match(modal, /ViewColumn\.Beside/);
  assert.doesNotMatch(modal, /moveEditorToNewWindow/);
  assert.match(modal, />Refactor</);
  assert.doesNotMatch(modal, />OK</);
  assert.doesNotMatch(modal, />Apply</);
  assert.match(modal, /Code after refactor/);
  assert.match(modal, /renderCodePreviewHtml/);
  const main = fs.readFileSync(path.join(__dirname, '..', 'refactor.js'), 'utf8');
  assert.match(main, /showModalInput/);
  assert.match(main, /captureEditor/);
});

test('applyEditsToText replaces a single-line span', () => {
  const text = 'let x = 1\nlet y = x\n';
  const out = applyEditsToText(text, [
    {
      line: 1,
      column: 5,
      end_line: 1,
      end_column: 6,
      new_text: 'total',
      kind: 'replace',
    },
  ]);
  assert.equal(out, 'let total = 1\nlet y = x\n');
});

test('applyEditsToText inserts then keeps later replace valid via bottom-up order', () => {
  const text = 'a = 1\nb = 2\n';
  const out = applyEditsToText(text, [
    { line: 1, column: 1, end_line: 1, end_column: 1, new_text: 'pre\n', kind: 'insert' },
    { line: 2, column: 1, end_line: 2, end_column: 2, new_text: 'c', kind: 'replace' },
  ]);
  assert.equal(out, 'pre\na = 1\nc = 2\n');
});

test('applySelectedEdits respects indices and builds after text', () => {
  const sources = { '/t.pys': 'foo()\nbar()\n' };
  const edits = [
    {
      file: '/t.pys',
      line: 1,
      column: 1,
      end_line: 1,
      end_column: 4,
      new_text: 'baz',
      kind: 'replace',
    },
    {
      file: '/t.pys',
      line: 2,
      column: 1,
      end_line: 2,
      end_column: 4,
      new_text: 'qux',
      kind: 'replace',
    },
  ];
  const onlyFirst = applySelectedEdits(sources, edits, [0]);
  assert.equal(onlyFirst['/t.pys'], 'baz()\nbar()\n');
});

test('buildLineDiff marks added and deleted lines', () => {
  const diff = buildLineDiff('a = 1\nb = 2\n', 'a = 1\nc = 2\n');
  const kinds = diff.map((d) => d.kind);
  assert.ok(kinds.includes('del'));
  assert.ok(kinds.includes('add'));
});
