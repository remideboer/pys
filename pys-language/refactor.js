/**
 * Educational refactoring: plan via IDE process, preview, apply WorkspaceEdit.
 */
const vscode = require('vscode');
const {
  buildIdeProcessSpec,
  resolveWorkspaceFile,
  runJsonProcess,
} = require('./ide-process');

const PYTHON = process.platform === 'win32' ? 'python' : 'python3';

/**
 * @param {vscode.ExtensionContext} context
 * @param {{ runJsonProcess?: typeof runJsonProcess }} [deps]
 */
function registerRefactoring(context, deps = {}) {
  const runJson = deps.runJsonProcess || runJsonProcess;

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
    const args = ['--refactor-plan', op, contained, ...extraArgs];
    const envSpec = buildIdeProcessSpec(context.extensionPath, workspace.uri.fsPath, args);
    try {
      return await runJson(PYTHON, envSpec.args, envSpec.options, {});
    } catch (err) {
      vscode.window.showErrorMessage(`PYS refactor failed: ${err.message || err}`);
      return null;
    }
  }

  /**
   * @param {object} plan
   */
  async function previewAndApply(plan) {
    if (!plan) {
      return;
    }
    const title = plan.title || plan.catalog_id || 'Refactor';
    const why = plan.why ? `\n\nWhy: ${plan.why}` : '';
    const summary = plan.summary || '';
    if (plan.conflicts && plan.conflicts.length) {
      const hard = plan.conflicts.filter((c) => !c.soft);
      const lines = plan.conflicts.map(
        (c) => `- ${c.message}${c.file ? ` (${c.file}:${c.line})` : ''}`,
      );
      if (hard.length && !plan.ok) {
        await vscode.window.showErrorMessage(
          `${title} blocked:\n${lines.join('\n')}${why}`,
          { modal: true },
        );
        return;
      }
      const pick = await vscode.window.showWarningMessage(
        `${title}: ${plan.conflicts.length} conflict(s).\n${summary}${why}\n\n${lines.join('\n')}`,
        { modal: true },
        'Refactor Anyway',
        'Cancel',
      );
      if (pick !== 'Refactor Anyway') {
        return;
      }
    }
    const edits = plan.edits || [];
    if (!edits.length) {
      vscode.window.showInformationMessage(`${title}: nothing to change.`);
      return;
    }
    const items = edits.map((e, i) => ({
      label: e.label || `${e.kind} ${e.file}:${e.line}`,
      description: e.optional ? 'optional' : '',
      picked: !e.optional,
      editIndex: i,
    }));
    const chosen = await vscode.window.showQuickPick(items, {
      canPickMany: true,
      title: `${title} — preview edits (${summary})`,
      placeHolder: 'Uncheck sites to exclude, then Accept',
    });
    if (!chosen || !chosen.length) {
      return;
    }
    const selected = new Set(chosen.map((c) => c.editIndex));
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
    const ok = await vscode.workspace.applyEdit(we);
    if (ok) {
      vscode.window.showInformationMessage(`${title} applied. ${plan.why ? 'Tip: ' + plan.why.slice(0, 120) : ''}`);
    }
  }

  function posArgs(document, position) {
    return [
      '--line',
      String(position.line + 1),
      '--column',
      String(position.character + 1),
    ];
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
          ...posArgs(document, position),
          '--new-name',
          newName,
        ]);
        if (!plan || !plan.ok) {
          const msg = (plan && plan.conflicts && plan.conflicts[0] && plan.conflicts[0].message)
            || (plan && plan.message)
            || 'Rename failed';
          throw new Error(msg);
        }
        const we = new vscode.WorkspaceEdit();
        for (const e of plan.edits || []) {
          const uri = vscode.Uri.file(e.file);
          const range = new vscode.Range(
            new vscode.Position(e.line - 1, e.column - 1),
            new vscode.Position(e.end_line - 1, e.end_column - 1),
          );
          we.replace(uri, range, e.new_text || '');
        }
        return we;
      },
    }),
  );

  async function runOp(op, extraBuilder) {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document.languageId !== 'pys') {
      return;
    }
    const doc = editor.document;
    const sel = editor.selection;
    const extra = extraBuilder(doc, sel);
    const plan = await callRefactorPlan(doc, op, extra);
    await previewAndApply(plan);
  }

  const commands = [
    ['pys.refactor.rename', async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;
      await vscode.commands.executeCommand('editor.action.rename');
    }],
    ['pys.refactor.extractVariable', async () => {
      await runOp('extract-variable', (doc, sel) => {
        const name = 'extracted';
        return [
          '--start-line', String(sel.start.line + 1),
          '--start-column', String(sel.start.character + 1),
          '--end-line', String(sel.end.line + 1),
          '--end-column', String(sel.end.character + 1),
          '--new-name', name,
        ];
      });
    }],
    ['pys.refactor.extractFunction', async () => {
      const name = await vscode.window.showInputBox({ prompt: 'New function name', value: 'extracted' });
      if (!name) return;
      await runOp('extract-function', (doc, sel) => [
        '--start-line', String(sel.start.line + 1),
        '--end-line', String(sel.end.line + 1),
        '--new-name', name,
      ]);
    }],
    ['pys.refactor.inlineVariable', async () => {
      await runOp('inline-variable', (doc, sel) => posArgs(doc, sel.active));
    }],
    ['pys.refactor.inlineFunction', async () => {
      await runOp('inline-function', (doc, sel) => posArgs(doc, sel.active));
    }],
    ['pys.refactor.safeDelete', async () => {
      await runOp('safe-delete', (doc, sel) => posArgs(doc, sel.active));
    }],
    ['pys.refactor.introduceParameter', async () => {
      const param = await vscode.window.showInputBox({ prompt: 'Parameter name', value: 'param' });
      if (!param) return;
      const ptype = await vscode.window.showInputBox({ prompt: 'Parameter type', value: 'int' });
      await runOp('introduce-parameter', (doc, sel) => [
        ...posArgs(doc, sel.active),
        '--param-name', param,
        '--param-type', ptype || 'int',
      ]);
    }],
  ];

  for (const [id, fn] of commands) {
    context.subscriptions.push(vscode.commands.registerCommand(id, fn));
  }

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
        add('Rename Symbol…', 'pys.refactor.rename', vscode.CodeActionKind.Refactor, 'rename');
        return actions;
      },
    }, {
      providedCodeActionKinds: [
        vscode.CodeActionKind.Refactor,
        vscode.CodeActionKind.RefactorExtract,
        vscode.CodeActionKind.RefactorInline,
        vscode.CodeActionKind.RefactorRewrite,
      ],
    }),
  );
}

module.exports = { registerRefactoring };
