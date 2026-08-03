const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('path');
const {
  loadMapRegistry,
  mapPysBreakpoint,
  mapPyStackFrame,
  remapSetBreakpointsArgs,
  remapSetBreakpointsResponse,
  remapBreakpoint,
  remapStackFrames,
  remapVariables,
  rewriteEvaluateExpression,
  rewriteLogMessageExpressions,
  collectInlineValueSites,
  filterInlineValueSitesByScope,
  normalizePathKey,
} = require('../debug-map');

const PY = path.join('C:', 'tmp', 'dbg', 'demo.py');
const PYS = path.join('C:', 'ws', 'demo.pys');

function registryFromSidecar(sidecar) {
  const mapFiles = { demo: 'demo.pysmap.json' };
  const read = () => JSON.stringify(sidecar);
  return loadMapRegistry(mapFiles, read);
}

test('loadMapRegistry indexes py and pys paths', () => {
  const reg = registryFromSidecar({
    version: 1,
    pys: PYS,
    py: PY,
    lines: [
      { py: 10, pys: 1 },
      { py: 11, pys: 2 },
    ],
  });
  assert.equal(reg.byPy.has(normalizePathKey(PY)), true);
  assert.equal(reg.byPys.has(normalizePathKey(PYS)), true);
});

test('mapPysBreakpoint exact and forward nearest', () => {
  const reg = registryFromSidecar({
    version: 1,
    pys: PYS,
    py: PY,
    lines: [
      { py: 10, pys: 1 },
      { py: 12, pys: 3 },
    ],
  });
  assert.deepEqual(mapPysBreakpoint(reg, PYS, 1), { pyPath: PY, pyLine: 10 });
  assert.deepEqual(mapPysBreakpoint(reg, PYS, 2), { pyPath: PY, pyLine: 12 });
});

test('mapPyStackFrame exact and backward nearest', () => {
  const reg = registryFromSidecar({
    version: 1,
    pys: PYS,
    py: PY,
    lines: [
      { py: 10, pys: 1 },
      { py: 12, pys: 3 },
    ],
  });
  assert.deepEqual(mapPyStackFrame(reg, PY, 12), { pysPath: PYS, pysLine: 3 });
  assert.deepEqual(mapPyStackFrame(reg, PY, 11), { pysPath: PYS, pysLine: 1 });
});

test('remapSetBreakpointsArgs rewrites .pys source to .py', () => {
  const reg = registryFromSidecar({
    version: 1,
    pys: PYS,
    py: PY,
    lines: [{ py: 5, pys: 2 }],
  });
  const out = remapSetBreakpointsArgs(reg, {
    source: { path: PYS, name: 'demo.pys' },
    breakpoints: [{ line: 2 }],
  });
  assert.equal(out.source.path, PY);
  assert.equal(out.breakpoints[0].line, 5);
});

test('remapSetBreakpointsResponse maps verified glyph back to .pys', () => {
  const reg = registryFromSidecar({
    version: 1,
    pys: PYS,
    py: PY,
    lines: [{ py: 5, pys: 2 }],
  });
  const body = remapSetBreakpointsResponse(
    reg,
    {
      breakpoints: [
        { id: 1, verified: true, line: 5, source: { path: PY, name: 'demo.py' } },
      ],
    },
    PYS,
  );
  assert.equal(body.breakpoints[0].source.path, PYS);
  assert.equal(body.breakpoints[0].line, 2);
});

test('remapBreakpoint event source back to .pys', () => {
  const reg = registryFromSidecar({
    version: 1,
    pys: PYS,
    py: PY,
    lines: [{ py: 9, pys: 4 }],
  });
  const bp = remapBreakpoint(reg, {
    id: 2,
    verified: true,
    line: 9,
    source: { path: PY },
  });
  assert.equal(bp.source.path, PYS);
  assert.equal(bp.line, 4);
});

test('remapStackFrames rewrites .py frames to .pys', () => {
  const reg = registryFromSidecar({
    version: 1,
    pys: PYS,
    py: PY,
    lines: [{ py: 8, pys: 4 }],
  });
  const frames = remapStackFrames(reg, [
    { id: 1, line: 8, source: { path: PY, name: 'demo.py' } },
  ]);
  assert.equal(frames[0].source.path, PYS);
  assert.equal(frames[0].line, 4);
});

