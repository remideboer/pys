const vscode = require('vscode');
const fs = require('fs');
const path = require('path');
const {
  buildWorkspaceIdeProcessSpec,
  buildRunEnv,
  resolveWorkspaceFile,
  runJsonProcess,
} = require('./ide-process');

const PYS_KEYWORDS = [
  'if', 'else', 'unless', 'switch', 'case', 'default', 'loop', 'function', 'func', 'class', 'struct', 'enum', 'interface', 'trait',
  'implements', 'inherits', 'uses', 'requires', 'return', 'import', 'from', 'var', 'break', 'continue',
  'pass', 'public', 'private', 'protected', 'module', 'global', 'package', 'const', 'fix',
  'this', 'super', 'not', 'and', 'or', 'xor', 'shift', 'true', 'false', 'null', 'print', 'all', 'sealed',
  'abstract', 'tasks', 'task', 'await', 'shared',
];

const PYS_TYPES = [
  'int', 'float', 'char', 'string', 'bool', 'void',
  'byte', 'nibble', 'int16', 'int32', 'int64', 'dword',
];

const PYS_MD_KEYWORDS = new Set([
  'if', 'else', 'unless', 'switch', 'case', 'default', 'loop', 'function', 'func', 'class', 'struct', 'enum', 'interface', 'trait',
  'implements', 'inherits', 'uses', 'requires', 'return', 'import', 'from', 'var', 'break', 'continue',
  'pass', 'public', 'private', 'protected', 'module', 'global', 'package', 'const', 'fix',
  'this', 'super', 'not', 'and', 'or', 'xor', 'shift', 'print', 'all', 'sealed',
  'abstract', 'tasks', 'task', 'await', 'shared',
]);
const PYS_MD_TYPES = new Set([
  'int', 'float', 'char', 'string', 'bool', 'void',
  'byte', 'nibble', 'int16', 'int32', 'int64', 'dword',
  'list', 'dict', 'tuple', 'set',
]);
const PYS_MD_CONSTANTS = new Set(['true', 'false', 'null']);

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function highlightPysForMarkdown(code) {
  // Keep whitespace as its own tokens so formatting survives preview.
  const tokenPattern =
    /(\s+|##[\s\S]*?\/#|\/\/[^\n]*|#[^\n]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])'|\b\d+\.?\d*\b|\b[A-Za-z_]\w*\b|[^\s])/g;
  let out = '';
  let match;
  while ((match = tokenPattern.exec(code)) !== null) {
    const tok = match[0];
    if (/^\s+$/.test(tok)) {
      out += escapeHtml(tok);
      continue;
    }
    let cls = 'p';
    if (tok.startsWith('##') || tok.startsWith('#') || tok.startsWith('//')) {
      cls = 'c';
    } else if (
      (tok.startsWith('"') && tok.endsWith('"')) ||
      (tok.startsWith("'") && tok.endsWith("'"))
    ) {
      cls = 's';
    } else if (/^\d/.test(tok)) {
      cls = 'n';
    } else if (PYS_MD_CONSTANTS.has(tok)) {
      cls = 'b';
    } else if (PYS_MD_KEYWORDS.has(tok)) {
      cls = 'k';
    } else if (PYS_MD_TYPES.has(tok)) {
      cls = 't';
    }
    out += `<span class="${cls}">${escapeHtml(tok)}</span>`;
  }
  return `<pre class="hljs"><code class="language-pys pys-md">${out}</code></pre>\n`;
}

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

function getConfiguredMainRelative() {
  const value = vscode.workspace.getConfiguration('pys').get('mainFile', '');
  return typeof value === 'string' ? value.trim() : '';
}

function resolveMainFilePath() {
  const relative = getConfiguredMainRelative();
  if (!relative) {
    return null;
  }
  const workspace = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
  if (!workspace) {
    return null;
  }
  const workspacePath = workspace.uri.fsPath;
  const candidate = path.isAbsolute(relative)
    ? relative
    : path.join(workspacePath, relative);
  return resolveWorkspaceFile(workspacePath, candidate);
}

function activate(context) {
  const diagnosticCollection = vscode.languages.createDiagnosticCollection('pys');
  context.subscriptions.push(diagnosticCollection);

  let validateTimer = null;
  let validateController = null;
  context.subscriptions.push({
    dispose() {
      validateController?.abort();
    },
  });

  const hintMeta = new Map(); // `${uri}:${line}:${code}` -> hint
  const warningMeta = new Map(); // `${uri}:${line}:${code}` -> warning

  const mainStatus = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
  mainStatus.command = 'pys.runMain';
  context.subscriptions.push(mainStatus);

  function refreshMainFileUi() {
    const relative = getConfiguredMainRelative();
    const absolute = resolveMainFilePath();
    const exists = absolute && fs.existsSync(absolute);
    vscode.commands.executeCommand('setContext', 'pys.hasMainFile', Boolean(relative));
    if (!relative) {
      mainStatus.hide();
      return;
    }
    const label = path.basename(relative);
    mainStatus.text = exists ? `$(play) PYS: ${label}` : `$(warning) PYS main missing`;
    mainStatus.tooltip = exists
      ? `Run main file (${relative})`
      : `Configured main file not found: ${relative}`;
    mainStatus.show();
  }
  function usageTipsEnabled() {
    return vscode.workspace.getConfiguration('pys').get('libraryTyping.usageTips', false);
  }

  /** Show Run/Debug title icons only for .pys files without Error diagnostics. */
  function refreshRunnableContext(document) {
    const active = vscode.window.activeTextEditor;
    if (!active || active.document.languageId !== 'pys' || active.document.uri.scheme !== 'file') {
      vscode.commands.executeCommand('setContext', 'pys.fileRunnable', false);
      return;
    }
    if (document && active.document.uri.toString() !== document.uri.toString()) {
      return;
    }
    const diags = diagnosticCollection.get(active.document.uri) || [];
    const hasError = diags.some((d) => d.severity === vscode.DiagnosticSeverity.Error);
    vscode.commands.executeCommand('setContext', 'pys.fileRunnable', !hasError);
  }

  function appendTips(message, tips) {
    if (!usageTipsEnabled() || !tips || !tips.length) {
      return message;
    }
    return `${message}\n${tips.map((tip) => `Tip: ${tip}`).join('\n')}`;
  }

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
      appendTips(parsed.message || 'PYS syntax error', parsed.tips),
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

  function createHintDiagnostic(hint, document) {
    const line = Math.max(Number(hint.line || 1) - 1, 0);
    const column = Math.max(Number(hint.column || 1) - 1, 0);
    const lineText = document.lineAt(line).text;
    const rest = lineText.slice(column);
    const word = rest.match(/^[A-Za-z_]\w*/);
    const endCol = word ? column + word[0].length : Math.min(column + 1, lineText.length);
    const diagnostic = new vscode.Diagnostic(
      new vscode.Range(new vscode.Position(line, column), new vscode.Position(line, endCol)),
      appendTips(hint.message || 'PYS typing hint', hint.tips),
      vscode.DiagnosticSeverity.Information,
    );
    diagnostic.source = 'PYS';
    diagnostic.code = hint.code || 'pys.untyped-library';
    const key = `${document.uri.toString()}:${hint.line}:${diagnostic.code}`;
    hintMeta.set(key, hint);
    return diagnostic;
  }

  function createWarningDiagnostic(warning, document) {
    const line = Math.max(Number(warning.line || 1) - 1, 0);
    const column = Math.max(Number(warning.column || 1) - 1, 0);
    const lineText = document.lineAt(line).text;
    const rest = lineText.slice(column);
    const word = rest.match(/^[A-Za-z_]\w*/);
    const endCol = word ? column + word[0].length : Math.min(column + 1, lineText.length);
    let message = warning.message || 'PYS warning';
    if (warning.tips && warning.tips.length) {
      message = `${message}\n${warning.tips.map((tip) => `Tip: ${tip}`).join('\n')}`;
    }
    const diagnostic = new vscode.Diagnostic(
      new vscode.Range(new vscode.Position(line, column), new vscode.Position(line, endCol)),
      message,
      vscode.DiagnosticSeverity.Warning,
    );
    diagnostic.source = 'PYS';
    diagnostic.code = warning.code || 'pys.warning';
    const key = `${document.uri.toString()}:${warning.line}:${diagnostic.code}`;
    warningMeta.set(key, warning);
    return diagnostic;
  }

  async function validateDocument(document) {
    if (document.languageId !== 'pys' || document.uri.scheme !== 'file') {
      diagnosticCollection.delete(document.uri);
      refreshRunnableContext(document);
      return;
    }

    const workspace = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
    if (!workspace) {
      diagnosticCollection.delete(document.uri);
      refreshRunnableContext(document);
      return;
    }

    const workspacePath = workspace.uri.fsPath;
    const pythonExecutable = process.platform === 'win32' ? 'python' : 'python3';

    validateController?.abort();
    const controller = new AbortController();
    validateController = controller;
    const spec = buildWorkspaceIdeProcessSpec(
      context.extensionPath,
      workspacePath,
      document.uri.fsPath,
    );
    if (!spec) {
      diagnosticCollection.delete(document.uri);
      afterDiagnosticsUpdated(document);
      return;
    }
    try {
      const parsed = await runJsonProcess(
        pythonExecutable,
        spec.args,
        spec.options,
        { signal: controller.signal },
      );
      if (validateController !== controller) {
        return;
      }
      const diagnostics = [];
      // Clear stale hint/warning metadata for this document
      for (const key of [...hintMeta.keys()]) {
        if (key.startsWith(`${document.uri.toString()}:`)) {
          hintMeta.delete(key);
        }
      }
      for (const key of [...warningMeta.keys()]) {
        if (key.startsWith(`${document.uri.toString()}:`)) {
          warningMeta.delete(key);
        }
      }
      if (!parsed.ok && parsed.error) {
        diagnostics.push(createDiagnosticFromError(parsed.error, document));
      }
      for (const warning of parsed.warnings || []) {
        diagnostics.push(createWarningDiagnostic(warning, document));
      }
      for (const hint of parsed.hints || []) {
        diagnostics.push(createHintDiagnostic(hint, document));
      }
      diagnosticCollection.set(document.uri, diagnostics);
      afterDiagnosticsUpdated(document);
    } catch (error) {
      if (error && error.code === 'CANCELLED') {
        return;
      }
      diagnosticCollection.set(document.uri, [
        new vscode.Diagnostic(
          new vscode.Range(0, 0, 0, 1),
          `PYS diagnostics failed (${error.code || 'PROCESS_ERROR'}).`,
          vscode.DiagnosticSeverity.Error,
        ),
      ]);
      afterDiagnosticsUpdated(document);
    } finally {
      if (validateController === controller) {
        validateController = null;
      }
    }
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
    const diags = diagnosticCollection.get(document.uri) || [];
    if (diags.some((d) => d.severity === vscode.DiagnosticSeverity.Error)) {
      return [];
    }
    const top = new vscode.Range(0, 0, 0, 0);
    const runCmd = {
      title: '$(play) Run',
      command: 'pys.runFile',
      arguments: [document.uri]
    };
    const debugCmd = {
      title: '$(debug-alt) Debug',
      command: 'pys.debugFile',
      arguments: [document.uri]
    };
    return [new vscode.CodeLens(top, runCmd), new vscode.CodeLens(top, debugCmd)];
  }

  const codeLensChange = new vscode.EventEmitter();
  context.subscriptions.push(codeLensChange);
  context.subscriptions.push(vscode.languages.registerCodeLensProvider(
    { language: 'pys' },
    { provideCodeLenses, onDidChangeCodeLenses: codeLensChange.event },
  ));

  function afterDiagnosticsUpdated(document) {
    refreshRunnableContext(document);
    codeLensChange.fire();
  }
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
        struct: 'Value type (fields only): `package struct Damage { int amount }`\nConstruct with `Damage(20)` / `Damage(amount=20)`. Fields are always public; use `global`/`package`/`module` on the struct. Copied on assign/call.',
        enum: 'Closed nominal set: `enum HttpStatus { OK = 200 }`\nMembers: `HttpStatus.OK`. Use `.value` for the underlying int/string. Prefer SCREAMING_SNAKE_CASE names.',
        trait: 'Composable behavior (not a type): `trait Printable { requires string name\n  string label() { return this.name } }`\nCompose with `class C uses Printable { … }`.',
        uses: 'Compose traits onto a class: `class Product uses Printable, Comparable { … }`\nPlaced after `inherits` and before `implements`.',
        requires: 'Trait host obligation: `requires string name` or `requires int compareTo(Product other)`.\nThe using class (or ancestor) must supply it.',
        inherits: 'Subclass syntax: `class Truck inherits Car { ... }`',
        unless: 'Negated if: `unless (condition) { ... }` → `if not (condition):`',
        switch: 'Multi-way branch: statement `case L: …` (trailing `continue` = fall-through) or expression `case L, M => expr`. Exhaustive expressions need all enum members or `default`.',
        case: 'Switch arm: `case LABEL:` (statement) or `case A, B => expr` (expression). Bare enum labels resolve from the subject type.',
        default: 'Switch catch-all arm: `default:` or `default => expr`. Required for non-exhaustive switch expressions.',
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
        sealed: 'Prevents inheritance: `sealed class Ship { ... }`. No class may use `inherits` on a sealed class. Mutually exclusive with `abstract`.',
        abstract: 'Abstract class or method: `abstract class Shape { public abstract float area() }`.\nConcrete subclasses must implement every abstract method. Cannot write `sealed abstract`. Do not instantiate an abstract class.',
        void: 'No return value: `public void add(string item) { … }` or `public abstract void add(string item)`.\nA `void` method must not `return expr` (bare `return` is ok).',
        import: 'Import exports: `import funcs`, `import all from funcs.pys`, or `import name from funcs.pys`.',
        from: 'Used in `import name from module.pys` / `import all from module.pys`.',
        tasks: 'Structured concurrency group: `tasks { task { … } }`. Leaving the block waits for all children.',
        task: 'One concurrent unit inside `tasks`. Named: `task ready { return 1 }` then `await ready` in a sibling.',
        await: 'Wait until a value is ready (named task handle / future). Only inside a `task` body.',
        shared: 'Cross-task mutable cell: `shared int counter = 0`. Outer captures are otherwise read-only inside tasks.',
        string: 'Text type (transpiles to Python `str`)',
        int: 'Integer type. Literals: `10`, `0b1010`, `0xFF` (optional `_` separators).',
        float: 'Floating-point type',
        char: 'Single-character type (transpiles to `str`)',
        bool: 'Boolean type',
        byte: 'Unsigned 8-bit int alias (0..255). Emit as Python int.',
        nibble: 'Unsigned 4-bit int alias (0..15). Emit as Python int.',
        int16: 'Unsigned 16-bit int alias (0..65535). Emit as Python int.',
        int32: 'Unsigned 32-bit int alias (0..2³²−1). Emit as Python int.',
        int64: 'Unsigned 64-bit int alias (0..2⁶⁴−1). Emit as Python int.',
        dword: 'Unsigned 32-bit int alias (same range as int32).',
        xor: 'Bitwise XOR (same as `^`). `and`/`or`/`not` stay logical.',
        shift: 'Word form: `shift left` / `shift right` (same as `<<` / `>>`).',
      };
      if (!hints[word]) {
        return null;
      }
      return new vscode.Hover(new vscode.MarkdownString(`**${word}**\n\n${hints[word]}`));
    }
  }));

  /** Dotted path through the segment under the cursor, e.g. `mysql.connector.connect`. */
  function getDottedPathAt(document, position) {
    const line = document.lineAt(position.line).text;
    const pos = position.character;
    const isPart = (i) => i >= 0 && i < line.length && /[A-Za-z0-9_]/.test(line[i]);
    const isDot = (i) => i >= 0 && i < line.length && line[i] === '.';

    let left = pos;
    let right = pos;
    while (left > 0 && (isPart(left - 1) || isDot(left - 1))) {
      left -= 1;
    }
    while (right < line.length && (isPart(right) || isDot(right))) {
      right += 1;
    }
    while (left < right && line[left] === '.') {
      left += 1;
    }
    while (right > left && line[right - 1] === '.') {
      right -= 1;
    }
    const full = line.slice(left, right);
    if (!full || !/^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*$/.test(full)) {
      return null;
    }
    const cursor = Math.min(Math.max(pos - left, 0), Math.max(full.length - 1, 0));
    let segEnd = cursor;
    while (segEnd < full.length && full[segEnd] !== '.') {
      segEnd += 1;
    }
    // If the cursor is on a dot, use the segment before it.
    if (full[cursor] === '.' && cursor > 0) {
      segEnd = cursor;
    }
    return full.slice(0, segEnd);
  }

  async function locateSymbol(document, symbol, token) {
    const workspace = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
    if (!workspace || !symbol) {
      return null;
    }
    const workspacePath = workspace.uri.fsPath;
    const pythonExecutable = process.platform === 'win32' ? 'python' : 'python3';
    const spec = buildWorkspaceIdeProcessSpec(
      context.extensionPath,
      workspacePath,
      document.uri.fsPath,
      [symbol],
    );
    if (!spec) {
      return null;
    }
    try {
      const parsed = await runJsonProcess(
        pythonExecutable,
        spec.args,
        spec.options,
        { signal: token },
      );
      return parsed.location || null;
    } catch (_error) {
      return null;
    }
  }

  async function provideSymbolLocation(document, position, token) {
    const symbol = getDottedPathAt(document, position);
    if (!symbol) {
      return null;
    }
    const location = await locateSymbol(document, symbol, token);
    if (!location || !location.file) {
      return null;
    }
    const uri = vscode.Uri.file(location.file);
    const line = Math.max((location.line || 1) - 1, 0);
    const column = Math.max((location.column || 1) - 1, 0);
    return new vscode.Location(uri, new vscode.Position(line, column));
  }

  context.subscriptions.push(vscode.languages.registerDefinitionProvider({ language: 'pys' }, {
    provideDefinition: provideSymbolLocation,
  }));

  context.subscriptions.push(vscode.languages.registerDeclarationProvider({ language: 'pys' }, {
    provideDeclaration: provideSymbolLocation,
  }));

  const typeTokenCache = new Map(); // uri -> { types: Set, version: number }
  const semanticLegend = new vscode.SemanticTokensLegend(['pysType'], []);

  /** Index of a `#` line-comment start, or -1. Ignores `#s{…}` string interpolations. */
  function lineCommentStart(text) {
    let inString = false;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (inString) {
        if (ch === '\\') {
          i += 1;
          continue;
        }
        if (ch === '"') {
          inString = false;
        }
        continue;
      }
      if (ch === '"') {
        inString = true;
        continue;
      }
      if (ch === '#' && !/^#[sficbo]\{/.test(text.slice(i))) {
        return i;
      }
    }
    return -1;
  }

  async function fetchValidatedTypes(document, token) {
    const workspace = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
    if (!workspace) {
      return [];
    }
    const workspacePath = workspace.uri.fsPath;
    const pythonExecutable = process.platform === 'win32' ? 'python' : 'python3';
    const spec = buildWorkspaceIdeProcessSpec(
      context.extensionPath,
      workspacePath,
      document.uri.fsPath,
    );
    if (!spec) {
      return [];
    }
    try {
      const parsed = await runJsonProcess(
        pythonExecutable,
        spec.args,
        spec.options,
        { signal: token },
      );
      return parsed.validated_types || [];
    } catch (_error) {
      return [];
    }
  }

  context.subscriptions.push(vscode.languages.registerDocumentSemanticTokensProvider(
    { language: 'pys' },
    {
      async provideDocumentSemanticTokens(document, token) {
        const key = document.uri.toString();
        let types = typeTokenCache.get(key);
        if (!types || types.version !== document.version) {
          const validated = await fetchValidatedTypes(document, token);
          types = { types: new Set(validated), version: document.version };
          typeTokenCache.set(key, types);
        }
        const builder = new vscode.SemanticTokensBuilder(semanticLegend);
        const skip = new Set(['int', 'float', 'char', 'string', 'bool']); // already grammar-highlighted
        let inBlockComment = false;
        for (let line = 0; line < document.lineCount; line++) {
          const text = document.lineAt(line).text;
          if (inBlockComment) {
            if (text.includes('/#')) {
              inBlockComment = false;
            }
            continue;
          }
          if (text.includes('##')) {
            inBlockComment = !text.includes('/#');
            // Fall through only for code before `##` on the same line (rare).
          }
          const commentAt = lineCommentStart(text);
          const codePart = commentAt >= 0 ? text.slice(0, commentAt) : text;
          if (!codePart.trim()) {
            continue;
          }
          for (const typeName of types.types) {
            if (skip.has(typeName) || typeName.length < 2) {
              continue;
            }
            const re = new RegExp(`\\b${typeName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'g');
            let match;
            while ((match = re.exec(codePart)) !== null) {
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

      for (const diagnostic of diagnostics) {
        if (diagnostic.code !== 'pys.enum-naming') {
          continue;
        }
        const key = `${document.uri.toString()}:${diagnostic.range.start.line + 1}:${diagnostic.code}`;
        const warning = warningMeta.get(key);
        const suggested = warning && warning.suggested_fix;
        if (!suggested) {
          continue;
        }
        const action = new vscode.CodeAction(
          `Rename to ${suggested}`,
          vscode.CodeActionKind.QuickFix,
        );
        action.diagnostics = [diagnostic];
        action.isPreferred = true;
        action.edit = new vscode.WorkspaceEdit();
        action.edit.replace(document.uri, diagnostic.range, suggested);
        actions.push(action);
      }

      for (const diagnostic of diagnostics) {
        if (diagnostic.code !== 'pys.untyped-loop-var') {
          continue;
        }
        const key = `${document.uri.toString()}:${diagnostic.range.start.line + 1}:${diagnostic.code}`;
        const hint = hintMeta.get(key);
        if (!hint || !hint.suggested_loop) {
          continue;
        }
        const action = new vscode.CodeAction(
          `Use typed loop: ${hint.suggested_loop}`,
          vscode.CodeActionKind.QuickFix,
        );
        action.diagnostics = [diagnostic];
        action.isPreferred = true;
        action.edit = new vscode.WorkspaceEdit();
        const line = document.lineAt(diagnostic.range.start.line);
        const replaced = line.text.replace(
          /loop\s*\(\s*(?:[A-Za-z_]\w*\s+)?[A-Za-z_]\w*\s+in\s+[^)]+\)/,
          hint.suggested_loop,
        );
        action.edit.replace(document.uri, line.range, replaced);
        actions.push(action);
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
      refreshRunnableContext(editor.document);
      scheduleValidate(editor.document);
    } else {
      refreshRunnableContext(null);
    }
  }));

  // Optimistic: show Run/Debug until the first validation reports an Error.
  if (vscode.window.activeTextEditor && vscode.window.activeTextEditor.document.languageId === 'pys') {
    vscode.commands.executeCommand('setContext', 'pys.fileRunnable', true);
  } else {
    vscode.commands.executeCommand('setContext', 'pys.fileRunnable', false);
  }

  context.subscriptions.push(vscode.workspace.onDidChangeConfiguration((event) => {
    if (event.affectsConfiguration('pys.libraryTyping')) {
      for (const document of vscode.workspace.textDocuments) {
        if (document.languageId === 'pys') {
          scheduleValidate(document);
        }
      }
    }
    if (event.affectsConfiguration('pys.mainFile')) {
      refreshMainFileUi();
    }
  }));

  for (const document of vscode.workspace.textDocuments) {
    if (document.languageId === 'pys') {
      scheduleValidate(document);
    }
  }

  refreshMainFileUi();

  async function saveAllFiles() {
    try {
      return vscode.workspace.saveAll();
    } catch (error) {
      console.error('Failed to save all files before run/debug:', error);
      return false;
    }
  }

  function getPythonExecutable() {
    return process.platform === 'win32' ? 'python' : 'python3';
  }

  function getBundledRoot() {
    return path.join(context.extensionPath, 'bundled');
  }

  function ensureBundledTranspiler() {
    const bundled = getBundledRoot();
    const marker = path.join(bundled, 'transpiler', '__main__.py');
    if (!fs.existsSync(marker)) {
      vscode.window.showErrorMessage(
        'Bundled PYS transpiler not found. Contributors: run `npm run prepare` in pys-language, then reload.'
      );
      return null;
    }
    return bundled;
  }

  function shellQuote(value) {
    if (process.platform === 'win32') {
      return `"${String(value).replace(/"/g, '\\"')}"`;
    }
    return `'${String(value).replace(/'/g, `'\\''`)}'`;
  }

  function resolveTargetPysFile(file) {
    let filePath = resolveFilePath(file);
    if (!filePath && vscode.window.activeTextEditor) {
      const active = vscode.window.activeTextEditor.document;
      if (active.languageId === 'pys' || active.uri.fsPath.toLowerCase().endsWith('.pys')) {
        filePath = active.uri.fsPath;
      }
    }
    if (!filePath) {
      filePath = resolveMainFilePath();
    }
    const workspace = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
    if (!filePath || !workspace) {
      return null;
    }
    return resolveWorkspaceFile(workspace.uri.fsPath, filePath);
  }

  async function runPysFile(filePath) {
    if (!filePath) {
      vscode.window.showErrorMessage('No PYS file to run. Set pys.mainFile or open a .pys file.');
      return;
    }
    if (!vscode.workspace.isTrusted) {
      vscode.window.showErrorMessage('Trust this workspace before running PYS files.');
      return;
    }
    const workspace = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
    if (!workspace) {
      vscode.window.showErrorMessage('Open a workspace before running PYS files.');
      return;
    }
    filePath = resolveWorkspaceFile(workspace.uri.fsPath, filePath);
    if (!filePath) {
      vscode.window.showErrorMessage('PYS file must resolve inside the workspace.');
      return;
    }
    const bundled = ensureBundledTranspiler();
    if (!bundled) {
      return;
    }
    if (!fs.existsSync(filePath)) {
      vscode.window.showErrorMessage(`PYS file not found: ${filePath}`);
      return;
    }
    const saved = await saveAllFiles();
    if (!saved) {
      vscode.window.showErrorMessage('Unable to save files before running.');
      return;
    }
    const pythonExecutable = getPythonExecutable();
    const workDir = path.dirname(filePath);
    filePath = resolveWorkspaceFile(workspace.uri.fsPath, filePath);
    if (!filePath) {
      vscode.window.showErrorMessage('PYS file left the workspace before execution.');
      return;
    }
    const term = vscode.window.createTerminal({
      name: 'Run PYS',
      cwd: workDir,
      env: buildRunEnv(bundled, workspace.uri.fsPath),
    });
    term.show();
    term.sendText(
      `${pythonExecutable} -m transpiler run ${shellQuote(filePath)}`,
      true
    );
  }

  async function debugPysFile(filePath) {
    if (!filePath) {
      vscode.window.showErrorMessage('No PYS file to debug. Set pys.mainFile or open a .pys file.');
      return;
    }
    if (!vscode.workspace.isTrusted) {
      vscode.window.showErrorMessage('Trust this workspace before debugging PYS files.');
      return;
    }
    const workspace = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
    if (!workspace) {
      vscode.window.showErrorMessage('Open a workspace before debugging PYS files.');
      return;
    }
    filePath = resolveWorkspaceFile(workspace.uri.fsPath, filePath);
    if (!filePath) {
      vscode.window.showErrorMessage('PYS file must resolve inside the workspace.');
      return;
    }
    const bundled = ensureBundledTranspiler();
    if (!bundled) {
      return;
    }
    if (!fs.existsSync(filePath)) {
      vscode.window.showErrorMessage(`PYS file not found: ${filePath}`);
      return;
    }
    const saved = await saveAllFiles();
    if (!saved) {
      vscode.window.showErrorMessage('Unable to save files before debugging.');
      return;
    }
    filePath = resolveWorkspaceFile(workspace.uri.fsPath, filePath);
    if (!filePath) {
      vscode.window.showErrorMessage('PYS file left the workspace before execution.');
      return;
    }
    // Runs via the Python debugger on generated code — not PYS source stepping.
    vscode.debug.startDebugging(undefined, {
      name: 'Run .pys file',
      type: 'python',
      request: 'launch',
      module: 'transpiler',
      args: ['run', filePath],
      cwd: path.dirname(filePath),
      env: buildRunEnv(bundled, workspace.uri.fsPath),
      console: 'integratedTerminal',
    });
  }

  context.subscriptions.push(vscode.commands.registerCommand('pys.runFile', async (file) => {
    await runPysFile(resolveTargetPysFile(file));
  }));

  context.subscriptions.push(vscode.commands.registerCommand('pys.debugFile', async (file) => {
    await debugPysFile(resolveTargetPysFile(file));
  }));

  context.subscriptions.push(vscode.commands.registerCommand('pys.runMain', async () => {
    const mainPath = resolveMainFilePath();
    if (!mainPath) {
      vscode.window.showErrorMessage('No main file set. Use "PYS: Set as Main File" or set pys.mainFile.');
      return;
    }
    await runPysFile(mainPath);
  }));

  context.subscriptions.push(vscode.commands.registerCommand('pys.debugMain', async () => {
    const mainPath = resolveMainFilePath();
    if (!mainPath) {
      vscode.window.showErrorMessage('No main file set. Use "PYS: Set as Main File" or set pys.mainFile.');
      return;
    }
    await debugPysFile(mainPath);
  }));

  context.subscriptions.push(vscode.commands.registerCommand('pys.setAsMainFile', async (file) => {
    let filePath = resolveFilePath(file);
    if (!filePath && vscode.window.activeTextEditor) {
      filePath = vscode.window.activeTextEditor.document.uri.fsPath;
    }
    if (!filePath || !filePath.toLowerCase().endsWith('.pys')) {
      vscode.window.showErrorMessage('Select a .pys file to set as main.');
      return;
    }
    const workspace = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
    if (!workspace) {
      vscode.window.showErrorMessage('Open a workspace folder to set a main file.');
      return;
    }
    filePath = resolveWorkspaceFile(workspace.uri.fsPath, filePath);
    if (!filePath) {
      vscode.window.showErrorMessage('Main file must resolve inside the workspace folder.');
      return;
    }
    let relative = path.relative(workspace.uri.fsPath, filePath);
    if (!relative || relative.startsWith('..')) {
      vscode.window.showErrorMessage('Main file must be inside the workspace folder.');
      return;
    }
    relative = relative.replace(/\\/g, '/');
    await vscode.workspace.getConfiguration('pys').update(
      'mainFile',
      relative,
      vscode.ConfigurationTarget.Workspace,
    );
    refreshMainFileUi();
    vscode.window.showInformationMessage(`PYS main file set to ${relative}`);
  }));

  // Markdown preview highlighter for ```pys fences (editor uses TextMate injection).
  return {
    extendMarkdownIt(md) {
      const originalHighlight = md.options.highlight;
      md.options.highlight = (str, lang) => {
        if (lang && String(lang).toLowerCase() === 'pys') {
          return highlightPysForMarkdown(str);
        }
        if (typeof originalHighlight === 'function') {
          return originalHighlight(str, lang);
        }
        return null;
      };
      return md;
    },
  };
}

function deactivate() {}

module.exports = { activate, deactivate };
