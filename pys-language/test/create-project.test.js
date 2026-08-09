const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const {
  createPysProjectScaffold,
  MAIN_SOURCE,
  PYSTOML,
} = require('../create-project');

test('createPysProjectScaffold writes src, tests, and unified pys.toml', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pys-scaffold-'));
  try {
    const result = createPysProjectScaffold(root);
    assert.equal(result.root, path.resolve(root));
    assert.equal(
      fs.readFileSync(path.join(root, 'src', 'main.pys'), 'utf8'),
      MAIN_SOURCE,
    );
    assert.ok(fs.existsSync(path.join(root, 'tests', '.gitkeep')));
    assert.equal(fs.readFileSync(path.join(root, 'pys.toml'), 'utf8'), PYSTOML);
    assert.match(PYSTOML, /\[project\]\nmain = "src\/main\.pys"/);
    assert.match(PYSTOML, /\[interpreter\]/);
    assert.match(PYSTOML, /\[dependencies\]/);
    assert.ok(!fs.existsSync(path.join(root, 'pys.deps')));
    assert.ok(result.created.includes(path.join('src', 'main.pys')));
    assert.ok(result.created.includes('pys.toml'));
    assert.ok(!result.created.includes('pys.deps'));
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('createPysProjectScaffold refuses an existing pys.toml', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pys-scaffold-'));
  try {
    fs.writeFileSync(path.join(root, 'pys.toml'), '[source_roots]\n', 'utf8');
    assert.throws(
      () => createPysProjectScaffold(root),
      (err) => err && err.code === 'PYS_PROJECT_EXISTS',
    );
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});
