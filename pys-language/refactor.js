/**
 * Educational refactoring: plan via IDE process; rename uses the at-cursor
 * rename widget; other ops may prompt for a name; live orange/blue preview
 * with sticky Accept/Reject (CodeLens + ignoreFocusOut bar).
 */
const vscode = require('vscode');
const {
  buildIdeProcessSpec,
  resolveWorkspaceFile,
  runJsonProcess,
} = require('./ide-process');
const {
  captureEditor,
  showModalInput,
} = require('./refactor-modal');
const {
  showLivePreview,
  ensureCodeLensProvider,
} = require('./refactor-live-preview');

const PYTHON = process.platform === 'win32' ? 'python' : 'python3';

/**
 * @param {vscode.ExtensionContext} context
 * @param {{ runJsonProcess?: typeof runJsonProcess }} [deps]
 */
function registerRefactoring(context, deps = {}) {
  const runJson = deps.runJsonProcess || runJsonProcess;
  ensureCodeLensProvider(context);

  async function callRefactorPlan(document, op, extraArgs) {
    const workspace = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
    if (!workspace) {
      vscode.window.showErrorMessage('PYS refactor: open a workspace folder.');
      return null;
    }
    const contained = resolveWorkspaceFile(workspace.uri.fsPath, document.uri.fsPath);
    if (!contained) {
      vscode.window.showErrorMessage('PYS refactor: file is outside the workspace.');
      return null;
    }
    const args = ['--refactor-plan', op, contained, '--stdin', ...extraArgs];
    const envSpec = buildIdeProcessSpec(context.extensionPath, workspace.uri.fsPath, args);
    try {
      return await runJson(PYTHON, envSpec.args, envSpec.options, {
        stdin: document.getText(),
        timeoutMs: 15_000,
      });
    } catch (err) {
      vscode.window.showErrorMessage(`PYS refactor failed: ${err.message || err}`);
      return null;
    }
  }

  function posArgs(position) {
    return [
      '--line',
      String(position.line + 1),
      '--column',
      String(position.character + 1),
    ];
  }

  /**
   * @param {object[]} edits
   * @param {Iterable<number>} selectedIndices
   */
  function workspaceEditFromPlan(edits, selectedIndices) {
    const selected = new Set([...selectedIndices].map(Number));
    const we = new vscode.WorkspaceEdit();
    for (let i = 0; i < edits.length; i++) {
      if (!selected.has(i)) {
        continue;
      }
      const e = edits[i];
      const uri = vscode.Uri.file(e.file);
      const start = new vscode.Position(Math.max(e.line - 1, 0), Math.max(e.column - 1, 0));
      const end = new vscode.Position(
        Math.max((e.end_line || e.line) - 1, 0),
        Math.max((e.end_column || e.column) - 1, 0),
      );
      if (e.kind === 'insert') {
        we.insert(uri, start, e.new_text || '');
      } else {
        we.replace(uri, new vscode.Range(start, end), e.new_text || '');
      }
    }
    return we;
  }

  async function previewAndApply(document, plan, editorSnap) {
    if (!plan) {
      return;
    }
    const title = plan.title || plan.catalog_id || 'Refactor';
    const why = plan.why || '';
    const conflicts = plan.conflicts || [];
    const hard = conflicts.filter((c) => !c.soft);
    const hardBlocked = hard.length > 0 && !plan.ok;
    const edits = plan.edits || [];

    const chosen = await showLivePreview(
      context,
      {
        title,
        summary: plan.summary || '',
        why,
        conflicts,
        edits,
        hardBlocked,
        message: plan.message || (!edits.length ? 'Nothing to change.' : ''),
      },
      document,
    );
    if (chosen === null || hardBlocked) {
      return;
    }
    if (!chosen.indices.length) {
      vscode.window.showWarningMessage(`${title}: no edit sites selected.`);
      return;
    }

    if (chosen.alreadyApplied) {
      try {
        await vscode.window.showTextDocument(document.uri, {
          viewColumn: editorSnap?.viewColumn || vscode.ViewColumn.Active,
          preview: false,
        });
      } catch (_e) {
        // ignore
      }
      // No toast — Accept already confirmed in the sticky preview UI.
      return;
    }

    const we = workspaceEditFromPlan(edits, chosen.indices);
    const ok = await vscode.workspace.applyEdit(we);
    if (!ok) {
      vscode.window.showErrorMessage(`${title}: apply failed (WorkspaceEdit rejected).`);
      return;
    }
    try {
      await vscode.window.showTextDocument(document.uri, {
        viewColumn: editorSnap?.viewColumn || vscode.ViewColumn.Active,
        preview: false,
      });
    } catch (_e) {
      // ignore
    }
  }

  /**
   * @param {string} op
   * @param {vscode.TextDocument} document
   * @param {vscode.Selection} selection
   * @param {ReturnType<typeof captureEditor>} editorSnap
   * @param {(doc: vscode.TextDocument, sel: vscode.Selection) => string[] | Promise<string[]|null>} extraBuilder
   */
  async function runOp(op, document, selection, editorSnap, extraBuilder) {
    // After a Beside name prompt, active editor.selection is often wrong —
    // always prefer the pre-modal snap.
    const sel = (editorSnap && editorSnap.selection) || selection;
    const extra = await extraBuilder(document, sel);
    if (extra === null) {
      return;
    }
    const plan = await callRefactorPlan(document, op, extra);
    await previewAndApply(document, plan, editorSnap);
  }

  function requirePysEditor() {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document.languageId !== 'pys') {
      vscode.window.showErrorMessage('PYS refactor: open a .pys editor tab first.');
      return null;
    }
    return editor;
  }

  const commands = [
    ['pys.refactor.rename', async () => {
      const editor = requirePysEditor();
      if (!editor) return;
      // Native at-cursor rename input (same widget as F2).
      await vscode.commands.executeCommand('editor.action.rename');
    }],
    ['pys.refactor.extractVariable', async () => {
      const editor = requirePysEditor();
      if (!editor) return;
      const snap = captureEditor(editor);
      const name = await showModalInput(
        context,
        {
          title: 'Extract Variable',
          prompt: 'Name for the new local',
          value: 'extracted',
        },
        snap,
      );
      if (name === null || !String(name).trim()) {
        return;
      }
      await runOp('extract-variable', editor.document, editor.selection, snap, async (_doc, sel) => [
        '--start-line', String(sel.start.line + 1),
        '--start-column', String(sel.start.character + 1),
        '--end-line', String(sel.end.line + 1),
        '--end-column', String(sel.end.character + 1),
        '--new-name', String(name).trim(),
      ]);
    }],
    ['pys.refactor.extractFunction', async () => {
      const editor = requirePysEditor();
      if (!editor) return;
      const snap = captureEditor(editor);
      const name = await showModalInput(
        context,
        {
          title: 'Extract Function',
          prompt: 'Name for the new function or method',
          value: 'extracted',
        },
        snap,
      );
      if (name === null || !String(name).trim()) {
        return;
      }
      await runOp('extract-function', editor.document, editor.selection, snap, async (_doc, sel) => [
        '--start-line', String(sel.start.line + 1),
        '--end-line', String(sel.end.line + 1),
        '--new-name', String(name).trim(),
      ]);
    }],
    ['pys.refactor.inlineVariable', async () => {
      const editor = requirePysEditor();
      if (!editor) return;
      const snap = captureEditor(editor);
      await runOp('inline-variable', editor.document, editor.selection, snap, async (_doc, sel) =>
        posArgs(sel.active),
      );
    }],
    ['pys.refactor.inlineFunction', async () => {
      const editor = requirePysEditor();
      if (!editor) return;
      const snap = captureEditor(editor);
      await runOp('inline-function', editor.document, editor.selection, snap, async (_doc, sel) =>
        posArgs(sel.active),
      );
    }],
    ['pys.refactor.safeDelete', async () => {
      const editor = requirePysEditor();
      if (!editor) return;
      const snap = captureEditor(editor);
      await runOp('safe-delete', editor.document, editor.selection, snap, async (_doc, sel) =>
        posArgs(sel.active),
      );
    }],
    ['pys.refactor.introduceParameter', async () => {
      const editor = requirePysEditor();
      if (!editor) return;
      const snap = captureEditor(editor);
      const param = await showModalInput(
        context,
        {
          title: 'Introduce Parameter',
          prompt: 'Parameter name',
          value: 'param',
        },
        snap,
      );
      if (param === null || !String(param).trim()) {
        return;
      }
      const ptype = await showModalInput(
        context,
        {
          title: 'Introduce Parameter',
          prompt: 'Parameter type',
          value: 'int',
        },
        snap,
      );
      if (ptype === null) {
        return;
      }
      await runOp('introduce-parameter', editor.document, editor.selection, snap, async (_doc, sel) => [
        ...posArgs(sel.active),
        '--param-name', String(param).trim(),
        '--param-type', String(ptype).trim() || 'int',
      ]);
    }],
    ['pys.generate.createClass', async () => {
      const editor = requirePysEditor();
      if (!editor) return;
      const snap = captureEditor(editor);
      await runOp('create-class', editor.document, editor.selection, snap, async (_doc, sel) =>
        posArgs(sel.active),
      );
    }],
  ];

  for (const [id, fn] of commands) {
    context.subscriptions.push(vscode.commands.registerCommand(id, fn));
  }

  context.subscriptions.push(
    vscode.languages.registerRenameProvider({ language: 'pys' }, {
      async prepareRename(document, position) {
        const word = document.getWordRangeAtPosition(position);
        if (!word) {
          throw new Error('No symbol to rename');
        }
        return word;
      },
      async provideRenameEdits(document, position, newName) {
        const plan = await callRefactorPlan(document, 'rename', [
          ...posArgs(position),
          '--new-name',
          newName,
        ]);
        if (!plan || !plan.ok) {
          const msg = (plan && plan.conflicts && plan.conflicts[0] && plan.conflicts[0].message)
            || (plan && plan.message)
            || 'Rename failed';
          throw new Error(msg);
        }
        const edits = plan.edits || [];
        const chosen = await showLivePreview(
          context,
          {
            title: plan.title || 'Rename Symbol',
            summary: plan.summary || '',
            why: plan.why || '',
            conflicts: plan.conflicts || [],
            edits,
            hardBlocked: false,
            message: plan.message || '',
          },
          document,
        );
        if (chosen === null) {
          return null;
        }
        // Live preview already mutated the buffer on Accept.
        if (chosen.alreadyApplied) {
          return new vscode.WorkspaceEdit();
        }
        return workspaceEditFromPlan(edits, chosen.indices);
      },
    }),
  );

  const catalogDocs = {
    'extract-variable': new vscode.MarkdownString(
      '**Extract Variable** (Fowler)\n\nReplace an expression with a named local.\n\n*Why:* names document intent and avoid duplicating expressions.',
    ),
    'extract-function': new vscode.MarkdownString(
      '**Extract Function** (Fowler)\n\nMove statements into a new function/method.\n\n*Why:* smaller units are easier to name and test. Methods stay in the method section.',
    ),
    'inline-variable': new vscode.MarkdownString(
      '**Inline Variable** (Fowler)\n\nReplace uses with the initializer and remove the decl.',
    ),
    'inline-function': new vscode.MarkdownString(
      '**Inline Function** (Fowler)\n\nReplace calls with the body when safe.',
    ),
    'safe-delete': new vscode.MarkdownString(
      '**Safe Delete**\n\nDelete only when no binding-aware references remain.',
    ),
    'introduce-parameter': new vscode.MarkdownString(
      '**Introduce Parameter** (Add Parameter)\n\nPromote a local into an explicit API parameter.',
    ),
    'create-class': new vscode.MarkdownString(
      '**Create Class**\n\nGenerate a class with fields and constructor from named call arguments.',
    ),
  };

  context.subscriptions.push(
    vscode.languages.registerCodeActionsProvider({ language: 'pys' }, {
      provideCodeActions(document, range) {
        const actions = [];
        const add = (title, command, kind, docKey) => {
          const a = new vscode.CodeAction(title, kind);
          a.command = { title, command };
          a.isPreferred = false;
          if (catalogDocs[docKey]) {
            a.documentation = catalogDocs[docKey];
          }
          actions.push(a);
        };
        if (!range.isEmpty) {
          add('Extract Variable…', 'pys.refactor.extractVariable', vscode.CodeActionKind.RefactorExtract, 'extract-variable');
          add('Extract Function…', 'pys.refactor.extractFunction', vscode.CodeActionKind.RefactorExtract, 'extract-function');
        }
        add('Inline Variable…', 'pys.refactor.inlineVariable', vscode.CodeActionKind.RefactorInline, 'inline-variable');
        add('Inline Function…', 'pys.refactor.inlineFunction', vscode.CodeActionKind.RefactorInline, 'inline-function');
        add('Safe Delete…', 'pys.refactor.safeDelete', vscode.CodeActionKind.Refactor, 'safe-delete');
        add('Introduce Parameter…', 'pys.refactor.introduceParameter', vscode.CodeActionKind.RefactorRewrite, 'introduce-parameter');
        add('Create Class from Call…', 'pys.generate.createClass', vscode.CodeActionKind.QuickFix, 'create-class');
        add('Rename Symbol…', 'pys.refactor.rename', vscode.CodeActionKind.Refactor, 'rename');
        return actions;
      },
    }, {
      providedCodeActionKinds: [
        vscode.CodeActionKind.Refactor,
        vscode.CodeActionKind.RefactorExtract,
        vscode.CodeActionKind.RefactorInline,
        vscode.CodeActionKind.RefactorRewrite,
        vscode.CodeActionKind.QuickFix,
      ],
    }),
  );
}

module.exports = { registerRefactoring };
