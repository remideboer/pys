/**
 * PYS ↔ Python line-map helpers for Debug Adapter remapping (F-004 / UX maturity).
 * Pure functions — unit-tested without VS Code.
 */
const fs = require('fs');
const path = require('path');

const DEFAULT_HIDE_PREFIXES = ['_pys_', '__pys_', '_Pys'];

function isWindowsAbsolutePath(filePath) {
  return /^[A-Za-z]:[\\/]/.test(filePath) || filePath.startsWith('\\\\');
}

function normalizePathKey(filePath) {
  if (!filePath) {
    return '';
  }
  // POSIX path.resolve() treats `C:\...` as relative and prefixes cwd. Keep
  // Windows absolute DAP/test paths stable when the host is Linux/macOS CI.
  if (process.platform !== 'win32' && isWindowsAbsolutePath(filePath)) {
    return filePath.replace(/\//g, '\\').toLowerCase();
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

/** Map only a generated line that has its own PYS statement origin. */
function mapExactPyStackFrame(registry, pyPath, pyLine) {
  const record = registry.byPy.get(normalizePathKey(pyPath));
  if (!record || !record.pyToPys.has(pyLine)) {
    return null;
  }
  return { pysPath: record.pys, pysLine: record.pyToPys.get(pyLine) };
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
    const logMessage = rewriteLogMessageExpressions(registry, bp.logMessage);
    if (!mapped) {
      return logMessage === bp.logMessage ? bp : { ...bp, logMessage };
    }
    return { ...bp, line: mapped.pyLine, logMessage };
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

/** Translate exact backend absence spelling to the PYS source spelling. */
function formatPysDebugValue(value) {
  return value === 'None' ? 'null' : value;
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
    const formatted = { ...v, value: formatPysDebugValue(v.value) };
    // Prefer pysmap `names` before hidePrefixes — brace-scoped locals are
    // emitted as `_pys_bN_*` (CER-015) but must still display as the PYS name.
    const display = names[v.name];
    if (display) {
      out.push({ ...formatted, name: display });
      continue;
    }
    if (shouldHideVariableName(v.name, hidePrefixes)) {
      continue;
    }
    out.push(formatted);
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

/**
 * Rewrite identifiers inside an expression using the PYS→emitted name table.
 * Used for logpoint `{...}` bodies (may be more than a bare name).
 */
function rewriteExpressionIdentifiers(registry, expression) {
  if (typeof expression !== 'string' || !expression) {
    return expression;
  }
  const map = registry.emittedByPys || {};
  if (!Object.keys(map).length) {
    return expression;
  }
  return expression.replace(/\b[A-Za-z_][A-Za-z0-9_]*\b/g, (id) => map[id] || id);
}

/**
 * Rewrite `{expr}` segments in a DAP logpoint message to emitted Python names.
 * Plain text outside braces is unchanged. See VS Code / IntelliJ logpoints.
 */
function rewriteLogMessageExpressions(registry, logMessage) {
  if (typeof logMessage !== 'string' || !logMessage) {
    return logMessage;
  }
  return logMessage.replace(/\{([^{}]*)\}/g, (_, inner) => `{${rewriteExpressionIdentifiers(registry, inner)}}`);
}

/**
 * Find identifier sites for inline debug values (IntelliJ-style end-of-line hints).
 *
 * @param {string} sourceText full document text
 * @param {number} stoppedLine1Based inclusive max source line (1-based)
 * @param {{ keywords?: string[], types?: string[] }} [options]
 * @returns {{ line: number, column: number, length: number, name: string }[]}
 *   line/column are 0-based (VS Code Range).
 */
function collectInlineValueSites(sourceText, stoppedLine1Based, options = {}) {
  const skip = new Set([...(options.keywords || []), ...(options.types || [])]);
  const lines = String(sourceText || '').split(/\r?\n/);
  const maxLine = Math.min(lines.length, Math.max(0, Number(stoppedLine1Based) || 0));
  const sites = [];
  for (let i = 0; i < maxLine; i++) {
    let line = lines[i];
    const hash = line.indexOf('#');
    if (hash >= 0) {
      line = line.slice(0, hash);
    }
    // Blank out string literals so names inside quotes are ignored.
    line = line.replace(/"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'/g, (m) => ' '.repeat(m.length));
    const re = /[A-Za-z_][A-Za-z0-9_]*/g;
    const seen = new Set();
    let match;
    while ((match = re.exec(line)) !== null) {
      const name = match[0];
      if (skip.has(name) || seen.has(name)) {
        continue;
      }
      seen.add(name);
      sites.push({
        line: i,
        column: match.index,
        length: name.length,
        name,
      });
    }
  }
  return sites;
}

/**
 * Keep only identifier sites whose name is in the current frame scope set.
 * @param {{ name: string }[]} sites
 * @param {Set<string>|Map<string, unknown>|string[]} scopeNames
 */
function filterInlineValueSitesByScope(sites, scopeNames) {
  if (!Array.isArray(sites) || !sites.length) {
    return [];
  }
  let allowed;
  if (scopeNames instanceof Set) {
    allowed = scopeNames;
  } else if (scopeNames instanceof Map) {
    // Map default iteration yields [k,v] pairs — use .keys() explicitly.
    allowed = new Set(scopeNames.keys());
  } else if (Array.isArray(scopeNames)) {
    allowed = new Set(scopeNames);
  } else {
    allowed = new Set();
  }
  if (!allowed.size) {
    return [];
  }
  return sites.filter((s) => s && allowed.has(s.name));
}

module.exports = {
  DEFAULT_HIDE_PREFIXES,
  isWindowsAbsolutePath,
  normalizePathKey,
  loadMapRegistry,
  mapPysBreakpoint,
  mapPyStackFrame,
  mapExactPyStackFrame,
  remapSetBreakpointsArgs,
  remapSetBreakpointsResponse,
  remapBreakpoint,
  remapStackFrames,
  shouldHideVariableName,
  formatPysDebugValue,
  remapVariables,
  rewriteEvaluateExpression,
  rewriteExpressionIdentifiers,
  rewriteLogMessageExpressions,
  collectInlineValueSites,
  filterInlineValueSitesByScope,
};
