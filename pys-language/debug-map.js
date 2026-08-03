/**
 * PYS ↔ Python line-map helpers for Debug Adapter remapping (F-004 / UX maturity).
 * Pure functions — unit-tested without VS Code.
 */
const fs = require('fs');
const path = require('path');

const DEFAULT_HIDE_PREFIXES = ['_pys_', '__pys_', '_Pys'];

function normalizePathKey(filePath) {
  if (!filePath) {
    return '';
  }
  let resolved = filePath;
  try {
    resolved = fs.realpathSync.native
      ? fs.realpathSync.native(filePath)
      : fs.realpathSync(filePath);
  } catch (_err) {
    resolved = path.resolve(filePath);
  }
  return process.platform === 'win32' ? resolved.toLowerCase() : resolved;
}

/**
 * Load sidecars from prepare_debug `maps` dict: stem -> pysmap.json path.
 * Returns { byPy, byPys, names, hidePrefixes } registries.
 */
function loadMapRegistry(mapFiles, readFileSync = fs.readFileSync) {
  const byPy = new Map();
  const byPys = new Map();
  const names = Object.create(null);
  let hidePrefixes = [...DEFAULT_HIDE_PREFIXES];
  for (const mapPath of Object.values(mapFiles || {})) {
    const raw = JSON.parse(readFileSync(mapPath, 'utf8'));
    const record = {
      pys: raw.pys,
      py: raw.py,
      // pys line -> first py line
      pysToPy: new Map(),
      // py line -> pys line
      pyToPys: new Map(),
    };
    for (const entry of raw.lines || []) {
      const py = entry.py;
      const pys = entry.pys;
      if (typeof py !== 'number' || typeof pys !== 'number') {
        continue;
      }
      if (!record.pysToPy.has(pys)) {
        record.pysToPy.set(pys, py);
      }
      record.pyToPys.set(py, pys);
    }
    if (raw.py) {
      byPy.set(normalizePathKey(raw.py), record);
    }
    if (raw.pys) {
      byPys.set(normalizePathKey(raw.pys), record);
    }
    if (raw.names && typeof raw.names === 'object') {
      Object.assign(names, raw.names);
    }
    if (Array.isArray(raw.hidePrefixes) && raw.hidePrefixes.length) {
      hidePrefixes = raw.hidePrefixes.slice();
    }
  }
  // Reverse map: PYS display name -> emitted name (for evaluate rewrite).
  const emittedByPys = Object.create(null);
  for (const [emitted, display] of Object.entries(names)) {
    emittedByPys[display] = emitted;
  }
  return { byPy, byPys, names, emittedByPys, hidePrefixes };
}

/** Map a .pys breakpoint line to a generated .py line (exact, else next mapped). */
function mapPysBreakpoint(registry, pysPath, pysLine) {
  const record = registry.byPys.get(normalizePathKey(pysPath));
  if (!record) {
    return null;
  }
  if (record.pysToPy.has(pysLine)) {
    return { pyPath: record.py, pyLine: record.pysToPy.get(pysLine) };
  }
  let best = null;
  for (const [pys, py] of record.pysToPy.entries()) {
    if (pys >= pysLine && (best === null || pys < best.pys)) {
      best = { pys, py };
    }
  }
  if (best) {
    return { pyPath: record.py, pyLine: best.py };
  }
  return null;
}

/** Map a generated .py stack line back to .pys when known. */
function mapPyStackFrame(registry, pyPath, pyLine) {
  const record = registry.byPy.get(normalizePathKey(pyPath));
  if (!record) {
    return null;
  }
  if (record.pyToPys.has(pyLine)) {
    return { pysPath: record.pys, pysLine: record.pyToPys.get(pyLine) };
  }
  // Walk backward for nearest mapped line (stepping often lands mid-statement).
  for (let line = pyLine; line >= 1; line -= 1) {
    if (record.pyToPys.has(line)) {
      return { pysPath: record.pys, pysLine: record.pyToPys.get(line) };
    }
  }
  return null;
}

function remapSetBreakpointsArgs(registry, args) {
  if (!args || !args.source || !args.source.path) {
    return args;
  }
  const src = args.source.path;
  if (!src.toLowerCase().endsWith('.pys')) {
    return args;
  }
  const record = registry.byPys.get(normalizePathKey(src));
  if (!record) {
    return args;
  }
  const breakpoints = (args.breakpoints || []).map((bp) => {
    const mapped = mapPysBreakpoint(registry, src, bp.line);
    if (!mapped) {
      return bp;
    }
    return { ...bp, line: mapped.pyLine };
  });
  return {
    ...args,
    source: { ...args.source, path: record.py, name: path.basename(record.py) },
    breakpoints,
  };
}

