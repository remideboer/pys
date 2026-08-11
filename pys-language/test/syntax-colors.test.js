/**
 * Syntax color scheme file → package.json defaults + Settings color pickers.
 */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const {
  parseSchemes,
  rulesFromEntries,
  ROLE_SCOPES,
  ROLE_PACKAGE_SETTINGS,
  THEME_KEYS,
  apply,
} = require('../scripts/apply-syntax-colors.js');

const {
  mergeTokenColorCustomizations,
  isManagedPysRule,
  normalizeHex,
  overridesFromInspect,
  ROLE_SETTING_KEYS,
} = require('../syntax-colors-ui.js');

const root = path.join(__dirname, '..');
const schemesPath = path.join(root, 'syntax-color-schemes.md');

test('syntax-color-schemes.md uses roles not color names as identifiers', () => {
  const md = fs.readFileSync(schemesPath, 'utf8');
  assert.match(md, /## theme: dark/);
  assert.match(md, /## theme: light/);
  assert.match(md, /## theme: high-contrast/);
  assert.match(md, /→ types #[0-9A-Fa-f]{6}/);
  assert.match(md, /→ keywords #[0-9A-Fa-f]{6}/);
  assert.match(md, /Settings → Extensions/);
  assert.doesNotMatch(md, /→ Yellow #/);

  const themes = parseSchemes(md);
  assert.ok(themes.dark.length >= 7);
  const types = themes.dark.find((e) => e.role === 'types');
  assert.ok(types.hex.startsWith('#'));
  assert.match(types.usage, /types/i);
});

test('apply-syntax-colors maps roles to package.json hex and color settings', () => {
  apply();
  const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
  const themes = parseSchemes(fs.readFileSync(schemesPath, 'utf8'));
  const darkHex = Object.fromEntries(
    themes.dark.filter((e) => ROLE_SCOPES[e.role]).map((e) => [e.role, e.hex]),
  );
  const lightHex = Object.fromEntries(
    themes.light.filter((e) => ROLE_SCOPES[e.role]).map((e) => [e.role, e.hex]),
  );
  const hcHex = Object.fromEntries(
    themes['high-contrast'].filter((e) => ROLE_SCOPES[e.role]).map((e) => [e.role, e.hex]),
  );

  const dark =
    pkg.contributes.configurationDefaults['editor.tokenColorCustomizations']['[*Dark*]']
      .textMateRules;
  const light =
    pkg.contributes.configurationDefaults['editor.tokenColorCustomizations']['[*Light*]']
      .textMateRules;
  const hc =
    pkg.contributes.configurationDefaults['editor.tokenColorCustomizations']['[*HighContrast*]']
      .textMateRules;

  const darkTypes = dark.find((r) => r.scope.includes('storage.type.primitive.pys'));
  const darkKeywords = dark.find((r) => r.scope.includes('storage.modifier.pys'));
  const lightTypes = light.find((r) => r.scope.includes('storage.type.primitive.pys'));
  const hcStrings = hc.find((r) => r.scope.includes('string.quoted.double.pys'));
  assert.equal(darkTypes.settings.foreground, darkHex.types);
  assert.equal(darkKeywords.settings.foreground, darkHex.keywords);
  assert.equal(lightTypes.settings.foreground, lightHex.types);
  assert.equal(hcStrings.settings.foreground, hcHex.strings);
  assert.notEqual(darkTypes.settings.foreground, darkKeywords.settings.foreground);

  const props = pkg.contributes.configuration.properties;
  for (const [role, settingId] of Object.entries(ROLE_PACKAGE_SETTINGS)) {
    const prop = props[settingId];
    assert.ok(prop, `missing setting ${settingId}`);
    assert.equal(prop.type, 'string');
    assert.equal(prop.format, 'color');
    assert.equal(prop.default, darkHex[role]);
  }

  for (const role of Object.keys(ROLE_SCOPES)) {
    assert.ok(
      dark.some((r) => JSON.stringify(r.scope) === JSON.stringify(ROLE_SCOPES[role].scope)),
      `dark missing rules for role ${role}`,
    );
  }
  assert.deepEqual(Object.keys(THEME_KEYS).sort(), ['dark', 'high-contrast', 'light']);
});

test('rulesFromEntries rejects missing roles', () => {
  assert.throws(
    () => rulesFromEntries([{ usage: 'x', role: 'types', hex: '#8BE9FD' }]),
    /missing roles/i,
  );
});

test('mergeTokenColorCustomizations applies overrides and preserves foreign rules', () => {
  const existing = {
    '[*Dark*]': {
      textMateRules: [
        {
          scope: ['comment.line.number-sign.pys', 'comment.block.pys'],
          settings: { foreground: '#6272A4' },
        },
        {
          scope: ['entity.name.function.python'],
          settings: { foreground: '#ABCDEF' },
        },
      ],
    },
  };
  const merged = mergeTokenColorCustomizations(existing, { types: '#00ff00' });
  assert.ok(merged['[*Dark*]'].textMateRules.some((r) => r.scope.includes('entity.name.function.python')));
  const typesRule = merged['[*Dark*]'].textMateRules.find((r) =>
    r.scope.includes('storage.type.primitive.pys'),
  );
  assert.equal(typesRule.settings.foreground, '#00FF00');
  assert.ok(!merged['[*Dark*]'].textMateRules.some((r) => isManagedPysRule(r) && r.scope.includes('comment.line')));
  assert.equal(merged['[*HighContrast*]'].textMateRules.find((r) =>
    r.scope.includes('storage.type.primitive.pys'),
  ).settings.foreground, '#00FF00');
});

test('mergeTokenColorCustomizations clears managed rules when overrides empty', () => {
  const existing = {
    '[*Dark*]': {
      textMateRules: [
        {
          scope: [...ROLE_SCOPES.types.scope],
          settings: { foreground: '#111111' },
        },
        {
          scope: ['meta.embedded'],
          settings: { foreground: '#222222' },
        },
      ],
    },
  };
  const merged = mergeTokenColorCustomizations(existing, {});
  assert.equal(merged['[*Dark*]'].textMateRules.length, 1);
  assert.deepEqual(merged['[*Dark*]'].textMateRules[0].scope, ['meta.embedded']);
});

test('overridesFromInspect only uses explicit layer values', () => {
  const overrides = overridesFromInspect(
    (key) => {
      if (key === ROLE_SETTING_KEYS.types) {
        return { globalValue: '#abcdef', workspaceValue: undefined };
      }
      return { globalValue: undefined, workspaceValue: undefined };
    },
    'global',
  );
  assert.deepEqual(overrides, { types: '#ABCDEF' });
  assert.deepEqual(
    overridesFromInspect(
      () => ({ globalValue: '#abcdef', workspaceValue: undefined }),
      'workspace',
    ),
    {},
  );
});

test('normalizeHex accepts short and long forms', () => {
  assert.equal(normalizeHex('#0f0'), '#00FF00');
  assert.equal(normalizeHex('#00ff00aa'), '#00FF00');
});

test('package.json contributes Customize Syntax Colors command', () => {
  const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
  const cmd = pkg.contributes.commands.find((c) => c.command === 'pys.customizeSyntaxColors');
  assert.ok(cmd);
  assert.match(cmd.title, /Syntax Colors/i);
});
