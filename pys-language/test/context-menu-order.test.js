/**
 * Context menu order + in-class extract title.
 */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { isOffsetInClassBody } = require('../in-class-body.js');

const root = path.join(__dirname, '..');
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));

test('editor/context order: run, refactor, find usages, generate, reveal, extra', () => {
  const ctx = manifest.contributes.menus['editor/context'].filter(
    (e) => e.when && String(e.when).includes('resourceExtname == .pys'),
  );
  const byCmd = (id) => ctx.find((e) => e.command === id || e.submenu === id);
  assert.equal(byCmd('pys.runFile').group, '0_run@1');
  assert.equal(byCmd('pys.debugFile').group, '0_run@2');
  assert.equal(byCmd('pys.refactor.rename').group, '1_pys_refactor@1');
  assert.equal(byCmd('pys.refactor.extractFunction').group, '1_pys_refactor@2');
  assert.equal(byCmd('pys.refactor.extractMethod').group, '1_pys_refactor@2');
  assert.match(byCmd('pys.refactor.extractFunction').when, /!pys\.inClassBody/);
  assert.match(byCmd('pys.refactor.extractMethod').when, /pys\.inClassBody/);
  assert.equal(byCmd('pys.refactor.more').group, '1_pys_refactor@3');
  assert.equal(byCmd('pys.findUsages').group, 'navigation@50');
  assert.equal(byCmd('pys.generate').group, 'z_pys_generate@1');
  assert.equal(byCmd('revealFileInOS').group, 'z_pys_reveal@1');
  assert.equal(byCmd('pys.debugTranspiledFile').group, 'z_pys_extra@1');

  const refactorSub = manifest.contributes.submenus.find((s) => s.id === 'pys.refactor.more');
  assert.equal(refactorSub.label, 'Refactor');
  const genSub = manifest.contributes.submenus.find((s) => s.id === 'pys.generate');
  assert.equal(genSub.label, 'Generate');

  const gen = manifest.contributes.menus['pys.generate'].map((e) => e.command);
  assert.deepEqual(gen, [
    'pys.generate.constructor',
    'pys.generate.toString',
    'pys.generate.overrideMethods',
    'pys.generate.gettersSetters',
    'pys.generate.test',
    'pys.generate.createClass',
  ]);

  const more = manifest.contributes.menus['pys.refactor.more'].map((e) => e.command);
  assert.ok(more.includes('pys.refactor.extractVariable'));
  assert.ok(!ctx.some((e) => e.command === 'pys.refactor.extractVariable'));
});

test('isOffsetInClassBody detects class vs top-level function', () => {
  const src = [
    'class Hero {',
    '    public void greet() {',
    '        print("hi")',
    '    }',
    '}',
    'function top() {',
    '    print(1)',
    '}',
    '',
  ].join('\n');
  const inGreet = src.indexOf('print("hi")');
  const inTop = src.indexOf('print(1)');
  assert.equal(isOffsetInClassBody(src, inGreet), true);
  assert.equal(isOffsetInClassBody(src, inTop), false);
});
