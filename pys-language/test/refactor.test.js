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
