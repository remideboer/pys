const vscode = require('vscode');
const cp = require('child_process');
const path = require('path');

const PYS_KEYWORDS = [
  'if', 'else', 'unless', 'loop', 'function', 'func', 'class', 'interface',
  'implements', 'inherits', 'return', 'import', 'from', 'var', 'break', 'continue',
  'pass', 'public', 'private', 'protected', 'module', 'global', 'package', 'const', 'fix',
  'this', 'super', 'not', 'and', 'or', 'true', 'false', 'null', 'print', 'all', 'sealed',
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
    if (String(parsed.message || '').includes('Class methods must not use `function`') && functionMatch) {
      endCol = functionMatch.index + functionMatch[0].length;
    } else if (String(parsed.message || '').includes('Remove `method`') && /\bmethod\b/.exec(lineText)) {
      const methodMatch = /\bmethod\b/.exec(lineText);
      endCol = methodMatch.index + methodMatch[0].length;
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
    if (parsed.code) {
      diagnostic.code = parsed.code;
    }
    if (parsed.suggested_fix) {
      diagnostic.code = diagnostic.code || 'pys.missing-type';
    }
    if (String(parsed.message || '').includes('Class methods must not use `function`')) {
      diagnostic.code = 'pys.invalid-class-function';
      diagnostic.message = 'Remove `function`. Class methods use an access modifier: `public name(args)`.';
    } else if (String(parsed.message || '').includes('Remove `method`')) {
      diagnostic.code = 'pys.invalid-class-method-keyword';
      diagnostic.message = 'Remove `method`. Use `public name(args)` or `public string name(args)`.';
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

source_path = Path(sys.argv[1])
source = source_path.read_text(encoding='utf-8')
try:
    Parser(source, source_path=source_path).parse()
    print(json.dumps({"ok": True}))
except TranspileError as exc:
    sf = getattr(exc, "source_file", None)
    print(json.dumps({
        "ok": False,
        "message": exc.args[0] if exc.args else str(exc),
        "line": getattr(exc, "line_number", None),
        "column": getattr(exc, "column", None),
        "code_line": getattr(exc, "code_line", None),
        "source_file": str(sf) if sf else None,
        "code": getattr(exc, "code", None),
        "suggested_fix": getattr(exc, "suggested_fix", None),
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
        var: 'Type-inferred variable: `var name = value`\nThe inferred type is fixed; later assignments must match.',
        interface: 'Abstract type: `interface Name { public action() }`\nMethods have no body and must be implemented by classes.',
        implements: 'Class implements interface(s): `class Car implements Startable { ... }`',
        class: 'Class: `class Name { ... }`\nInheritance: `class Child inherits Parent { ... }`\nInterfaces: `class Name implements Iface { ... }`',
        inherits: 'Subclass syntax: `class Truck inherits Car { ... }`',
        unless: 'Negated if: `unless (condition) { ... }` → `if not (condition):`',
        this: 'Current instance reference (becomes `self` in Python)',
        super: 'Call parent constructor/method: `super(...)`',
        private: 'Visible only inside the defining class. Required on fields and methods.',
        protected: 'Visible in the class and subclasses. Required on fields and methods.',
        module: 'Module-only. On class members: same `.pys` file (required). On top-level functions/classes: default if omitted.',
        const: 'Compile-time constant: `const float PI = 3.14` or `global const float PI = 3.14`.\nCannot be reassigned; initializer must be a constant expression.',
        fix: 'Runtime immutability: `fix int x = sum(4, 5)`. Initializer may be any expression; value cannot change after assignment.',
        global: 'Top-level export with global access across the whole project. Use: `global function name(...)` or `global const float PI = ...`.',
        package: 'Top-level export visible only in the same folder. Use: `package function name(...)`.',
        public: 'Visible everywhere. Class methods: `public name(args)` or `public string name(args)`.',
        sealed: 'Prevents inheritance: `sealed class Ship { ... }`. No class may use `inherits` on a sealed class.',
        import: 'Import exports: `import funcs`, `import all from funcs.pys`, or `import name from funcs.pys`.',
        from: 'Used in `import name from module.pys` / `import all from module.pys`.',
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

  function locateSymbol(document, word) {
    const workspace = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
    if (!workspace) {
      return Promise.resolve(null);
    }
    const workspacePath = workspace.uri.fsPath;
    const pythonExecutable = process.platform === 'win32' ? 'python' : 'python3';
    return new Promise((resolve) => {
      const child = cp.spawn(
        pythonExecutable,
        ['-m', 'transpiler.ide', document.uri.fsPath, word],
        {
          cwd: workspacePath,
          env: {
            ...process.env,
            PYTHONPATH: [workspacePath, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter),
          },
        },
      );
      let output = '';
      child.stdout.on('data', (chunk) => {
        output += chunk.toString();
      });
      child.on('close', () => {
        try {
          const parsed = JSON.parse(output.trim() || '{}');
          resolve(parsed.location || null);
        } catch (error) {
          resolve(null);
        }
      });
      child.on('error', () => resolve(null));
    });
  }

  context.subscriptions.push(vscode.languages.registerDefinitionProvider({ language: 'pys' }, {
    async provideDefinition(document, position) {
      const range = document.getWordRangeAtPosition(position);
      if (!range) {
        return null;
      }
      const word = document.getText(range);
      const location = await locateSymbol(document, word);
      if (!location || !location.file) {
        return null;
      }
      const uri = vscode.Uri.file(location.file);
      const line = Math.max((location.line || 1) - 1, 0);
      const column = Math.max((location.column || 1) - 1, 0);
      return new vscode.Location(uri, new vscode.Position(line, column));
    }
  }));

  context.subscriptions.push(vscode.languages.registerDeclarationProvider({ language: 'pys' }, {
    async provideDeclaration(document, position) {
      const range = document.getWordRangeAtPosition(position);
      if (!range) {
        return null;
      }
      const word = document.getText(range);
      const location = await locateSymbol(document, word);
      if (!location || !location.file) {
        return null;
      }
      const uri = vscode.Uri.file(location.file);
      const line = Math.max((location.line || 1) - 1, 0);
      const column = Math.max((location.column || 1) - 1, 0);
      return new vscode.Location(uri, new vscode.Position(line, column));
    }
  }));

  const typeTokenCache = new Map(); // uri -> { types: Set, version: number }
  const semanticLegend = new vscode.SemanticTokensLegend(['pysType'], []);

  function fetchValidatedTypes(document) {
    const workspace = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
    if (!workspace) {
      return Promise.resolve([]);
    }
    const workspacePath = workspace.uri.fsPath;
    const pythonExecutable = process.platform === 'win32' ? 'python' : 'python3';
    return new Promise((resolve) => {
      const child = cp.spawn(
        pythonExecutable,
        ['-m', 'transpiler.ide', document.uri.fsPath],
        {
          cwd: workspacePath,
          env: {
            ...process.env,
            PYTHONPATH: [workspacePath, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter),
          },
        },
      );
      let output = '';
      child.stdout.on('data', (chunk) => {
        output += chunk.toString();
      });
      child.on('close', () => {
        try {
          const parsed = JSON.parse(output.trim() || '{}');
          resolve(parsed.validated_types || []);
        } catch (error) {
          resolve([]);
        }
      });
      child.on('error', () => resolve([]));
    });
  }

  context.subscriptions.push(vscode.languages.registerDocumentSemanticTokensProvider(
    { language: 'pys' },
    {
      async provideDocumentSemanticTokens(document) {
        const key = document.uri.toString();
        let types = typeTokenCache.get(key);
        if (!types || types.version !== document.version) {
          const validated = await fetchValidatedTypes(document);
          types = { types: new Set(validated), version: document.version };
          typeTokenCache.set(key, types);
        }
        const builder = new vscode.SemanticTokensBuilder(semanticLegend);
        const skip = new Set(['int', 'float', 'char', 'string', 'bool']); // already grammar-highlighted
        for (let line = 0; line < document.lineCount; line++) {
          const text = document.lineAt(line).text;
          for (const typeName of types.types) {
            if (skip.has(typeName) || typeName.length < 2) {
              continue;
            }
            const re = new RegExp(`\\b${typeName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'g');
            let match;
            while ((match = re.exec(text)) !== null) {
              builder.push(line, match.index, match[0].length, 0, 0);
            }
          }
        }
        return builder.build();
      }
    },
    semanticLegend,
  ));

  context.subscriptions.push(vscode.languages.registerCodeActionsProvider({ language: 'pys' }, {
    provideCodeActions(document, range, context) {
      const diagnostics = context.diagnostics || [];
      const actions = [];

      const functionDiag = diagnostics.find((diagnostic) => diagnostic.code === 'pys.invalid-class-function');
      if (functionDiag) {
        const fix = new vscode.CodeAction('Remove `function`', vscode.CodeActionKind.QuickFix);
        fix.diagnostics = [functionDiag];
        fix.isPreferred = true;
        fix.edit = new vscode.WorkspaceEdit();
        const line = document.lineAt(functionDiag.range.start.line).text;
        const match = /\bfunction\s+/.exec(line);
        if (match) {
          const start = new vscode.Position(functionDiag.range.start.line, match.index);
          const end = new vscode.Position(functionDiag.range.start.line, match.index + match[0].length);
          fix.edit.replace(document.uri, new vscode.Range(start, end), '');
          actions.push(fix);
        }
      }

      const methodDiag = diagnostics.find((diagnostic) => diagnostic.code === 'pys.invalid-class-method-keyword');
      if (methodDiag) {
        const fix = new vscode.CodeAction('Remove `method`', vscode.CodeActionKind.QuickFix);
        fix.diagnostics = [methodDiag];
        fix.isPreferred = true;
        fix.edit = new vscode.WorkspaceEdit();
        const line = document.lineAt(methodDiag.range.start.line).text;
        const match = /\bmethod\s+/.exec(line);
        if (match) {
          const start = new vscode.Position(methodDiag.range.start.line, match.index);
          const end = new vscode.Position(methodDiag.range.start.line, match.index + match[0].length);
          fix.edit.replace(document.uri, new vscode.Range(start, end), '');
          actions.push(fix);
        }
      }

      const missingType = diagnostics.find((diagnostic) => diagnostic.code === 'pys.missing-type');
      if (missingType) {
        const suggested = (missingType.message.match(/Suggested declaration: `([^`]+)`/) || [])[1];
        if (suggested) {
          const fix = new vscode.CodeAction(`Declare as: ${suggested.split('=')[0].trim()}`, vscode.CodeActionKind.QuickFix);
          fix.diagnostics = [missingType];
          fix.isPreferred = true;
          fix.edit = new vscode.WorkspaceEdit();
          const line = document.lineAt(missingType.range.start.line);
          fix.edit.replace(document.uri, line.range, suggested);
          actions.push(fix);
        }
      }

      return actions;
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
