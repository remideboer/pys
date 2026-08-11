/**
 * QuickFix helpers: make enclosing class abstract + Create Class gating.
 */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const { findEnclosingClassHeader } = require('../class-header.js');

function fakeDoc(lines) {
  return {
    lineAt(i) {
      return { text: lines[i] ?? '' };
    },
  };
}

test('findEnclosingClassHeader inserts before bare class', () => {
  const doc = fakeDoc(['class Character{', '    public abstract int greet()', '}']);
  const hit = findEnclosingClassHeader(doc, 1, 'Character');
  assert.ok(hit);
  assert.equal(hit.line, 0);
  assert.equal(hit.alreadyAbstract, false);
  assert.equal(hit.closed, false);
  assert.equal(hit.classIndex, 0);
});

test('findEnclosingClassHeader replaces closed with abstract', () => {
  const doc = fakeDoc(['package closed class Ship{', '    public abstract int f()', '}']);
  const hit = findEnclosingClassHeader(doc, 1, 'Ship');
  assert.ok(hit);
  assert.equal(hit.closed, true);
  assert.equal(hit.closedIndex, 'package '.length);
  assert.equal(hit.classIndex, 'package closed '.length);
});

test('findEnclosingClassHeader detects already abstract', () => {
  const doc = fakeDoc(['abstract class A{', '    public abstract int f()', '}']);
  const hit = findEnclosingClassHeader(doc, 1, 'A');
  assert.ok(hit);
  assert.equal(hit.alreadyAbstract, true);
});

test('extension offers make-abstract and gates create-class on sentinel', () => {
  const src = fs.readFileSync(path.join(__dirname, '..', 'extension.js'), 'utf8');
  assert.match(src, /pys\.abstract-method/);
  assert.match(src, /Make class/);
  assert.match(src, /findEnclosingClassHeader/);
  assert.match(src, /suggested_fix === 'create-class'/);
  assert.match(src, /require\('\.\/class-header'\)/);
});

test('refactor catalog no longer always-on Create Class QuickFix', () => {
  const src = fs.readFileSync(path.join(__dirname, '..', 'refactor.js'), 'utf8');
  assert.doesNotMatch(
    src,
    /add\('Create Class…',\s*'pys\.generate\.createClass',\s*vscode\.CodeActionKind\.QuickFix/,
  );
  assert.match(src, /pys\.generate\.createClass/);
});
