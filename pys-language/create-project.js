/**
 * Pure filesystem scaffold for a new PYS project (ADR-017 source roots).
 * Kept free of vscode so unit tests can run under node --test.
 */

'use strict';

const path = require('path');
const fs = require('fs');

const PYSTOML = `[project]
main = "src/main.pys"

[source_roots]
main = "src"
test = "tests"

[interpreter]
version = ">=3.10"

[dependencies]
# Add third-party packages here, then right-click pys.toml → PYS: Run Deps Lock
# "example-package" = { version = "1.2.3" }

# npm packages for --target javascript (optional):
# [dependencies.npm]
# mysql2 = "^3.11.0"
`;

const MAIN_SOURCE = `# Expected output:
# Hello from PYS

print("Hello from PYS")
`;

/**
 * @param {string} projectRoot absolute path
 * @param {{ existsSync?: Function, mkdirSync?: Function, writeFileSync?: Function }} [io]
 * @returns {{ root: string, created: string[] }}
 */
function createPysProjectScaffold(projectRoot, io = fs) {
  const root = path.resolve(projectRoot);
  if (!io.existsSync(root)) {
    io.mkdirSync(root, { recursive: true });
  }
  const tomlPath = path.join(root, 'pys.toml');
  if (io.existsSync(tomlPath)) {
    const err = new Error(`Already a PYS project (pys.toml exists): ${root}`);
    err.code = 'PYS_PROJECT_EXISTS';
    throw err;
  }
  const created = [];
  for (const rel of ['src', 'tests']) {
    const dir = path.join(root, rel);
    if (!io.existsSync(dir)) {
      io.mkdirSync(dir, { recursive: true });
      created.push(rel + path.sep);
    }
    if (rel === 'tests') {
      const keep = path.join(dir, '.gitkeep');
      if (!io.existsSync(keep)) {
        io.writeFileSync(keep, '', 'utf8');
        created.push(path.join(rel, '.gitkeep'));
      }
    }
  }
  const mainPath = path.join(root, 'src', 'main.pys');
  if (!io.existsSync(mainPath)) {
    io.writeFileSync(mainPath, MAIN_SOURCE, 'utf8');
    created.push(path.join('src', 'main.pys'));
  }
  io.writeFileSync(tomlPath, PYSTOML, 'utf8');
  created.push('pys.toml');
  return { root, created };
}

module.exports = {
  createPysProjectScaffold,
  MAIN_SOURCE,
  PYSTOML,
};