function remapBreakpoint(registry, bp, preferredPysPath) {
  if (!bp) {
    return bp;
  }
  const srcPath = (bp.source && bp.source.path) || '';
  let pyPath = srcPath;
  let pysPath = preferredPysPath;
  if (srcPath.toLowerCase().endsWith('.py')) {
    const mapped = mapPyStackFrame(registry, srcPath, bp.line);
    if (mapped) {
      return {
        ...bp,
        line: mapped.pysLine,
        source: {
          ...(bp.source || {}),
          path: mapped.pysPath,
          name: path.basename(mapped.pysPath),
        },
      };
    }
  }
  if (pysPath) {
    const record = registry.byPys.get(normalizePathKey(pysPath));
    if (record && srcPath && normalizePathKey(srcPath) === normalizePathKey(record.py)) {
      const mapped = mapPyStackFrame(registry, record.py, bp.line);
      if (mapped) {
        return {
          ...bp,
          line: mapped.pysLine,
          source: {
            ...(bp.source || {}),
            path: mapped.pysPath,
            name: path.basename(mapped.pysPath),
          },
        };
      }
    }
  }
  return bp;
}

/**
 * Remap setBreakpoints response body so verified glyphs stay on .pys.
 * @param {object} registry
 * @param {object} body DAP setBreakpoints response body
 * @param {string} [requestedPysPath] original .pys path from the request
 */
function remapSetBreakpointsResponse(registry, body, requestedPysPath) {
  if (!body || !Array.isArray(body.breakpoints)) {
    return body;
  }
  return {
    ...body,
    breakpoints: body.breakpoints.map((bp) =>
      remapBreakpoint(registry, bp, requestedPysPath),
    ),
  };
}

function remapStackFrames(registry, frames) {
  if (!Array.isArray(frames)) {
    return frames;
  }
  return frames.map((frame) => {
    const srcPath = frame.source && frame.source.path;
    if (!srcPath || !srcPath.toLowerCase().endsWith('.py')) {
      return frame;
    }
    const mapped = mapPyStackFrame(registry, srcPath, frame.line);
    if (!mapped) {
      return frame;
    }
    return {
      ...frame,
      line: mapped.pysLine,
      source: {
        ...frame.source,
        path: mapped.pysPath,
        name: path.basename(mapped.pysPath),
      },
    };
  });
}

function shouldHideVariableName(name, hidePrefixes) {
  if (!name || typeof name !== 'string') {
    return false;
  }
  const prefixes = hidePrefixes || DEFAULT_HIDE_PREFIXES;
  return prefixes.some((p) => name.startsWith(p));
}

/** Remap Locals/Variables display names; drop runtime helper clutter. */
function remapVariables(registry, variables) {
  if (!Array.isArray(variables)) {
    return variables;
  }
  const names = registry.names || {};
  const hidePrefixes = registry.hidePrefixes || DEFAULT_HIDE_PREFIXES;
  const out = [];
  for (const v of variables) {
    if (!v || typeof v.name !== 'string') {
      out.push(v);
      continue;
    }
    if (shouldHideVariableName(v.name, hidePrefixes)) {
      continue;
    }
    const display = names[v.name];
    if (display) {
      out.push({ ...v, name: display });
    } else {
      out.push(v);
    }
  }
  return out;
}

/**
 * Rewrite a bare Watch/evaluate expression from PYS name to emitted name.
 * Only bare identifiers (optional whitespace); leave complex expressions alone.
 */
function rewriteEvaluateExpression(registry, expression) {
  if (typeof expression !== 'string') {
    return expression;
  }
  const trimmed = expression.trim();
  if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(trimmed)) {
    return expression;
  }
  const emitted = registry.emittedByPys && registry.emittedByPys[trimmed];
  return emitted || expression;
}

module.exports = {
  DEFAULT_HIDE_PREFIXES,
  normalizePathKey,
  loadMapRegistry,
  mapPysBreakpoint,
  mapPyStackFrame,
  remapSetBreakpointsArgs,
  remapSetBreakpointsResponse,
  remapBreakpoint,
  remapStackFrames,
  shouldHideVariableName,
  remapVariables,
  rewriteEvaluateExpression,
};
