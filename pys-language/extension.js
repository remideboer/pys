const vscode = require('vscode');
const cp = require('child_process');
const path = require('path');

const PYS_KEYWORDS = [
  'if', 'else', 'unless', 'loop', 'function', 'func', 'method', 'class',
  'inherits', 'return', 'import', 'from', 'let', 'break', 'continue',
  'pass', 'public', 'private', 'protected', 'module', 'this', 'super',
  'not', 'and', 'or', 'true', 'false', 'null', 'print',
];

const PYS_TYPES = ['int', 'float', 'char', 'string', 'bool'];

function resolveFilePath(file) {
  if (!file) {
    return null;
  }
  if (file instanceof vscode.Uri) {
    return file.fsPath;
  }
  const fileString = String(file);
  if (fileString.startsWith('file://')) {
    return vscode.Uri.parse(fileString).fsPath;
  }
  const maybeUri = vscode.Uri.parse(fileString);
  if (maybeUri.scheme === 'file') {
    return maybeUri.fsPath;
  }
  return fileString;
}

function activate(context) {
  const diagnosticCollection = vscode.languages.createDiagnosticCollection('pys');
  context.subscriptions.push(diagnosticCollection);

  let validateTimer = null;
  let validateChild = null;

  function createDiagnosticFromError(parsed, document) {
    const line = Number(parsed.line || 1);
    const column = Number(parsed.column || 1);
    const lineText = document.lineAt(Math.max(line - 1, 0)).text;
    const startCol = Math.max(column - 1, 0);
    let endCol = startCol + 1;
    const functionMatch = /\bfunction\b/.exec(lineText);
    if (String(parsed.message || '').includes('Class methods must use `method` instead of `function`.') && functionMatch) {
      endCol = functionMatch.index + functionMatch[0].length;
    } else {
      const rest = lineText.slice(startCol);
      const word = rest.match(/^[A-Za-z_]\w*|[^\s]/);
      if (word) {
        endCol = startCol + word[0].length;
      } else {
        endCol = Math.max(lineText.length, startCol + 1);
      }
    }
    const start = new vscode.Position(Math.max(line - 1, 0), startCol);
    const end = new vscode.Position(Math.max(line - 1, 0), endCol);
    const diagnostic = new vscode.Diagnostic(
      new vscode.Range(start, end),
      parsed.message || 'PYS syntax error',
      vscode.DiagnosticSeverity.Error,
    );
    diagnostic.source = 'PYS';
    if (String(parsed.message || '').includes('Class methods must use `method` instead of `function`.')) {
      diagnostic.code = 'pys.invalid-class-function';
      diagnostic.message = 'Use `method` for class methods instead of `function`.';
    }
    return diagnostic;
  }

  async function validateDocument(document) {
    if (document.languageId !== 'pys' || document.uri.scheme !== 'file') {
      diagnosticCollection.delete(document.uri);
      return;
    }

    const workspace = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
    if (!workspace) {
      diagnosticCollection.delete(document.uri);
      return;
    }

    const workspacePath = workspace.uri.fsPath;
    const pythonExecutable = process.platform === 'win32' ? 'python' : 'python3';
    const pythonCode = `
import json
import sys
from pathlib import Path
from transpiler.transpiler import Parser, TranspileError

source = Path(sys.argv[1]).read_text(encoding='utf-8')
try:
    Parser(source).parse()
    print(json.dumps({"ok": True}))
except TranspileError as exc:
    print(json.dumps({
        "ok": False,
        "message": str(exc),
        "line": getattr(exc, "line_number", None),
        "column": getattr(exc, "column", None),
        "code_line": getattr(exc, "code_line", None),
    }))
except Exception as exc:
    print(json.dumps({"ok": False, "message": f"{type(exc).__name__}: {exc}"}))
`;

    if (validateChild) {
      try {
        validateChild.kill();
      } catch (error) {
        // ignore
      }
      validateChild = null;
    }

    return new Promise((resolve) => {
      const child = cp.spawn(pythonExecutable, ['-c', pythonCode, document.uri.fsPath], {
        cwd: workspacePath,
        env: {
          ...process.env,
          PYTHONPATH: [workspacePath, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter),
        },
      });
      validateChild = child;
      let output = '';
      child.stdout.on('data', (chunk) => {
        output += chunk.toString();
      });
      child.stderr.on('data', () => {});
      child.on('close', () => {
        if (validateChild === child) {
          validateChild = null;
        }
        try {
          const parsed = JSON.parse(output.trim() || '{"ok": true}');
          if (parsed.ok) {
            diagnosticCollection.set(document.uri, []);
            resolve();
            return;
          }

          const diagnostic = createDiagnosticFromError(parsed, document);
          diagnosticCollection.set(document.uri, [diagnostic]);
        } catch (error) {
          diagnosticCollection.set(document.uri, [
            new vscode.Diagnostic(
              new vscode.Range(0, 0, 0, 1),
              'Unable to parse PYS diagnostics.',
              vscode.DiagnosticSeverity.Error,
            ),
          ]);
        }
        resolve();
      });
      child.on('error', () => {
        if (validateChild === child) {
          validateChild = null;
        }
        diagnosticCollection.set(document.uri, []);
        resolve();
      });
    });
  }

  function scheduleValidate(document) {
    if (validateTimer) {
      clearTimeout(validateTimer);
    }
    validateTimer = setTimeout(() => {
      validateDocument(document);
    }, 300);
  }

  function provideCodeLenses(document, token) {
    const top = new vscode.Range(0, 0, 0, 0);
    const runCmd = {
      title: 'Run',
      command: 'pys.runFile',
      arguments: [document.uri]
    };
    const debugCmd = {
      title: 'Debug',
      command: 'pys.debugFile',
      arguments: [document.uri]
    };
    return [new vscode.CodeLens(top, runCmd), new vscode.CodeLens(top, debugCmd)];
  }

  context.subscriptions.push(vscode.languages.registerCodeLensProvider({ language: 'pys' }, { provideCodeLenses }));
  context.subscriptions.push(vscode.languages.registerCompletionItemProvider({ language: 'pys' }, {
    provideCompletionItems() {
      const items = [];
      for (const keyword of PYS_KEYWORDS) {
        const item = new vscode.CompletionItem(keyword, vscode.CompletionItemKind.Keyword);
        item.detail = 'PYS keyword';
        items.push(item);
      }
      for (const typeName of PYS_TYPES) {
        const item = new vscode.CompletionItem(typeName, vscode.CompletionItemKind.TypeParameter);
        item.detail = 'PYS type';
        items.push(item);
      }
      return items;
    }
  }));
  context.subscriptions.push(vscode.languages.registerHoverProvider({ language: 'pys' }, {
    provideHover(document, position) {
      const range = document.getWordRangeAtPosition(position);
      if (!range) {
        return null;
      }
      const word = document.getText(range);
      const hints = {
        loop: 'C-style: `loop (int i = 0, i < n, i++) { ... }`\nWhile-style: `loop (condition) { ... }`',
        function: 'Top-level function: `function name(args) { ... }`\nTyped: `function int name(args) { return 0 }`',
        method: 'Class method: `public method name(args) { ... }`',
        class: 'Class: `class Name { ... }`\nInheritance: `class Child inherits Parent { ... }`',
        inherits: 'Subclass syntax: `class Truck inherits Car { ... }`',
        unless: 'Negated if: `unless (condition) { ... }` → `if not (condition):`',
        this: 'Current instance reference (becomes `self` in Python)',
        super: 'Call parent constructor/method: `super(...)`',
        private: 'Visible only inside the defining class',
        protected: 'Visible in the class and subclasses',
        module: 'Visible only within the same `.pys` file',
        public: 'Visible everywhere',
        string: 'Text type (transpiles to Python `str`)',
        int: 'Integer type',
        float: 'Floating-point type',
        char: 'Single-character type (transpiles to `str`)',
        bool: 'Boolean type',
      };
      if (!hints[word]) {
        return null;
      }
      return new vscode.Hover(new vscode.MarkdownString(`**${word}**\n\n${hints[word]}`));
    }
  }));
  context.subscriptions.push(vscode.languages.registerCodeActionsProvider({ language: 'pys' }, {
    provideCodeActions(document, range, context) {
      const diagnostics = context.diagnostics || [];
      const target = diagnostics.find((diagnostic) => diagnostic.code === 'pys.invalid-class-function');
      if (!target) {
        return [];
      }

      const fix = new vscode.CodeAction('Replace with `method`', vscode.CodeActionKind.QuickFix);
      fix.diagnostics = [target];
      fix.isPreferred = true;
      fix.edit = new vscode.WorkspaceEdit();
      fix.edit.replace(document.uri, new vscode.Range(target.range.start, target.range.end), 'method');
      return [fix];
    }
  }));
  context.subscriptions.push(vscode.workspace.onDidOpenTextDocument((document) => {
    if (document.languageId === 'pys') {
      scheduleValidate(document);
    }
  }));
  context.subscriptions.push(vscode.workspace.onDidChangeTextDocument((event) => {
    if (event.document.languageId === 'pys') {
      scheduleValidate(event.document);
    }
  }));
  context.subscriptions.push(vscode.workspace.onDidSaveTextDocument((document) => {
    if (document.languageId === 'pys') {
      scheduleValidate(document);
    }
  }));
  context.subscriptions.push(vscode.window.onDidChangeActiveTextEditor((editor) => {
    if (editor && editor.document.languageId === 'pys') {
      scheduleValidate(editor.document);
    }
  }));

  for (const document of vscode.workspace.textDocuments) {
    if (document.languageId === 'pys') {
      scheduleValidate(document);
    }
  }

  async function saveAllFiles() {
    try {
      return vscode.workspace.saveAll();
    } catch (error) {
      console.error('Failed to save all files before run/debug:', error);
      return false;
    }
  }

  context.subscriptions.push(vscode.commands.registerCommand('pys.runFile', async (file) => {
    let filePath = resolveFilePath(file);
    if (!filePath && vscode.window.activeTextEditor) {
      filePath = vscode.window.activeTextEditor.document.uri.fsPath;
    }
    if (!filePath) {
      vscode.window.showErrorMessage('Invalid PYS file path.');
      return;
    }
    const workspace = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
    const runner = workspace ? path.join(workspace.uri.fsPath, '.vscode', 'run_pys.py') : null;
    if (!runner) {
      vscode.window.showErrorMessage('Workspace runner not found');
      return;
    }
    const saved = await saveAllFiles();
    if (!saved) {
      vscode.window.showErrorMessage('Unable to save files before running.');
      return;
    }
    const term = vscode.window.createTerminal({ name: 'Run PYS' });
    term.show();
    const cmd = `python "${runner}" "${filePath}"`;
    term.sendText(cmd, true);
  }));

  context.subscriptions.push(vscode.commands.registerCommand('pys.debugFile', async (file) => {
    let filePath = resolveFilePath(file);
    if (!filePath && vscode.window.activeTextEditor) {
      filePath = vscode.window.activeTextEditor.document.uri.fsPath;
    }
    if (!filePath) {
      vscode.window.showErrorMessage('Invalid PYS file path.');
      return;
    }
    const workspace = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
    const runner = workspace ? path.join(workspace.uri.fsPath, '.vscode', 'run_pys.py') : null;
    if (!runner) {
      vscode.window.showErrorMessage('Workspace runner not found');
      return;
    }
    const saved = await saveAllFiles();
    if (!saved) {
      vscode.window.showErrorMessage('Unable to save files before debugging.');
      return;
    }
    vscode.debug.startDebugging(undefined, {
      name: 'Run .pys file',
      type: 'python',
      request: 'launch',
      program: runner,
      args: [filePath]
    });
  }));
}

function deactivate() {}

module.exports = { activate, deactivate };
