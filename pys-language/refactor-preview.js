/**
 * Client-side apply of RefactorPlan edits (mirrors transpiler/refactor/apply.py)
 * so the preview dialog can show the resulting code before WorkspaceEdit.
 */

/**
 * @param {string} text
 * @param {Array<{
 *   line: number, column: number, end_line?: number, end_column?: number,
 *   new_text?: string, kind?: string
 * }>} edits
 * @returns {string}
 */
function applyEditsToText(text, edits) {
  const lines = splitKeepEnds(text);
  const ordered = [...edits].sort((a, b) => {
    const al = a.line || 0;
    const bl = b.line || 0;
    if (al !== bl) return bl - al;
    const ac = a.column || 0;
    const bc = b.column || 0;
    if (ac !== bc) return bc - ac;
    const ael = a.end_line || al;
    const bel = b.end_line || bl;
    if (ael !== bel) return bel - ael;
    return (b.end_column || bc) - (a.end_column || ac);
  });

  for (const ed of ordered) {
    if ((ed.kind || 'replace') === 'insert') {
      let lineI = Math.max((ed.line || 1) - 1, 0);
      const col = Math.max((ed.column || 1) - 1, 0);
      while (lines.length <= lineI) {
        lines.push('\n');
      }
      const { body, nl } = stripNl(lines[lineI]);
      lines[lineI] = body.slice(0, col) + (ed.new_text || '') + body.slice(col) + nl;
      continue;
    }
    const startLine = Math.max((ed.line || 1) - 1, 0);
    const endLine = Math.max((ed.end_line || ed.line || 1) - 1, 0);
    const startCol = Math.max((ed.column || 1) - 1, 0);
    const endCol = Math.max((ed.end_column || ed.column || 1) - 1, 0);
    if (startLine === endLine) {
      const { body, nl } = stripNl(lines[startLine] || '');
      lines[startLine] = body.slice(0, startCol) + (ed.new_text || '') + body.slice(endCol) + nl;
    } else {
      const first = stripNl(lines[startLine] || '');
      const last = stripNl(lines[endLine] || '');
      const merged =
        first.body.slice(0, startCol) + (ed.new_text || '') + last.body.slice(endCol) + last.nl;
      lines.splice(startLine, endLine - startLine + 1, merged);
    }
  }
  return lines.join('');
}

/**
 * @param {Record<string, string>} sources path → original text
 * @param {Array<{file: string} & object>} edits
 * @param {number[]|null|undefined} selectedIndices null/undefined = all
 * @returns {Record<string, string>} path → after text
 */
function applySelectedEdits(sources, edits, selectedIndices) {
  const selected =
    selectedIndices == null
      ? edits.map((_, i) => i)
      : selectedIndices.map(Number).filter((i) => i >= 0 && i < edits.length);
  /** @type {Record<string, typeof edits>} */
  const byFile = {};
  for (const i of selected) {
    const e = edits[i];
    if (!e || !e.file) continue;
    (byFile[e.file] || (byFile[e.file] = [])).push(e);
  }
  /** @type {Record<string, string>} */
  const out = {};
  for (const [file, text] of Object.entries(sources)) {
    const fileEdits = byFile[file];
    out[file] = fileEdits && fileEdits.length ? applyEditsToText(text, fileEdits) : text;
  }
  for (const file of Object.keys(byFile)) {
    if (!(file in out)) {
      out[file] = applyEditsToText(sources[file] || '', byFile[file]);
    }
  }
  return out;
}

/**
 * Line-based unified hunks for preview (context lines around changes).
 * @param {string} before
 * @param {string} after
 * @param {number} [context=3]
 * @returns {Array<{kind: 'ctx'|'add'|'del', text: string}>}
 */