test('remapVariables renames _c_ captures and hides runtime helpers', () => {
  const reg = registryFromSidecar({
    version: 1,
    pys: PYS,
    py: PY,
    lines: [],
    names: { _c_hits: 'hits' },
    hidePrefixes: ['_pys_', '__pys_', '_Pys'],
  });
  const vars = remapVariables(reg, [
    { name: '_c_hits', value: '3', variablesReference: 0 },
    { name: '_pys_tg_0', value: '<TaskGroup>', variablesReference: 1 },
    { name: '__pys_task_a', value: '<fn>', variablesReference: 0 },
    { name: 'n', value: '1', variablesReference: 0 },
  ]);
  assert.deepEqual(
    vars.map((v) => v.name),
    ['hits', 'n'],
  );
});

test('rewriteEvaluateExpression maps bare PYS name to emitted', () => {
  const reg = registryFromSidecar({
    version: 1,
    pys: PYS,
    py: PY,
    lines: [],
    names: { _c_hits: 'hits' },
  });
  assert.equal(rewriteEvaluateExpression(reg, 'hits'), '_c_hits');
  assert.equal(rewriteEvaluateExpression(reg, ' hits '), '_c_hits');
  assert.equal(rewriteEvaluateExpression(reg, 'hits + 1'), 'hits + 1');
  assert.equal(rewriteEvaluateExpression(reg, 'n'), 'n');
});

test('collectInlineValueSites finds vars up to stopped line', () => {
  const src = [
    'int total = 0',
    'print("total")  # name in string ignored',
    'total = bump(total)',
    'print(total)',
  ].join('\n');
  const sites = collectInlineValueSites(src, 3, {
    keywords: ['print'],
    types: ['int'],
  });
  assert.deepEqual(
    sites.map((s) => ({ line: s.line, name: s.name })),
    [
      { line: 0, name: 'total' },
      { line: 2, name: 'total' },
      { line: 2, name: 'bump' },
    ],
  );
});

test('filterInlineValueSitesByScope keeps only in-scope names', () => {
  const sites = [
    { line: 0, column: 4, length: 5, name: 'total' },
    { line: 2, column: 0, length: 4, name: 'bump' },
    { line: 2, column: 7, length: 5, name: 'total' },
  ];
  const filtered = filterInlineValueSitesByScope(sites, new Set(['total']));
  assert.deepEqual(
    filtered.map((s) => s.name),
    ['total', 'total'],
  );
  assert.deepEqual(filterInlineValueSitesByScope(sites, new Set()), []);
  // Map of name -> value (as returned by fetchFrameLocalValues) must use keys.
  const asMap = new Map([
    ['total', '1'],
    ['other', '2'],
  ]);
  assert.deepEqual(
    filterInlineValueSitesByScope(sites, asMap).map((s) => s.name),
    ['total', 'total'],
  );
});

test('rewriteLogMessageExpressions rewrites braced PYS names', () => {
  const reg = registryFromSidecar({
    version: 1,
    pys: PYS,
    py: PY,
    lines: [{ py: 10, pys: 3 }],
    names: { _c_hits: 'hits' },
  });
  assert.equal(
    rewriteLogMessageExpressions(reg, 'hits={hits} n={n}'),
    'hits={_c_hits} n={n}',
  );
  assert.equal(
    rewriteLogMessageExpressions(reg, 'sum={hits + 1}'),
    'sum={_c_hits + 1}',
  );
});

test('remapSetBreakpointsArgs preserves and rewrites logMessage', () => {
  const reg = registryFromSidecar({
    version: 1,
    pys: PYS,
    py: PY,
    lines: [{ py: 10, pys: 3 }],
    names: { _c_hits: 'hits' },
  });
  const out = remapSetBreakpointsArgs(reg, {
    source: { path: PYS, name: 'demo.pys' },
    breakpoints: [{ line: 3, logMessage: 'hits={hits}' }],
  });
  assert.equal(out.source.path, PY);
  assert.equal(out.breakpoints[0].line, 10);
  assert.equal(out.breakpoints[0].logMessage, 'hits={_c_hits}');
});
