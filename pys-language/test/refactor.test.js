const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const {
  applyEditsToText,
  applySelectedEdits,
  buildLineDiff,
  computeAfterSpans,
  posToOffset,
} = require('../refactor-preview');

test('refactor.js module file exists and exports registerRefactoring', () => {
  const src = fs.readFileSync(path.join(__dirname, '..', 'refactor.js'), 'utf8');
  assert.match(src, /function registerRefactoring/);
  assert.doesNotMatch(src, /registerRenameProvider/);
  assert.match(src, /CodeActionKind\.RefactorExtract/);
  assert.match(src, /showLivePreview/);
  assert.doesNotMatch(src, /showModalPreview/);
  assert.doesNotMatch(src, /refactor-inline-preview/);
  assert.doesNotMatch(
    src,
    /add\('Create Class…',\s*'pys\.generate\.createClass',\s*vscode\.CodeActionKind\.QuickFix/,
  );
});

test('refactor name prompts stay modal; apply preview is live in editor', () => {
  const modal = fs.readFileSync(path.join(__dirname, '..', 'refactor-modal.js'), 'utf8');
  assert.match(modal, /showModalInput/);
  const main = fs.readFileSync(path.join(__dirname, '..', 'refactor.js'), 'utf8');
  assert.match(main, /showModalInput/);
  assert.match(main, /captureEditor/);
  assert.match(main, /refactor-live-preview/);
  assert.match(main, /pys\.refactor\.rename/);
  assert.doesNotMatch(main, /editor\.action\.rename/);
  assert.match(main, /--stdin/);
  const live = fs.readFileSync(path.join(__dirname, '..', 'refactor-live-preview.js'), 'utf8');
  assert.match(live, /createTextEditorDecorationType/);
  assert.match(live, /Accept/);
  assert.match(live, /Reject/);
  assert.match(live, /showLivePreview/);
  assert.match(live, /alreadyApplied/);
  assert.match(live, /line-through/);
  assert.match(live, /CodeLens/);
  assert.match(live, /ignoreFocusOut/);
  assert.match(live, /createInputBox/);
  assert.doesNotMatch(live, /showInformationMessage/);
  assert.doesNotMatch(live, /createWebviewPanel/);
});

test('refactor menu items: run first, rename/extract before Go to Definition peers', () => {
  const manifest = JSON.parse(
    fs.readFileSync(path.join(__dirname, '..', 'package.json'), 'utf8'),
  );
  const ctx = manifest.contributes.menus['editor/context'];
  const rename = ctx.find((e) => e.command === 'pys.refactor.rename');
  const more = ctx.find((e) => e.submenu === 'pys.refactor.more');
  const find = ctx.find((e) => e.command === 'pys.findUsages');
  const run = ctx.find((e) => e.command === 'pys.runFile');
  const debug = ctx.find((e) => e.command === 'pys.debugFile');
  assert.ok(rename);
  assert.ok(more);
  assert.ok(find);
  assert.ok(run);
  assert.ok(debug);
  assert.equal(run.group, '0_run@1');
  assert.equal(debug.group, '0_run@2');
  assert.match(rename.group, /^1_pys_refactor@/);
  assert.match(more.group, /^1_pys_refactor@/);
  assert.match(find.group, /^navigation@/);
  const refactorSub = manifest.contributes.submenus.find((s) => s.id === 'pys.refactor.more');
  assert.equal(refactorSub.label, 'Refactor');
  // Catalog CodeAction must not re-add Rename Symbol (duplicate of context entry).
  const refactorSrc = fs.readFileSync(path.join(__dirname, '..', 'refactor.js'), 'utf8');
  assert.doesNotMatch(
    refactorSrc,
    /add\('Rename Symbol…',\s*'pys\.refactor\.rename'/,
  );
  assert.match(refactorSrc, /pys\.refactor\.extractMethod/);
  const f2 = (manifest.contributes.keybindings || []).find(
    (k) => k.command === 'pys.refactor.rename' && String(k.key).toLowerCase() === 'f2',
  );
  assert.ok(f2, 'F2 should invoke PYS rename (no built-in RenameProvider menu)');
});

test('computeAfterSpans maps rename sites onto after-text offsets', () => {
  const original = 'int getalA = 1\nprint(getalA)\n';
  const edits = [
    {
      line: 1,
      column: 5,
      end_line: 1,
      end_column: 11,
      new_text: 'valueA',
      kind: 'replace',
    },
    {
      line: 2,
      column: 7,
      end_line: 2,
      end_column: 13,
      new_text: 'valueA',
      kind: 'replace',
    },
  ];
  const after = applyEditsToText(original, edits);
  assert.equal(after, 'int valueA = 1\nprint(valueA)\n');
  const spans = computeAfterSpans(original, edits);
  assert.equal(spans.length, 2);
  assert.equal(spans[0].oldText, 'getalA');
  assert.equal(spans[0].newText, 'valueA');
  assert.equal(after.slice(spans[0].startAfter, spans[0].endAfter), 'valueA');
  assert.equal(after.slice(spans[1].startAfter, spans[1].endAfter), 'valueA');
});

test('posToOffset is 1-based line/column', () => {
  const text = 'ab\ncd\n';
  assert.equal(posToOffset(text, 1, 1), 0);
  assert.equal(posToOffset(text, 1, 2), 1);
  assert.equal(posToOffset(text, 2, 1), 3);
  assert.equal(posToOffset(text, 2, 2), 4);
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
