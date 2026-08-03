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
