/**
 * Refactor dialogs as an integrated side editor tab (ViewColumn.Beside).
 * Source stays visible on the left; primary action label is "Refactor".
 * Preview step shows a live diff of how selected edits will rewrite the code.
 */
const vscode = require('vscode');
const { applySelectedEdits, buildLineDiff } = require('./refactor-preview');

function escapeHtml(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function shellHtml({ title, bodyInner, script }) {
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline';"/>
<style>
  :root {
    color-scheme: light dark;
    --bg: var(--vscode-editor-background, #1e1e1e);
    --fg: var(--vscode-editor-foreground, #ccc);
    --border: var(--vscode-widget-border, #555);
    --btn: var(--vscode-button-background, #0e639c);
    --btn-fg: var(--vscode-button-foreground, #fff);
    --btn-sec: var(--vscode-button-secondaryBackground, #3a3d41);
    --btn-sec-fg: var(--vscode-button-secondaryForeground, #fff);
    --input-bg: var(--vscode-input-background, #3c3c3c);
    --input-fg: var(--vscode-input-foreground, #ccc);
    --input-border: var(--vscode-input-border, #555);
    --muted: var(--vscode-descriptionForeground, #888);
    --focus: var(--vscode-focusBorder, #007fd4);
    --err: var(--vscode-errorForeground, #f44747);
  }
  html, body {
    margin: 0; padding: 0; height: 100%;
    font-family: var(--vscode-font-family, system-ui, sans-serif);
    font-size: var(--vscode-font-size, 13px);
    color: var(--fg);
    background: transparent !important;
  }
  .backdrop {
    min-height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 16px;
    box-sizing: border-box;
    background: color-mix(in srgb, var(--bg) 82%, transparent);
  }
  .dialog {
    width: min(560px, 100%);
    max-height: min(90vh, 720px);
    overflow: auto;
    background: var(--bg);
    color: var(--fg);
    border: 1px solid var(--border);
    border-radius: 8px;
    box-shadow: 0 12px 40px rgba(0,0,0,0.45);
    padding: 20px 22px 16px;
    box-sizing: border-box;
  }
  h1 { margin: 0 0 8px; font-size: 1.15rem; font-weight: 600; }
  .summary { margin: 0 0 10px; color: var(--muted); line-height: 1.4; }
  .why {
    margin: 0 0 14px;
    padding: 8px 10px;
    border-left: 3px solid var(--focus);
    background: rgba(127,127,127,0.12);
    line-height: 1.4;
  }
  .conflicts {
    margin: 0 0 14px;
    padding: 8px 10px;
    border: 1px solid var(--err);
    border-radius: 4px;
    color: var(--err);
  }
  .conflicts ul { margin: 6px 0 0; padding-left: 1.2em; }
  label.field { display: block; margin: 0 0 6px; font-weight: 500; }
  input[type="text"] {
    width: 100%;
    box-sizing: border-box;
    padding: 8px 10px;
    margin-bottom: 16px;
    background: var(--input-bg);
    color: var(--input-fg);
    border: 1px solid var(--input-border);
    border-radius: 4px;
  }
  input[type="text"]:focus { outline: 1px solid var(--focus); }
  .edits { margin: 0 0 10px; max-height: 140px; overflow: auto; }
  .edit-row {
    display: flex;
    gap: 8px;
    align-items: flex-start;
    padding: 6px 4px;
    border-bottom: 1px solid var(--border);
  }
  .edit-row:last-child { border-bottom: none; }
  .edit-row label { flex: 1; cursor: pointer; line-height: 1.35; }
  .edit-meta { color: var(--muted); font-size: 0.9em; }
  .preview-label {
    margin: 12px 0 6px;
    font-weight: 600;
  }
  .code-preview {
    margin: 0 0 14px;
    max-height: 320px;
    overflow: auto;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: color-mix(in srgb, var(--bg) 92%, #000);
    font-family: var(--vscode-editor-font-family, ui-monospace, Consolas, monospace);
    font-size: var(--vscode-editor-font-size, 12px);
    line-height: 1.45;
  }
  .code-preview .file-head {
    padding: 6px 10px;
    border-bottom: 1px solid var(--border);
    color: var(--muted);
    font-family: var(--vscode-font-family, system-ui, sans-serif);
    font-size: 0.9em;
  }
  .code-preview pre {
    margin: 0;
    padding: 8px 0;
    white-space: pre;
  }
  .diff-line { padding: 0 10px; display: block; }
  .diff-add { background: color-mix(in srgb, #3fa66b 22%, transparent); }
  .diff-del { background: color-mix(in srgb, #f44747 18%, transparent); }
  .diff-ctx { color: var(--muted); }
  .actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 8px;
  }
  button {
    border: none;
    border-radius: 4px;
    padding: 7px 14px;
    cursor: pointer;
    font: inherit;
  }
  button.primary { background: var(--btn); color: var(--btn-fg); }
  button.secondary { background: var(--btn-sec); color: var(--btn-sec-fg); }
  button:focus { outline: 1px solid var(--focus); outline-offset: 1px; }
</style>
</head>
<body>
  <div class="backdrop" id="backdrop">
    <div class="dialog" role="dialog" aria-modal="true" aria-label="${escapeHtml(title)}">
      ${bodyInner}
    </div>
  </div>
  <script>
    const vscode = acquireVsCodeApi();
    ${script}
  </script>
</body>
</html>`;
}

/**
 * @param {vscode.TextEditor|undefined} editor
 */
function captureEditor(editor) {
  if (!editor) {
    return null;
  }
  return {
    uri: editor.document.uri,
    viewColumn: editor.viewColumn || vscode.ViewColumn.One,
    selection: editor.selection,
  };
}

/**
 * @param {{ uri: vscode.Uri, viewColumn: vscode.ViewColumn, selection?: vscode.Selection }|null} snap
 */
async function restoreEditor(snap) {
  if (!snap || !snap.uri) {
    return null;
  }
  try {
    const ed = await vscode.window.showTextDocument(snap.uri, {
      viewColumn: snap.viewColumn,
      preview: false,
      preserveFocus: false,
    });
    if (snap.selection) {
      ed.selection = snap.selection;
      ed.revealRange(snap.selection, vscode.TextEditorRevealType.InCenterIfOutsideViewport);
    }
    return ed;
  } catch (_e) {
    return null;
  }
}

/**
 * Open dialog in a side editor tab (ViewColumn.Beside) so the .pys source
 * stays visible on the left. Never Active (replaces source) and never a
 * detached window.
 */
function openModalPanel(context, title, html, onMessage, editorSnap) {
  return new Promise((resolve) => {
    const panel = vscode.window.createWebviewPanel(
      'pysRefactorModal',
      title,
      {
        viewColumn: vscode.ViewColumn.Beside,
        preserveFocus: false,
      },
      {
        enableScripts: true,
        retainContextWhenHidden: false,
        localResourceRoots: [],
      },
    );
    let settled = false;
    const finish = async (value) => {
      if (settled) return;
      settled = true;
      try {
        panel.dispose();
      } catch (_e) {
        // already disposed
      }
      await restoreEditor(editorSnap);
      resolve(value);
    };
    panel.webview.html = html;
    panel.webview.onDidReceiveMessage(
      (msg) => {
        if (onMessage(msg, (v) => {
          void finish(v);
        }, panel)) {
          // finish scheduled
        }
      },
      undefined,
      context.subscriptions,
    );
    panel.onDidDispose(
      () => {
        if (!settled) {
          settled = true;
          void restoreEditor(editorSnap).then(() => resolve(null));
        }
      },
      undefined,
      context.subscriptions,
    );
  });
}

function showModalInput(context, opts, editorSnap) {
  const title = opts.title || 'Refactor';
  const prompt = opts.prompt || '';
  const value = opts.value || '';
  const placeholder = opts.placeholder || '';
  const html = shellHtml({
    title,
    bodyInner: `
      <h1>${escapeHtml(title)}</h1>
      <p class="summary">${escapeHtml(prompt)}</p>
      <label class="field" for="val">${escapeHtml(prompt)}</label>
      <input id="val" type="text" value="${escapeHtml(value)}" placeholder="${escapeHtml(placeholder)}" autofocus />
      <div class="actions">
        <button type="button" class="secondary" id="cancel">Cancel</button>
        <button type="button" class="primary" id="ok">Refactor</button>
      </div>
    `,
    script: `
      const input = document.getElementById('val');
      input.focus();
      input.select();
      function submit() {
        vscode.postMessage({ type: 'ok', value: input.value });
      }
      document.getElementById('ok').addEventListener('click', submit);
      document.getElementById('cancel').addEventListener('click', () => vscode.postMessage({ type: 'cancel' }));
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') submit();
        if (e.key === 'Escape') vscode.postMessage({ type: 'cancel' });
      });
    `,
  });
  return openModalPanel(
    context,
    title,
    html,
    (msg, resolve) => {
      if (msg.type === 'ok') {
        resolve(typeof msg.value === 'string' ? msg.value : '');
        return true;
      }
      if (msg.type === 'cancel') {
        resolve(null);
        return true;
      }
      return false;
    },
    editorSnap,
  );
}

function basenamePath(p) {
  const s = String(p || '');
  const i = Math.max(s.lastIndexOf('/'), s.lastIndexOf('\\'));
  return i >= 0 ? s.slice(i + 1) : s;
}

/**
 * @param {Record<string, string>} sources
 * @param {object[]} edits
 * @param {number[]|null} selectedIndices
 */
function renderCodePreviewHtml(sources, edits, selectedIndices) {
  if (!sources || !Object.keys(sources).length || !edits || !edits.length) {
    return '<p class="summary">No code preview.</p>';
  }
  const afterByFile = applySelectedEdits(sources, edits, selectedIndices);
  const files = Object.keys(afterByFile).sort();
  return files
    .map((file) => {
      const before = sources[file] || '';
      const after = afterByFile[file] || '';
      if (before === after) {
        return '';
      }
      const lines = buildLineDiff(before, after, 3)
        .map((row) => {
          const cls =
            row.kind === 'add' ? 'diff-add' : row.kind === 'del' ? 'diff-del' : 'diff-ctx';
          const prefix = row.kind === 'add' ? '+' : row.kind === 'del' ? '-' : ' ';
          return `<span class="diff-line ${cls}">${escapeHtml(prefix + row.text)}</span>`;
        })
        .join('\n');
      return `<div class="file-head">${escapeHtml(basenamePath(file))}</div><pre>${lines}</pre>`;
    })
    .filter(Boolean)
    .join('') || '<p class="summary">No textual change with the current selection.</p>';
}

function showModalPreview(context, opts, editorSnap) {
  const title = opts.title || 'Refactor preview';
  const summary = opts.summary || '';
  const why = opts.why || '';
  const conflicts = opts.conflicts || [];
  const edits = opts.edits || [];
  const hardBlocked = opts.hardBlocked === true;
  /** @type {Record<string, string>} */
  const sources = opts.sources || {};

  const conflictHtml = conflicts.length
    ? `<div class="conflicts"><strong>Conflicts</strong><ul>${conflicts
        .map(
          (c) =>
            `<li>${escapeHtml(c.message)}${
              c.file ? ` <span class="edit-meta">(${escapeHtml(String(c.file))}:${c.line || '?'})</span>` : ''
            }${c.soft ? ' <span class="edit-meta">(soft)</span>' : ''}</li>`,
        )
        .join('')}</ul></div>`
    : '';

  const initialIndices = edits
    .map((e, i) => (e.optional ? -1 : i))
    .filter((i) => i >= 0);
  const previewInner = hardBlocked
    ? ''
    : renderCodePreviewHtml(sources, edits, initialIndices);

  const editsHtml = edits
    .map((e, i) => {
      const checked = e.optional ? '' : 'checked';
      const disabled = hardBlocked ? 'disabled' : '';
      const label = e.label || `${e.kind || 'edit'} ${e.file || ''}:${e.line || ''}`;
      return `<div class="edit-row">
        <input type="checkbox" id="e${i}" data-i="${i}" ${checked} ${disabled}/>
        <label for="e${i}">${escapeHtml(label)}
          <div class="edit-meta">${escapeHtml(basenamePath(e.file || ''))}:${e.line || ''} ${e.optional ? '(optional)' : ''}</div>
        </label>
      </div>`;
    })
    .join('');

  const html = shellHtml({
    title,
    bodyInner: `
      <h1>${escapeHtml(title)}</h1>
      ${summary ? `<p class="summary">${escapeHtml(summary)}</p>` : ''}
      ${why ? `<div class="why"><strong>Why</strong><br/>${escapeHtml(why)}</div>` : ''}
      ${conflictHtml}
      ${
        hardBlocked
          ? '<p class="summary">Refactor blocked until conflicts are resolved.</p>'
          : `<div class="edits">${editsHtml || '<p class="summary">No edits.</p>'}</div>
             <div class="preview-label">Code after refactor</div>
             <div class="code-preview" id="codePreview">${previewInner}</div>`
      }
      <div class="actions">
        <button type="button" class="secondary" id="cancel">${hardBlocked ? 'Close' : 'Cancel'}</button>
        ${hardBlocked ? '' : '<button type="button" class="primary" id="ok">Refactor</button>'}
      </div>
    `,
    script: `
      const hardBlocked = ${hardBlocked ? 'true' : 'false'};
      function collect() {
        return Array.from(document.querySelectorAll('input[type=checkbox][data-i]'))
          .filter((el) => el.checked)
          .map((el) => Number(el.getAttribute('data-i')));
      }
      function refreshPreview() {
        if (hardBlocked) return;
        vscode.postMessage({ type: 'repreview', indices: collect() });
      }
      window.addEventListener('message', (ev) => {
        const msg = ev.data || {};
        if (msg.type === 'setPreview') {
          const el = document.getElementById('codePreview');
          if (el) el.innerHTML = msg.html;
        }
      });
      for (const el of document.querySelectorAll('input[type=checkbox][data-i]')) {
        el.addEventListener('change', refreshPreview);
      }
      const ok = document.getElementById('ok');
      if (ok) {
        ok.addEventListener('click', () => vscode.postMessage({ type: 'ok', indices: collect() }));
      }
      document.getElementById('cancel').addEventListener('click', () => vscode.postMessage({ type: 'cancel' }));
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') vscode.postMessage({ type: 'cancel' });
        if (e.key === 'Enter' && !hardBlocked && ok) {
          vscode.postMessage({ type: 'ok', indices: collect() });
        }
      });
    `,
  });

  return openModalPanel(
    context,
    title,
    html,
    (msg, resolve, panel) => {
      if (msg.type === 'repreview') {
        const indices = Array.isArray(msg.indices) ? msg.indices.map(Number) : [];
        const next = renderCodePreviewHtml(sources, edits, indices);
        void panel.webview.postMessage({ type: 'setPreview', html: next });
        return false;
      }
      if (msg.type === 'ok') {
        resolve(Array.isArray(msg.indices) ? msg.indices.map(Number) : []);
        return true;
      }
      if (msg.type === 'cancel') {
        resolve(null);
        return true;
      }
      return false;
    },
    editorSnap,
  );
}

module.exports = {
  captureEditor,
  restoreEditor,
  showModalInput,
  showModalPreview,
};
