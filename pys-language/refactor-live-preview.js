/**
 * Live refactor preview in the editor window:
 * temporarily applies edits, paints orange (old) / blue (new) spans.
 * Accept / Reject stay on the changed line (CodeLens) + sticky input bar
 * (no disappearing toast).
 */
const vscode = require('vscode');
const { applyEditsToText, computeAfterSpans } = require('./refactor-preview');

/**
 * @param {string} filePath
 * @param {string} otherPath
 */
function sameFsPath(filePath, otherPath) {
  try {
    return vscode.Uri.file(filePath).fsPath === vscode.Uri.file(otherPath).fsPath;
  } catch (_e) {
    return filePath === otherPath;
  }
}

/**
 * @param {string} s
 * @param {number} max
 */
function previewLabel(s, max = 48) {
  const one = String(s).replace(/\r\n/g, '\n').replace(/\n/g, '↵').replace(/\t/g, '→');
  if (one.length <= max) return one;
  return `${one.slice(0, max - 1)}…`;
}

/** @type {vscode.CodeLensProvider|null} */
let lensProvider = null;
/** @type {vscode.EventEmitter<void>|null} */
let lensEmitter = null;
/** @type {vscode.CodeLens[]} */
let activeLenses = [];

/**
 * @param {vscode.ExtensionContext} context
 */
function ensureCodeLensProvider(context) {
  if (lensProvider) {
    return;
  }
  lensEmitter = new vscode.EventEmitter();
  lensProvider = {
    onDidChangeCodeLenses: lensEmitter.event,
    provideCodeLenses() {
      return activeLenses;
    },
    resolveCodeLens(lens) {
      return lens;
    },
  };
  context.subscriptions.push(
    vscode.languages.registerCodeLensProvider({ language: 'pys' }, lensProvider),
    lensEmitter,
  );
}

/**
 * @param {vscode.CodeLens[]} lenses
 */
function setActiveLenses(lenses) {
  activeLenses = lenses;
  if (lensEmitter) {
    lensEmitter.fire();
  }
}

/**
 * Sticky Accept / Reject at the edit site (CodeLens) + ignoreFocusOut input bar.
 * No toast — those disappear too quickly for inspection.
 *
 * @param {vscode.ExtensionContext} context
 * @param {{ anchor: vscode.Range, title?: string, uri?: vscode.Uri }} opts
 * @returns {Promise<'accept'|'reject'>}
 */
function waitAcceptReject(context, opts) {
  ensureCodeLensProvider(context);
  const token = `pys.livePreview.${Date.now()}.${Math.random().toString(36).slice(2, 8)}`;
  const acceptCmd = `${token}.accept`;
  const rejectCmd = `${token}.reject`;
  const title = opts.title || 'Refactor';
  const anchor = opts.anchor;

  const box = vscode.window.createInputBox();
  box.title = `${title} — live preview`;
  box.prompt = 'Orange = old · blue = new. Inspect freely, then Accept or Reject.';
  box.placeholder = 'Accept keeps changes · Reject restores';
  box.ignoreFocusOut = true;
  box.busy = false;
  box.value = '';
  box.buttons = [
    {
      iconPath: new vscode.ThemeIcon('check'),
      tooltip: 'Accept',
    },
    {
      iconPath: new vscode.ThemeIcon('close'),
      tooltip: 'Reject',
    },
  ];
  // Keep focus on the editor for inspection; box stays visible via ignoreFocusOut.
  box.show();

  setActiveLenses([
    new vscode.CodeLens(anchor, {
      title: '$(check) Accept',
      command: acceptCmd,
      tooltip: 'Keep the live preview changes',
    }),
    new vscode.CodeLens(anchor, {
      title: '$(close) Reject',
      command: rejectCmd,
      tooltip: 'Restore the text before preview',
    }),
  ]);

  return new Promise((resolve) => {
    let done = false;
    const finish = (choice) => {
      if (done) return;
      done = true;
      setActiveLenses([]);
      for (const d of disposables) {
        try {
          d.dispose();
        } catch (_e) {
          // ignore
        }
      }
      try {
        box.hide();
        box.dispose();
      } catch (_e) {
        // ignore
      }
      resolve(choice);
    };

    const disposables = [
      vscode.commands.registerCommand(acceptCmd, () => finish('accept')),
      vscode.commands.registerCommand(rejectCmd, () => finish('reject')),
      box.onDidTriggerButton((btn) => {
        const idx = box.buttons.indexOf(btn);
        if (idx === 0) finish('accept');
        else if (idx === 1) finish('reject');
      }),
      box.onDidAccept(() => finish('accept')),
      box.onDidHide(() => {
        // Esc / click-away — only reject if we did not already Accept.
        if (!done) finish('reject');
      }),
    ];
    context.subscriptions.push(...disposables);
  });
}