function buildLineDiff(before, after, context = 3) {
  const a = before.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');
  const b = after.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');
  // Drop trailing empty from final newline split
  if (a.length && a[a.length - 1] === '') a.pop();
  if (b.length && b[b.length - 1] === '') b.pop();

  // Myers-ish LCS via DP for small teaching files
  const n = a.length;
  const m = b.length;
  const dp = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  /** @type {Array<{kind: 'ctx'|'add'|'del', text: string, ai?: number, bi?: number}>} */
  const raw = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      raw.push({ kind: 'ctx', text: a[i], ai: i, bi: j });
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      raw.push({ kind: 'del', text: a[i], ai: i });
      i++;
    } else {
      raw.push({ kind: 'add', text: b[j], bi: j });
      j++;
    }
  }
  while (i < n) {
    raw.push({ kind: 'del', text: a[i], ai: i });
    i++;
  }
  while (j < m) {
    raw.push({ kind: 'add', text: b[j], bi: j });
    j++;
  }

  const changeIdx = [];
  for (let k = 0; k < raw.length; k++) {
    if (raw[k].kind !== 'ctx') changeIdx.push(k);
  }
  if (!changeIdx.length) {
    return [{ kind: 'ctx', text: '(no textual change)' }];
  }
  const keep = new Set();
  for (const idx of changeIdx) {
    for (let k = Math.max(0, idx - context); k <= Math.min(raw.length - 1, idx + context); k++) {
      keep.add(k);
    }
  }
  /** @type {Array<{kind: 'ctx'|'add'|'del', text: string}>} */
  const out = [];
  let last = -2;
  for (let k = 0; k < raw.length; k++) {
    if (!keep.has(k)) continue;
    if (last >= 0 && k > last + 1) {
      out.push({ kind: 'ctx', text: '…' });
    }
    out.push({ kind: raw[k].kind, text: raw[k].text });
    last = k;
  }
  return out;
}

function splitKeepEnds(text) {
  if (!text) return [];
  const out = [];
  let i = 0;
  while (i < text.length) {
    const n = text.indexOf('\n', i);
    if (n < 0) {
      out.push(text.slice(i));
      break;
    }
    // include \n; if \r precedes, keep it with the line
    out.push(text.slice(i, n + 1));
    i = n + 1;
  }
  return out;
}

function stripNl(line) {
  if (line.endsWith('\r\n')) return { body: line.slice(0, -2), nl: '\r\n' };
  if (line.endsWith('\n')) return { body: line.slice(0, -1), nl: '\n' };
  return { body: line, nl: '' };
}

/**
 * @param {string} text
 * @param {number} line1 1-based
 * @param {number} col1 1-based
 * @returns {number}
 */
function posToOffset(text, line1, col1) {
  let line = 1;
  let col = 1;
  for (let i = 0; i < text.length; i++) {
    if (line === line1 && col === col1) {
      return i;
    }
    if (text[i] === '\n') {
      line += 1;
      col = 1;
    } else {
      col += 1;
    }
  }
  if (line === line1 && col === col1) {
    return text.length;
  }
  return text.length;
}

/**
 * Map each edit to its span in the *after* text (top-down with delta).
 * @param {string} original
 * @param {object[]} edits
 * @returns {Array<{
 *   editIndex: number,
 *   startAfter: number,
 *   endAfter: number,
 *   oldText: string,
 *   newText: string,
 * }>}
 */
function computeAfterSpans(original, edits) {
  const sorted = edits.map((e, i) => ({ e, i })).sort((a, b) => {
    const al = a.e.line || 1;
    const bl = b.e.line || 1;
    if (al !== bl) return al - bl;
    return (a.e.column || 1) - (b.e.column || 1);
  });
  let delta = 0;
  /** @type {ReturnType<typeof computeAfterSpans>} */
  const spans = [];
  for (const { e, i } of sorted) {
    const kind = e.kind || 'replace';
    const startOrig = posToOffset(original, e.line || 1, e.column || 1);
    let endOrig = startOrig;
    if (kind !== 'insert') {
      endOrig = posToOffset(
        original,
        e.end_line || e.line || 1,
        e.end_column || e.column || 1,
      );
    }
    if (endOrig < startOrig) {
      endOrig = startOrig;
    }
    const oldText = original.slice(startOrig, endOrig);
    const newText = e.new_text == null ? '' : String(e.new_text);
    const startAfter = startOrig + delta;
    const endAfter = startAfter + newText.length;
    spans.push({
      editIndex: i,
      startAfter,
      endAfter,
      oldText,
      newText,
    });
    delta += newText.length - (endOrig - startOrig);
  }
  return spans;
}

module.exports = {
  applyEditsToText,
  applySelectedEdits,
  buildLineDiff,
  posToOffset,
  computeAfterSpans,
};
