/**
 * Grammar regressions for field / typed declarations (TextMate match strings).
 * Uses JS RegExp — patterns are Oniguruma-compatible for these cases.
 */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const grammarPath = path.join(__dirname, '..', 'syntaxes', 'pys.tmLanguage.json');
const grammar = JSON.parse(fs.readFileSync(grammarPath, 'utf8'));

function findDecl(name) {
  const patterns = grammar.repository.declarations.patterns;
  const hit = patterns.find((p) => p.name === name);
  assert.ok(hit, `missing declaration pattern ${name}`);
  return hit;
}

function toRegExp(match) {
  return new RegExp(match);
}

test('field declaration highlights builtin and user types', () => {
  const { match, captures } = findDecl('meta.field.declaration.pys');
  const re = toRegExp(match);

  const builtin = '    private string name'.match(re);
  assert.ok(builtin, 'private string name should match field pattern');
  assert.equal(builtin[1], 'private');
  assert.equal(builtin[4], 'string');
  assert.equal(builtin[6], 'name');
  assert.equal(captures['4'].name, 'storage.type.primitive.pys');
  assert.notEqual(captures['4'].name, 'storage.modifier.pys');

  const user = '    private Heritage heritage'.match(re);
  assert.ok(user, 'private Heritage heritage should match field pattern');
  assert.equal(user[1], 'private');
  assert.equal(user[5], 'Heritage');
  assert.equal(user[6], 'heritage');
  assert.equal(captures['5'].name, 'entity.name.type.pys');

  const bare = '    string name'.match(re);
  assert.ok(bare, 'bare string name should match field pattern (omitted access)');
  assert.equal(bare[1], undefined);
  assert.equal(bare[4], 'string');
  assert.equal(bare[6], 'name');
});

test('typed declaration does not treat private as a type', () => {
  const { match } = findDecl('meta.typed.declaration.pys');
  const re = toRegExp(match);
  // May match the trailing `string name` substring; must not capture `private` as a type.
  const hit = 'private string name'.match(re);
  assert.ok(hit);
  assert.notEqual(hit[1], 'private');
  assert.notEqual(hit[2], 'private');
  assert.equal(hit[1], 'string');
  assert.equal(hit[3], 'name');

  const user = 'Heritage heritage'.match(re);
  assert.ok(user);
  assert.equal(user[2], 'Heritage');
  assert.equal(user[3], 'heritage');
});

test('method declaration keeps override + return type', () => {
  const { match, captures } = findDecl('meta.method.declaration.pys');
  const re = toRegExp(match);
  const m = '    public override string toString(){'.match(re);
  assert.ok(m);
  assert.equal(m[1], 'public');
  assert.equal(m[4], 'override');
  assert.equal(m[5], 'string');
  assert.equal(m[7], 'toString');
  assert.equal(captures['5'].name, 'storage.type.primitive.pys');

  const bare = '    greet(){'.match(re);
  assert.ok(bare, 'bare greet() should match method pattern (omitted access)');
  assert.equal(bare[1], undefined);
  assert.equal(bare[7], 'greet');
});

test('package.json defaults share one color for primitive and class types', () => {
  // Full scheme → package.json wiring is covered in syntax-colors.test.js.
  const manifest = JSON.parse(
    fs.readFileSync(path.join(__dirname, '..', 'package.json'), 'utf8'),
  );
  const darkRules =
    manifest.contributes.configurationDefaults['editor.tokenColorCustomizations']['[*Dark*]']
      .textMateRules;
  const typeRule = darkRules.find(
    (r) => Array.isArray(r.scope) && r.scope.includes('storage.type.primitive.pys'),
  );
  assert.ok(typeRule);
  assert.ok(typeRule.scope.includes('entity.name.type.pys'));
  assert.ok(typeRule.scope.includes('entity.name.type.class.pys'));
  assert.match(typeRule.settings.foreground, /^#[0-9A-Fa-f]{6}$/);
  const props = manifest.contributes.configuration.properties;
  assert.equal(props['pys.syntaxColors.types'].type, 'string');
  assert.equal(props['pys.syntaxColors.types'].format, 'color');
  assert.equal(props['pys.syntaxColors.types'].default, typeRule.settings.foreground);
});