/**
 * Live-apply plan edits in open editors; orange old / blue new; Accept keeps, Reject restores.
 *
 * @param {vscode.ExtensionContext} context
 * @param {{
 *   title?: string,
 *   summary?: string,
 *   why?: string,
 *   conflicts?: Array<{ message?: string, soft?: boolean }>,
 *   edits?: object[],
 *   hardBlocked?: boolean,
 *   message?: string,
 * }} opts
 * @param {vscode.TextDocument} document
 * @returns {Promise<{ indices: number[], alreadyApplied: boolean }|null>}
 */
async function showLivePreview(context, opts, document) {
  const title = opts.title || 'Refactor';
  const edits = opts.edits || [];
  const conflicts = opts.conflicts || [];
  const hard = conflicts.filter((c) => !c.soft);
  const hardBlocked = Boolean(opts.hardBlocked);

  if (hardBlocked) {
    const detail = hard.map((c) => c.message).filter(Boolean).join('\n')
      || opts.message
      || 'Refactor blocked.';
    await vscode.window.showErrorMessage(`${title}: ${detail}`);
    return null;
  }

  if (!edits.length) {
    // Quiet — nothing to preview.
    return null;
  }

  /** @type {Map<string, object[]>} */
  const byFile = new Map();
  for (const e of edits) {
    if (!e || !e.file) continue;
    const key = vscode.Uri.file(e.file).fsPath;
    if (!byFile.has(key)) byFile.set(key, []);
    byFile.get(key).push(e);
  }

  /** @type {Array<{ editor: vscode.TextEditor, original: string, after: string, fileEdits: object[] }>} */
  const sessions = [];

  for (const [fsPath, fileEdits] of byFile) {
    const uri = vscode.Uri.file(fsPath);
    let doc;
    try {
      if (sameFsPath(fsPath, document.uri.fsPath)) {
        doc = document;
      } else {
        doc = await vscode.workspace.openTextDocument(uri);
      }
      const editor = await vscode.window.showTextDocument(doc, {
        preview: false,
        preserveFocus: sessions.length > 0,
        viewColumn: sessions.length === 0
          ? vscode.ViewColumn.Active
          : vscode.ViewColumn.Beside,
      });
      const original = doc.getText();
      const after = applyEditsToText(original, fileEdits);
      sessions.push({ editor, original, after, fileEdits });
    } catch (_e) {
      // skip unreadable peers
    }
  }

  if (!sessions.length) {
    await vscode.window.showErrorMessage(`${title}: no openable files for preview.`);
    return null;
  }

  const oldLineDeco = vscode.window.createTextEditorDecorationType({
    isWholeLine: true,
    backgroundColor: 'rgba(255, 140, 0, 0.12)',
    overviewRulerColor: 'rgba(255, 140, 0, 0.9)',
    overviewRulerLane: vscode.OverviewRulerLane.Left,
  });
  const newSpanDeco = vscode.window.createTextEditorDecorationType({
    backgroundColor: 'rgba(64, 140, 255, 0.45)',
    borderRadius: '2px',
    overviewRulerColor: 'rgba(64, 140, 255, 0.95)',
    overviewRulerLane: vscode.OverviewRulerLane.Center,
    fontWeight: 'bold',
  });
  const oldGhostDeco = vscode.window.createTextEditorDecorationType({
    overviewRulerColor: 'rgba(255, 140, 0, 0.95)',
    overviewRulerLane: vscode.OverviewRulerLane.Center,
  });

  const clearDecos = () => {
    for (const s of sessions) {
      try {
        s.editor.setDecorations(oldLineDeco, []);
        s.editor.setDecorations(newSpanDeco, []);
        s.editor.setDecorations(oldGhostDeco, []);
      } catch (_e) {
        // ignore
      }
    }
    oldLineDeco.dispose();
    newSpanDeco.dispose();
    oldGhostDeco.dispose();
  };

  const restoreAll = async () => {
    for (const s of sessions) {
      const doc = s.editor.document;
      const full = new vscode.Range(
        doc.positionAt(0),
        doc.positionAt(doc.getText().length),
      );
      await s.editor.edit((eb) => {
        eb.replace(full, s.original);
      }, { undoStopBefore: true, undoStopAfter: true });
    }
  };

  try {
    /** @type {vscode.Range|null} */
    let firstReveal = null;

    for (const s of sessions) {
      const doc = s.editor.document;
      const full = new vscode.Range(
        doc.positionAt(0),
        doc.positionAt(doc.getText().length),
      );
      const ok = await s.editor.edit((eb) => {
        eb.replace(full, s.after);
      }, { undoStopBefore: true, undoStopAfter: true });
      if (!ok) {
        clearDecos();
        await restoreAll();
        await vscode.window.showErrorMessage(`${title}: could not apply live preview.`);
        return null;
      }

      const spans = computeAfterSpans(s.original, s.fileEdits);
      /** @type {vscode.DecorationOptions[]} */
      const lineOpts = [];
      /** @type {vscode.DecorationOptions[]} */
      const newOpts = [];
      /** @type {vscode.DecorationOptions[]} */
      const ghostOpts = [];

      for (const span of spans) {
        const start = doc.positionAt(Math.min(span.startAfter, doc.getText().length));
        const end = doc.positionAt(Math.min(span.endAfter, doc.getText().length));
        const range = start.isEqual(end)
          ? new vscode.Range(start, start)
          : new vscode.Range(start, end);

        lineOpts.push({
          range: new vscode.Range(start.line, 0, start.line, 0),
          hoverMessage: new vscode.MarkdownString(
            `**Line changed**\n\n- old: \`${previewLabel(span.oldText, 80) || '∅'}\`\n`
            + `- new: \`${previewLabel(span.newText, 80) || '∅'}\``,
          ),
        });

        newOpts.push({
          range,
          hoverMessage: new vscode.MarkdownString(
            `**Proposed (live)**\n\n\`\`\`\n${span.newText || '(deleted)'}\n\`\`\``,
          ),
        });

        if (span.oldText) {
          ghostOpts.push({
            range: new vscode.Range(start, start),
            hoverMessage: new vscode.MarkdownString(
              `**Old span**\n\n\`\`\`\n${span.oldText}\n\`\`\``,
            ),
            renderOptions: {
              before: {
                contentText: ` ${previewLabel(span.oldText)} `,
                color: '#c45c00',
                backgroundColor: 'rgba(255, 140, 0, 0.35)',
                fontStyle: 'italic',
                textDecoration: 'line-through',
                margin: '0 6px 0 0',
              },
            },
          });
        }

        if (!firstReveal) {
          firstReveal = range;
        }
      }

      s.editor.setDecorations(oldLineDeco, lineOpts);
      s.editor.setDecorations(newSpanDeco, newOpts);
      s.editor.setDecorations(oldGhostDeco, ghostOpts);
    }

    if (firstReveal && sessions[0]) {
      sessions[0].editor.revealRange(firstReveal, vscode.TextEditorRevealType.InCenterIfOutsideViewport);
      sessions[0].editor.selection = new vscode.Selection(firstReveal.start, firstReveal.start);
    }

    const anchor = firstReveal || new vscode.Range(0, 0, 0, 0);
    const choice = await waitAcceptReject(context, { anchor, title });
    clearDecos();

    if (choice !== 'accept') {
      await restoreAll();
      return null;
    }

    return {
      indices: edits.map((_, i) => i),
      alreadyApplied: true,
    };
  } catch (err) {
    clearDecos();
    setActiveLenses([]);
    try {
      await restoreAll();
    } catch (_e) {
      // ignore
    }
    throw err;
  }
}

/** @deprecated use showLivePreview */
async function showInlinePreview(context, opts, document) {
  const result = await showLivePreview(context, opts, document);
  return result ? result.indices : null;
}

module.exports = {
  showLivePreview,
  showInlinePreview,
  sameFsPath,
  ensureCodeLensProvider,
};
