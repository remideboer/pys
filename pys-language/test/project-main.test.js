'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const {
  normalizedRelativeMain,
  readProjectMain,
  readProjectTarget,
  setProjectMain,
} = require('../project-main');

test('setProjectMain adds and replaces project main without losing sections', () => {
  const created = setProjectMain('[source_roots]\nsrc = "src"\n', 'src/app.pys');
  assert.equal(readProjectMain(created), 'src/app.pys');
  assert.match(created, /\[source_roots\]/);

  const replaced = setProjectMain(
    '[project]\nname = "demo"\nmain = "old.pys"\n\n[source_roots]\nsrc = "src"\n',
    'src/new.pys',
  );
  assert.equal(readProjectMain(replaced), 'src/new.pys');
  assert.equal((replaced.match(/^main\s*=/gm) || []).length, 1);
  assert.match(replaced, /name = "demo"/);
});

test('readProjectTarget parses optional emit target', () => {
  assert.equal(readProjectTarget('[project]\nmain = "a.pys"\n'), '');
  assert.equal(
    readProjectTarget('[project]\nmain = "a.pys"\ntarget = "javascript"\n'),
    'javascript',
  );
  assert.equal(
    readProjectTarget('[project]\ntarget = "Python"\nmain = "a.pys"\n'),
    'python',
  );
  assert.throws(
    () => readProjectTarget('[project]\ntarget = "ruby"\n'),
    /python.*javascript/,
  );
});

test('normalizedRelativeMain rejects paths outside the project', () => {
  const root = process.platform === 'win32' ? 'C:\\project' : '/project';
  const nested = process.platform === 'win32'
    ? 'C:\\project\\src\\app.pys'
    : '/project/src/app.pys';
  const outside = process.platform === 'win32'
    ? 'C:\\other\\app.pys'
    : '/other/app.pys';

  assert.equal(normalizedRelativeMain(root, nested), 'src/app.pys');
  assert.throws(() => normalizedRelativeMain(root, outside), /inside the project/);
});

test('extension manifest exposes entrypoint command and result language support', () => {
  const extensionRoot = path.resolve(__dirname, '..');
  const manifest = JSON.parse(
    fs.readFileSync(path.join(extensionRoot, 'package.json'), 'utf8'),
  );
  const commands = manifest.contributes.commands.map((entry) => entry.command);
  assert.match(manifest.version, /^\d+\.\d+\.\d+$/);
  assert.ok(commands.includes('pys.setAsEntrypoint'));
  assert.ok(commands.includes('pys.runProject'));

  const editorContext = manifest.contributes.menus['editor/context'] || [];
  const tomlRun = editorContext.find((entry) => entry.command === 'pys.runProject');
  const tomlLock = editorContext.find((entry) => entry.command === 'pys.lockDeps');
  assert.ok(tomlRun);
  assert.ok(tomlLock);
  assert.match(tomlRun.when, /pys\.toml/);
  assert.equal(tomlRun.group, 'navigation@0');

  const grammar = fs.readFileSync(
    path.join(extensionRoot, 'syntaxes', 'pys.tmLanguage.json'),
    'utf8',
  );
  assert.match(grammar, /propagate/);
  assert.match(grammar, /result/);
  assert.match(grammar, /nullable/);
  assert.match(grammar, /parseFloat/);
  assert.match(grammar, /\binput\b/);
  assert.match(grammar, /toBin/);
  assert.match(grammar, /toHex/);
  assert.match(grammar, /\bconstructor\b/);
  assert.match(grammar, /\bstatic\b/);
  assert.match(grammar, /\bopen\b/);
  assert.match(grammar, /\boverride\b/);

  const extension = fs.readFileSync(
    path.join(extensionRoot, 'extension.js'),
    'utf8',
  );
  assert.match(extension, /runProjectFromToml/);
  assert.match(extension, /readProjectTarget/);
  assert.match(extension, /skipEntrypointReconcile/);
  assert.match(extension, /diagnostic\.code === 'pys\.entrypoint-conflict'/);
  assert.match(extension, /Set this file as entrypoint/);
  assert.match(grammar, /punctuation\.definition\.decorator\.pys/);
  assert.match(grammar, /entity\.name\.function\.decorator\.pys/);
  assert.match(grammar, /meta\.function\.decorator\.pys/);
  assert.match(extension, /pys\.var-as-type/);
  assert.match(extension, /Replace `var` with `object`/);
  assert.match(extension, /Make type nullable/);
  assert.match(extension, /Surround with null check/);
  assert.match(extension, /'nullable'/);
  assert.match(extension, /'constructor'/);
  assert.match(extension, /'static'/);
  assert.match(extension, /Class-wide member/);
  assert.match(extension, /navigateLibrarySources/);
  assert.match(extension, /--library-sources/);
  assert.equal(
    manifest.contributes.configuration.properties['pys.navigateLibrarySources'].default,
    false,
  );
  assert.deepEqual(
    manifest.contributes.configuration.properties['pys.emitTarget'].enum,
    ['python', 'javascript'],
  );
  assert.equal(
    manifest.contributes.configuration.properties['pys.emitTarget'].default,
    'python',
  );
  assert.match(extension, /pys\.selectEmitTarget/);
  assert.match(extension, /require\('\.\/debug-launch'\)/);
  assert.match(extension, /buildLaunchConfig/);
  assert.match(extension, /debugAdapterTypes/);
  assert.match(extension, /'--target'/);
  assert.doesNotMatch(extension, /getEmitTarget\(\) !== 'python'/);

  const notes = fs.readFileSync(
    path.join(extensionRoot, 'RELEASE_NOTES.md'),
    'utf8',
  );
  // Notes must name the current package.json version (publish workflow check).
  // Do not require forever-keywords here — per-version highlights change.
  const versionLiteral = manifest.version.replace(/\./g, '\\.');
  assert.match(notes, new RegExp(versionLiteral));
});
