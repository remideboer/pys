const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

test('refactor.js module file exists and exports registerRefactoring', () => {
  const src = fs.readFileSync(path.join(__dirname, '..', 'refactor.js'), 'utf8');
  assert.match(src, /function registerRefactoring/);
  assert.match(src, /registerRenameProvider/);
  assert.match(src, /CodeActionKind\.RefactorExtract/);
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
  const main = fs.readFileSync(path.join(__dirname, '..', 'refactor.js'), 'utf8');
  assert.match(main, /showModalInput/);
  assert.match(main, /captureEditor/);
});
