/**
 * Editor context key `pys.inClassBody` for Extract Method vs Extract Function.
 * Heuristic: caret is after an unmatched `{` that follows a `class`/`entity` header
 * more recently than a top-level `function`/`func`.
 */

/**
 * @param {string} text
 * @param {number} offset 0-based
 * @returns {boolean}
 */
function isOffsetInClassBody(text, offset) {
  const head = text.slice(0, Math.max(0, Math.min(offset, text.length)));
  let depth = 0;
  let classDepth = 0;
  let i = 0;
  while (i < head.length) {
    const ch = head[i];
    if (ch === '"' || ch === "'") {
      const q = ch;
      i += 1;
      while (i < head.length) {
        if (head[i] === '\\') {
          i += 2;
          continue;
        }
        if (head[i] === q) {
          i += 1;
          break;
        }
        i += 1;
      }
      continue;
    }
    if (ch === '/' && head[i + 1] === '/') {
      i += 2;
      while (i < head.length && head[i] !== '\n') {
        i += 1;
      }
      continue;
    }
    if (ch === '{') {
      // Look back for class/entity vs function on this "header"
      const before = head.slice(0, i);
      const lineStart = before.lastIndexOf('\n') + 1;
      const header = before.slice(lineStart, i);
      const isType =
        /\b(class|entity)\b/.test(header) && !/\b(function|func)\b/.test(header);
      depth += 1;
      if (isType && classDepth === 0) {
        classDepth = depth;
      }
      i += 1;
      continue;
    }
    if (ch === '}') {
      if (classDepth && depth === classDepth) {
        classDepth = 0;
      }
      depth = Math.max(0, depth - 1);
      i += 1;
      continue;
    }
    i += 1;
  }
  return classDepth > 0 && depth >= classDepth;
}

/**
 * @param {typeof import('vscode')} vscodeApi
 * @param {import('vscode').ExtensionContext} context
 */
function registerInClassBodyContext(vscodeApi, context) {
  async function sync(editor) {
    let inside = false;
    if (editor && editor.document && (editor.document.languageId === 'pys' || /\.pys$/i.test(editor.document.fileName || ''))) {
      const doc = editor.document;
      const offset = doc.offsetAt(editor.selection.active);
      inside = isOffsetInClassBody(doc.getText(), offset);
    }
    await vscodeApi.commands.executeCommand('setContext', 'pys.inClassBody', inside);
  }

  void sync(vscodeApi.window.activeTextEditor);
  context.subscriptions.push(
    vscodeApi.window.onDidChangeActiveTextEditor((e) => {
      void sync(e);
    }),
    vscodeApi.window.onDidChangeTextEditorSelection((e) => {
      if (e.textEditor === vscodeApi.window.activeTextEditor) {
        void sync(e.textEditor);
      }
    }),
    vscodeApi.workspace.onDidChangeTextDocument((e) => {
      const ed = vscodeApi.window.activeTextEditor;
      if (ed && ed.document === e.document) {
        void sync(ed);
      }
    }),
  );
}

module.exports = {
  isOffsetInClassBody,
  registerInClassBodyContext,
};
