'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const root = path.join(__dirname, '..');
const ignorePath = path.join(root, '.vscodeignore');

test('runtime modules do not require excluded scripts/ folder', () => {
  const ignore = fs.readFileSync(ignorePath, 'utf8');
  assert.match(ignore, /^scripts$/m, '.vscodeignore must keep excluding scripts/');

  for (const name of ['syntax-colors-ui.js', 'syntax-color-picker.js', 'extension.js']) {
    const src = fs.readFileSync(path.join(root, name), 'utf8');
    assert.doesNotMatch(
      src,
      /require\(['"]\.\/scripts\//,
      `${name} must not require ./scripts/ (excluded from VSIX)`,
    );
  }

  assert.ok(
    fs.existsSync(path.join(root, 'syntax-color-roles.js')),
    'packaged syntax-color-roles.js must exist',
  );
  // Load path used at runtime (no vscode needed for roles + ui pure helpers)
  const roles = require('../syntax-color-roles.js');
  assert.ok(roles.ROLE_SCOPES.keywords);
  const ui = require('../syntax-colors-ui.js');
  assert.equal(typeof ui.registerSyntaxColorSettings, 'function');
});
