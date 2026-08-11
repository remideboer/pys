const vscode = require('vscode');
const fs = require('fs');
const path = require('path');
const os = require('os');
const {
  buildWorkspaceIdeProcessSpec,
  buildRunEnv,
  resolveWorkspaceFile,
  runJsonProcess,
} = require('./ide-process');
const {
  loadMapRegistry,
  mapExactPyStackFrame,
  remapSetBreakpointsArgs,
  remapSetBreakpointsResponse,
  remapBreakpoint,
  remapStackFrames,
  remapVariables,
  formatPysDebugValue,
  rewriteEvaluateExpression,
  collectInlineValueSites,
  filterInlineValueSitesByScope,
} = require('./debug-map');
const { createPysProjectScaffold } = require('./create-project');
const {
  installPlan,
  probeNode,
  probePython,
  resolveToolchainNeeds,
  stableVersionsFor,
  terminalInstallLine,
} = require('./runtime-ensure');
const {
  findProjectManifest,
  normalizedRelativeMain,
  readProjectMain,
  readProjectTarget,
  resolveManifestMain,
  setProjectMain,
} = require('./project-main');
const {
  PYS_DEBUG_SESSION_NAME,
  debugModeOptions,
  isPysDebugSession,
} = require('./debug-mode');
const {
  buildLaunchConfig,
  debugAdapterTypes,
} = require('./debug-launch');
const {
  DEFAULT_MAX_SKIPS,
  PysStepFilter,
} = require('./debug-step-filter');

/**
 * @type {Map<string, {
 *   dir: string,
 *   registry: object,
 *   remapSource: boolean,
 *   bpReqPysBySeq: Map<number, string>,
 *   stepFilter: PysStepFilter
 * }>}
 */
const pysDebugSessions = new Map();
/** @type {{ dir: string, registry: object, stepFilter: PysStepFilter } | null} */
let pendingPysDebug = null;

const PYS_KEYWORDS = [
  'if', 'else', 'unless', 'switch', 'case', 'default', 'loop', 'function', 'func', 'class', 'struct', 'data', 'entity', 'identity', 'lambda', 'enum', 'interface', 'trait',
  'implements', 'inherits', 'uses', 'requires', 'return', 'import', 'from', 'var', 'break', 'continue',
  'pass', 'public', 'private', 'protected', 'module', 'global', 'package', 'const', 'fix',
  'this', 'super', 'not', 'and', 'or', 'xor', 'shift', 'true', 'false', 'null', 'print', 'all', 'closed', 'open', 'override', 'constructor', 'static',
  'abstract', 'tasks', 'task', 'await', 'shared', 'atomic', 'ok', 'error', 'propagate', 'nullable',
];

const PYS_TYPES = [
  'int', 'float', 'char', 'string', 'bool', 'void', 'object',
  'byte', 'nibble', 'int16', 'int32', 'int64', 'dword',
  'list', 'dict', 'tuple', 'set', 'result', 'nullable',
];

const PYS_MD_KEYWORDS = new Set([
  'if', 'else', 'unless', 'switch', 'case', 'default', 'loop', 'function', 'func', 'class', 'struct', 'data', 'entity', 'identity', 'lambda', 'enum', 'interface', 'trait',
  'implements', 'inherits', 'uses', 'requires', 'return', 'import', 'from', 'var', 'break', 'continue',
  'pass', 'public', 'private', 'protected', 'module', 'global', 'package', 'const', 'fix',
  'this', 'super', 'not', 'and', 'or', 'xor', 'shift', 'print', 'all', 'closed', 'open', 'override', 'constructor', 'static',
  'abstract', 'tasks', 'task', 'await', 'shared', 'atomic', 'ok', 'error', 'propagate', 'nullable',
]);
const PYS_MD_TYPES = new Set([
  'int', 'float', 'char', 'string', 'bool', 'void', 'object',
  'byte', 'nibble', 'int16', 'int32', 'int64', 'dword',
  'list', 'dict', 'tuple', 'set', 'result', 'nullable',
]);
const PYS_MD_CONSTANTS = new Set(['true', 'false', 'null']);

function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

const { findEnclosingClassHeader } = require('./class-header');

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
  const workspace = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
  if (workspace) {
    const activePath = vscode.window.activeTextEditor?.document?.uri?.fsPath || workspace.uri.fsPath;
    const manifest = findProjectManifest(activePath, workspace.uri.fsPath)
      || findProjectManifest(workspace.uri.fsPath, workspace.uri.fsPath);
    if (manifest) {
      return readProjectMain(fs.readFileSync(manifest, 'utf8'));
    }
  }
  const value = vscode.workspace.getConfiguration('pys').get('mainFile', '');
  return typeof value === 'string' ? value.trim() : '';
}

function resolveMainFilePath() {
  const workspace = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
  if (!workspace) {
    return null;
  }
  const workspacePath = workspace.uri.fsPath;
  const activePath = vscode.window.activeTextEditor?.document?.uri?.fsPath || workspacePath;
  const manifest = findProjectManifest(activePath, workspacePath)
    || findProjectManifest(workspacePath, workspacePath);
  if (manifest) {
    return resolveManifestMain(manifest);
  }
  const relative = getConfiguredMainRelative();
  if (!relative) {
    return null;
  }
  const candidate = path.isAbsolute(relative)
    ? relative
    : path.join(workspacePath, relative);
  return resolveWorkspaceFile(workspacePath, candidate);
}

function activate(context) {
  const { registerRefactoring } = require('./refactor');
  registerRefactoring(context);
  const { registerInClassBodyContext } = require('./in-class-body');
  registerInClassBodyContext(vscode, context);
  const { registerSyntaxColorSettings } = require('./syntax-colors-ui');
  context.subscriptions.push(registerSyntaxColorSettings(vscode));
  const diagnosticCollection = vscode.languages.createDiagnosticCollection('pys');
  context.subscriptions.push(diagnosticCollection);

  // Beginner-visible Error paint (full red background) in addition to squiggles.
  const errorBackgroundDecoration = vscode.window.createTextEditorDecorationType({
    backgroundColor: 'rgba(220, 50, 47, 0.45)',
    overviewRulerColor: 'rgba(220, 50, 47, 0.9)',
    overviewRulerLane: vscode.OverviewRulerLane.Right,
  });
  context.subscriptions.push(errorBackgroundDecoration);

  function syncErrorDecorations(document) {
    const diags = diagnosticCollection.get(document.uri) || [];
    const ranges = diags
      .filter((d) => d.severity === vscode.DiagnosticSeverity.Error)
      .map((d) => d.range);
    for (const editor of vscode.window.visibleTextEditors) {
      if (editor.document.uri.toString() === document.uri.toString()) {
        editor.setDecorations(errorBackgroundDecoration, ranges);
      }
    }
  }

  function activeNormalPysEntry(session = vscode.debug.activeDebugSession) {
    if (!session || session.name !== PYS_DEBUG_SESSION_NAME) {
      return null;
    }
    return pysDebugSessions.get(session.id) || null;
  }

  async function syncPysStepContexts(session = vscode.debug.activeDebugSession) {
    const entry = activeNormalPysEntry(session);
    await Promise.all([
      vscode.commands.executeCommand(
        'setContext',
        'pys.debugSessionActive',
        Boolean(entry),
      ),
      vscode.commands.executeCommand(
        'setContext',
        'pys.debug.pysOnlyStepping',
        Boolean(entry && entry.stepFilter.enabled),
      ),
    ]);
  }

  void syncPysStepContexts();

  context.subscriptions.push(
    vscode.window.registerTreeDataProvider('pys.sidebar', {
      getChildren() {
        return [];
      },
      getTreeItem(element) {
        return element;
      },
    }),
  );

  let validateTimer = null;
  let validateController = null;
  context.subscriptions.push({
    dispose() {
      validateController?.abort();
    },
  });

  const hintMeta = new Map(); // `${uri}:${line}:${code}` -> hint
  const warningMeta = new Map(); // `${uri}:${line}:${code}` -> warning
  const errorMeta = new Map(); // `${uri}:${line}:${code}` -> error payload (suggested_fix)
  /** @type {Map<string, { variable_types?: Record<string, string>, narrowed_types?: Record<string, string> }>} */
  const analysisCache = new Map();

  const mainStatus = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
  mainStatus.command = 'pys.runMain';
  context.subscriptions.push(mainStatus);

  const emitTargetStatus = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 99);
  emitTargetStatus.command = 'pys.selectEmitTarget';
  context.subscriptions.push(emitTargetStatus);

  const intellisenseStatus = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 98);
  intellisenseStatus.command = 'pys.toggleIntellisense';
  context.subscriptions.push(intellisenseStatus);

  function intellisenseEnabled() {
    return vscode.workspace.getConfiguration('pys').get('intellisense.enabled', true) !== false;
  }

  function refreshIntellisenseUi() {
    const on = intellisenseEnabled();
    intellisenseStatus.text = on ? '$(lightbulb) PYS IntelliSense' : '$(circle-slash) PYS IntelliSense Off';
    intellisenseStatus.tooltip = on
      ? 'Analysis-driven completions On — click to disable'
      : 'IntelliSense Off (keywords only) — click to enable';
    intellisenseStatus.show();
  }

  function getEmitTarget() {
    const raw = vscode.workspace.getConfiguration('pys').get('emitTarget', 'python');
    return raw === 'javascript' ? 'javascript' : 'python';
  }

  function refreshEmitTargetUi() {
    const target = getEmitTarget();
    const label = target === 'javascript' ? 'Node' : 'Python';
    emitTargetStatus.text = `$(symbol-misc) PYS → ${label}`;
    emitTargetStatus.tooltip =
      target === 'javascript'
        ? 'Emit target: JavaScript (Node.js). Click to change.'
        : 'Emit target: Python (CPython). Click to change.';
    emitTargetStatus.show();
  }

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
    let startCol = Math.max(column - 1, 0);
    let endCol = startCol + 1;
    const functionMatch = /\bfunction\b/.exec(lineText);
    if (String(parsed.message || '').includes('Class methods must not use `function`') && functionMatch) {
      endCol = functionMatch.index + functionMatch[0].length;
    } else if (String(parsed.message || '').includes('Remove `method`') && /\bmethod\b/.exec(lineText)) {
      const methodMatch = /\bmethod\b/.exec(lineText);
      endCol = methodMatch.index + methodMatch[0].length;
    } else if (parsed.code === 'pys.unknown-type') {
      const unknown = /Unknown type '([^']+)'/.exec(String(parsed.message || ''));
      const typeName = unknown ? unknown[1] : '';
      const found = typeName ? lineText.indexOf(typeName) : -1;
      if (found >= 0) {
        startCol = found;
        endCol = found + typeName.length;
      } else {
        const rest = lineText.slice(startCol);
        const word = rest.match(/^[A-Za-z_]\w*|[^\s]/);
        if (word) {
          endCol = startCol + word[0].length;
        } else {
          endCol = Math.max(lineText.length, startCol + 1);
        }
      }
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
    if (parsed.suggested_fix && !parsed.code) {
      diagnostic.code = diagnostic.code || 'pys.missing-type';
    }
    if (
      parsed.suggested_fix
      && (
        parsed.code === 'pys.package-mismatch'
        || parsed.code === 'pys.null-non-nullable'
        || parsed.code === 'pys.nullable-use-before-check'
        || parsed.code === 'pys.var-as-type'
        || parsed.code === 'pys.indent'
        || parsed.code === 'pys.trait-require-typo'
        || parsed.code === 'pys.abstract-method'
        || (parsed.code === 'pys.unknown-type' && parsed.suggested_fix === 'create-class')
      )
    ) {
      const key = `${document.uri.toString()}:${line}:${parsed.code}`;
      errorMeta.set(key, parsed);
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
      afterDiagnosticsUpdated(document);
      return;
    }

    const workspace = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
    if (!workspace) {
      diagnosticCollection.delete(document.uri);
      afterDiagnosticsUpdated(document);
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
      ['--stdin'],
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
        { signal: controller.signal, stdin: document.getText() },
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
      for (const key of [...errorMeta.keys()]) {
        if (key.startsWith(`${document.uri.toString()}:`)) {
          errorMeta.delete(key);
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
      analysisCache.set(document.uri.toString(), {
        variable_types: parsed.variable_types || {},
        narrowed_types: parsed.narrowed_types || {},
      });
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
    syncErrorDecorations(document);
    refreshRunnableContext(document);
    codeLensChange.fire();
  }
  context.subscriptions.push(vscode.languages.registerCompletionItemProvider({ language: 'pys' }, {
    async provideCompletionItems(document, position, token) {
      const items = [];
      const pushStatic = () => {
        for (const keyword of PYS_KEYWORDS) {
          const item = new vscode.CompletionItem(keyword, vscode.CompletionItemKind.Keyword);
          item.detail = 'PYS keyword';
          item.sortText = `9_${keyword}`;
          items.push(item);
        }
        for (const typeName of PYS_TYPES) {
          const item = new vscode.CompletionItem(typeName, vscode.CompletionItemKind.TypeParameter);
          item.detail = 'PYS type';
          item.sortText = `4_${typeName}`;
          items.push(item);
        }
      };
      if (!intellisenseEnabled()) {
        pushStatic();
        return items;
      }
      const workspace = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
      if (!workspace || document.uri.scheme !== 'file') {
        pushStatic();
        return items;
      }
      const spec = buildWorkspaceIdeProcessSpec(
        context.extensionPath,
        workspace.uri.fsPath,
        document.uri.fsPath,
        [
          '--completions',
          '--line',
          String(position.line + 1),
          '--column',
          String(position.character + 1),
          '--stdin',
        ],
      );
      if (!spec) {
        pushStatic();
        return items;
      }
      try {
        const parsed = await runJsonProcess(
          process.platform === 'win32' ? 'python' : 'python3',
          spec.args,
          spec.options,
          { signal: token?.isCancellationRequested ? undefined : undefined, stdin: document.getText(), timeoutMs: 4000 },
        );
        if (token.isCancellationRequested) {
          return [];
        }
        const kindMap = {
          variable: vscode.CompletionItemKind.Variable,
          field: vscode.CompletionItemKind.Field,
          method: vscode.CompletionItemKind.Method,
          function: vscode.CompletionItemKind.Function,
          class: vscode.CompletionItemKind.Class,
          struct: vscode.CompletionItemKind.Struct,
          enum: vscode.CompletionItemKind.Enum,
          enumMember: vscode.CompletionItemKind.EnumMember,
          module: vscode.CompletionItemKind.Module,
          keyword: vscode.CompletionItemKind.Keyword,
        };
        for (const raw of parsed.items || []) {
          const item = new vscode.CompletionItem(
            raw.label,
            kindMap[raw.kind] || vscode.CompletionItemKind.Text,
          );
          item.detail = raw.detail || '';
          item.insertText = raw.insertText || raw.label;
          item.sortText = raw.sortText || raw.label;
          items.push(item);
        }
        if (!items.length) {
          pushStatic();
        }
        return items;
      } catch (_err) {
        pushStatic();
        return items;
      }
    },
  }, '.'));

  context.subscriptions.push(
    vscode.commands.registerCommand('pys.toggleIntellisense', async () => {
      const cfg = vscode.workspace.getConfiguration('pys');
      const next = !intellisenseEnabled();
      await cfg.update('intellisense.enabled', next, vscode.ConfigurationTarget.Workspace);
      refreshIntellisenseUi();
    }),
  );
  refreshIntellisenseUi();
  refreshEmitTargetUi();

  context.subscriptions.push(vscode.languages.registerHoverProvider({ language: 'pys' }, {
    provideHover(document, position) {
      const range = document.getWordRangeAtPosition(position);
      if (!range) {
        return null;
      }
      const word = document.getText(range);
      const analysis = analysisCache.get(document.uri.toString());
      if (analysis) {
        const key = `${position.line + 1}:${range.start.character + 1}`;
        const narrowed = analysis.narrowed_types && analysis.narrowed_types[key];
        const declared = analysis.variable_types && analysis.variable_types[word];
        if (narrowed || declared) {
          const lines = [`**${word}**`];
          if (declared) {
            lines.push(`Declared: \`${declared}\``);
          }
          if (narrowed) {
            lines.push(`Narrowed here: \`${narrowed}\``);
          }
          return new vscode.Hover(new vscode.MarkdownString(lines.join('\n\n')));
        }
      }
      const hints = {
        loop: 'C-style: `loop (int i = 0, i < n, i++) { ... }`\nWhile-style: `loop (condition) { ... }`',
        function: 'Top-level function: `function name(args) { ... }`\nTyped: `function int name(args) { return 0 }`',
        var: 'Type-inferred variable: `var name = value`\nThe inferred type is fixed; later assignments must match.',
        interface: 'Abstract type: `interface Name { action() }`, `interface Name { int capacity() }`, or a nominal return `interface Factory { Button createButton() }`.\nMethods are always public/abstract — omit access modifiers. No bodies; implementing classes use `public`.',
        implements: 'Class implements interface(s): `class Car implements Startable { ... }`',
        class: 'Class: `class Name { ... }`\nInheritance: `class Child inherits Parent { ... }`\nInterfaces: `class Name implements Iface { ... }`',
        struct: 'Value type (fields only): `package struct Damage { int amount }`\nConstruct with `Damage(20)` / `Damage(amount=20)`. Fields are always public; use `global`/`package`/`module` on the struct. Copied on assign/call.',
        data: 'Immutable value object: `data Money { int amountCents\n  string currency }`\nStructural `==` over all fields; fields implicitly fix. No methods/inherits/uses.',
        entity: 'Identity-keyed type: `entity Customer identity(customerId) { private fix int customerId … }`\n`==` uses identity fields only. Root needs `identity(...)`; keys must be `fix`. May inherit another entity.',
        identity: 'Entity key clause: `entity Name identity(id, …) { … }`.\nRoot entities require it; derived entities may omit (share parent keys) or append local fix fields.',
        lambda: 'Function type / keyword: `lambda<int -> bool> isEven = n => n % 2 == 0`.\nParams left of `->`, return right; sugar `lambda<R>` / `lambda<-> R>` for zero params.\nCapture by value; captured names read-only unless `shared` or `atomic`. Body: `=> expr` or `=> { … }`.',
        enum: 'Closed nominal set: `enum HttpStatus { OK = 200 }`\nMembers: `HttpStatus.OK`. Use `.value` for the underlying int/string. Prefer SCREAMING_SNAKE_CASE names.',
        trait: 'Composable behavior (not a type): `trait Printable { requires string name\n  string label() { return this.name } }`\nCompose with `class C uses Printable { … }`.',
        uses: 'Compose traits onto a class: `class Product uses Printable { … }` or remap requires: `uses Printable(name: title)`.\nPlaced after `inherits` and before `implements`. Remapping applies only to `requires`, not trait method names.',
        requires: 'Trait host obligation: `requires string name` or `requires int compareTo(Product other)`.\nThe using class (or ancestor) must supply it. Spelling is exact — `require` (no s) is an error.',
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
        closed: 'Prevents inheritance: `closed class Ship { ... }`. No class may use `inherits` on a closed class. Mutually exclusive with `abstract`.',
        open: 'Marks a method as an overridable extension point: `public open string speak()`. Subclasses plug in with `override`.',
        override: 'Plugs into an ancestor `open` or abstract method (or root `toString`/`equals`/`hashCode`): `public override string speak()`. Use `override closed` to seal the chain.',
        constructor: 'Explicit constructor: `public constructor(...) { ... }` (not the type name). Use `this(...)` to chain overloads and `super(...)` for the parent.',
        static: 'Class-wide member: `public static int total = 0` / `public static int getTotal()`. No `this` inside static methods; cannot combine with open/override. Access as `ClassName.member`.',
        abstract: 'Abstract class or method: `abstract class Shape { public abstract float area() }`.\nConcrete subclasses must `override` every abstract method. Cannot write `closed abstract`. Do not instantiate an abstract class.',
        void: 'No return value: `public void add(string item) { … }` or `public abstract void add(string item)`.\nA `void` method must not `return expr` (bare `return` is ok).',
        import: 'Import exports: `import funcs`, `import all from funcs.pys`, or `import name from funcs.pys`.',
        from: 'Used in `import name from module.pys` / `import all from module.pys`.',
        tasks: 'Structured concurrency group: `tasks { task { … } }`. Leaving the block waits for all children.',
        task: 'One concurrent unit inside `tasks`. Named: `task ready { return 1 }` then `await ready` in a sibling.',
        await: 'Wait until a value is ready (named task handle / future). Only inside a `task` body.',
        shared: 'Visibility of cross-task mutation: `shared int counter = 0`. Does **not** make `+=` race-free — use `atomic` for indivisible RMW.',
        atomic: 'Indivisible RMW cell: `atomic int counter = 0`.\nImplies shared for capture. Ops: `+=`/`-=`/`++`/`--`, `get()`, `compareAndSet(expected, new)`. Rejects `*=`/`/=`/`%=`.',
        result: 'Recoverable outcome: `result<Value, Error>`. Construct with `ok(value)` or `error(payload)`; handle with exhaustive `switch` or postfix `propagate`.',
        nullable: 'Explicit absence: `nullable<string> name = null`.\nPlain `string` never holds null. Check before use (`if (name != null) { … }`). Not the same as `result` (failure) or empty string/zero.',
        ok: 'Success constructor for an expected `result<T, E>`: `ok(value)`. Use `ok()` only for `result<void, E>`.',
        error: 'Failure constructor for an expected `result<T, E>`: `error(payload)`. An error payload is always required. Because `error` is a keyword, bind switch payloads as `message` (or another name), not `error`.',
        propagate: 'Postfix result handling: `load() propagate`. Success yields the value; failure immediately returns the same error. At the entrypoint, an unhandled error becomes a panic.',
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
    const extra = [symbol];
    // Opt-in: resolve into locked pys.deps Python (ADR-001). Diagnostics stay fail-closed.
    const navigateLibs = vscode.workspace.getConfiguration('pys').get('navigateLibrarySources', false);
    if (navigateLibs && vscode.workspace.isTrusted) {
      extra.push('--library-sources');
    }
    const spec = buildWorkspaceIdeProcessSpec(
      context.extensionPath,
      workspacePath,
      document.uri.fsPath,
      extra,
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

  async function findSymbolUsages(document, symbol, token, position) {
    const workspace = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
    if (!workspace || !symbol) {
      return [];
    }
    const workspacePath = workspace.uri.fsPath;
    const pythonExecutable = process.platform === 'win32' ? 'python' : 'python3';
    const extra = ['--usages', symbol];
    if (position) {
      extra.push('--line', String(position.line + 1), '--column', String(position.character + 1));
    }
    const spec = buildWorkspaceIdeProcessSpec(
      context.extensionPath,
      workspacePath,
      document.uri.fsPath,
      extra,
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
      const usages = (parsed && parsed.usages) || [];
      return usages
        .filter((u) => u && u.file)
        .map((u) => {
          const uri = vscode.Uri.file(u.file);
          const line = Math.max((u.line || 1) - 1, 0);
          const column = Math.max((u.column || 1) - 1, 0);
          const endCol = Math.max((u.end_column || (u.column || 1) + 1) - 1, 0);
          const range = new vscode.Range(
            new vscode.Position(line, column),
            new vscode.Position(line, endCol),
          );
          return new vscode.Location(uri, range);
        });
    } catch (_error) {
      return [];
    }
  }

  context.subscriptions.push(vscode.languages.registerReferenceProvider({ language: 'pys' }, {
    async provideReferences(document, position, _refContext, token) {
      const symbol = getDottedPathAt(document, position);
      if (!symbol) {
        return [];
      }
      return findSymbolUsages(document, symbol, token, position);
    },
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

      const unknownType = diagnostics.find((diagnostic) => diagnostic.code === 'pys.unknown-type');
      if (unknownType) {
        const unknownKey = `${document.uri.toString()}:${unknownType.range.start.line + 1}:pys.unknown-type`;
        const unknownMeta = errorMeta.get(unknownKey);
        if (unknownMeta && unknownMeta.suggested_fix === 'create-class') {
          const unknownMatch = /Unknown type '([^']+)'/.exec(String(unknownType.message || ''));
          const typeName = unknownMatch ? unknownMatch[1] : '';
          const fix = new vscode.CodeAction(
            typeName ? `Create class '${typeName}'` : 'Create missing class',
            vscode.CodeActionKind.QuickFix,
          );
          fix.diagnostics = [unknownType];
          fix.isPreferred = true;
          fix.command = {
            command: 'pys.generate.createClass',
            title: typeName ? `Create class '${typeName}'` : 'Create missing class',
            arguments: [{
              line: unknownType.range.start.line,
              character: unknownType.range.start.character,
              typeName,
            }],
          };
          actions.push(fix);
        }
      }

      const abstractMethod = diagnostics.find((diagnostic) => diagnostic.code === 'pys.abstract-method');
      if (abstractMethod) {
        const abstractKey = `${document.uri.toString()}:${abstractMethod.range.start.line + 1}:pys.abstract-method`;
        const abstractMeta = errorMeta.get(abstractKey);
        const suggested = abstractMeta && abstractMeta.suggested_fix;
        const classMatch = suggested
          ? /^abstract class ([A-Za-z_]\w*)$/.exec(String(suggested))
          : null;
        const className = classMatch ? classMatch[1] : '';
        const header = findEnclosingClassHeader(document, abstractMethod.range.start.line, className);
        if (header && !header.alreadyAbstract) {
          const fix = new vscode.CodeAction(
            className ? `Make class '${className}' abstract` : 'Make class abstract',
            vscode.CodeActionKind.QuickFix,
          );
          fix.diagnostics = [abstractMethod];
          fix.isPreferred = true;
          fix.edit = new vscode.WorkspaceEdit();
          if (header.closed) {
            fix.edit.replace(
              document.uri,
              new vscode.Range(
                new vscode.Position(header.line, header.closedIndex),
                new vscode.Position(header.line, header.closedIndex + 'closed '.length),
              ),
              'abstract ',
            );
          } else {
            fix.edit.insert(
              document.uri,
              new vscode.Position(header.line, header.classIndex),
              'abstract ',
            );
          }
          actions.push(fix);
        }
      }

      const entrypointConflict = diagnostics.find(
        (diagnostic) => diagnostic.code === 'pys.entrypoint-conflict',
      );
      if (entrypointConflict) {
        const fix = new vscode.CodeAction(
          'Set this file as entrypoint',
          vscode.CodeActionKind.QuickFix,
        );
        fix.diagnostics = [entrypointConflict];
        fix.isPreferred = true;
        fix.command = {
          command: 'pys.setAsEntrypoint',
          title: 'Set as entrypoint',
          arguments: [document.uri],
        };
        actions.push(fix);
      }

      const packageMismatch = diagnostics.find((diagnostic) => diagnostic.code === 'pys.package-mismatch');
      if (packageMismatch) {
        const key = `${document.uri.toString()}:${packageMismatch.range.start.line + 1}:pys.package-mismatch`;
        const meta = errorMeta.get(key);
        const suggested = meta && meta.suggested_fix;
        if (suggested) {
          const fix = new vscode.CodeAction(
            `Move file to ${suggested}`,
            vscode.CodeActionKind.QuickFix,
          );
          fix.diagnostics = [packageMismatch];
          fix.isPreferred = true;
          fix.command = {
            command: 'pys.moveToSuggestedPackagePath',
            title: 'Move file to suggested package path',
            arguments: [document.uri, suggested],
          };
          actions.push(fix);
        }
      }

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

      const requireTypo = diagnostics.find((diagnostic) => diagnostic.code === 'pys.trait-require-typo');
      if (requireTypo) {
        const key = `${document.uri.toString()}:${requireTypo.range.start.line + 1}:pys.trait-require-typo`;
        const meta = errorMeta.get(key);
        const suggested = (meta && meta.suggested_fix) || 'requires';
        const fix = new vscode.CodeAction(
          `Change \`require\` to \`${suggested}\``,
          vscode.CodeActionKind.QuickFix,
        );
        fix.diagnostics = [requireTypo];
        fix.isPreferred = true;
        fix.edit = new vscode.WorkspaceEdit();
        fix.edit.replace(document.uri, requireTypo.range, suggested);
        actions.push(fix);
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
        if (diagnostic.code !== 'pys.var-as-type') {
          continue;
        }
        const key = `${document.uri.toString()}:${diagnostic.range.start.line + 1}:${diagnostic.code}`;
        const meta = errorMeta.get(key);
        const suggested = meta && meta.suggested_fix;
        const line = document.lineAt(diagnostic.range.start.line);
        const text = line.text;
        if (suggested && suggested !== 'object' && new RegExp(`\\bvar\\s+${suggested}\\b`).test(text)) {
          const fix = new vscode.CodeAction('Omit parameter type (`var`)', vscode.CodeActionKind.QuickFix);
          fix.diagnostics = [diagnostic];
          fix.isPreferred = true;
          fix.edit = new vscode.WorkspaceEdit();
          fix.edit.replace(
            document.uri,
            line.range,
            text.replace(new RegExp(`\\bvar\\s+(${suggested})\\b`), '$1'),
          );
          actions.push(fix);
          continue;
        }
        const match = /\bvar\b/.exec(text);
        if (!match) {
          continue;
        }
        const fix = new vscode.CodeAction('Replace `var` with `object`', vscode.CodeActionKind.QuickFix);
        fix.diagnostics = [diagnostic];
        fix.isPreferred = true;
        fix.edit = new vscode.WorkspaceEdit();
        const start = new vscode.Position(line.lineNumber, match.index);
        const end = new vscode.Position(line.lineNumber, match.index + 3);
        fix.edit.replace(document.uri, new vscode.Range(start, end), 'object');
        actions.push(fix);
      }

      for (const diagnostic of diagnostics) {
        if (diagnostic.code !== 'pys.indent') {
          continue;
        }
        const key = `${document.uri.toString()}:${diagnostic.range.start.line + 1}:${diagnostic.code}`;
        const meta = errorMeta.get(key);
        const suggested = meta && meta.suggested_fix;
        if (!suggested) {
          continue;
        }
        const fix = new vscode.CodeAction('Fix indentation', vscode.CodeActionKind.QuickFix);
        fix.diagnostics = [diagnostic];
        fix.isPreferred = true;
        fix.edit = new vscode.WorkspaceEdit();
        const line = document.lineAt(diagnostic.range.start.line);
        fix.edit.replace(document.uri, line.range, suggested);
        actions.push(fix);
      }

      for (const diagnostic of diagnostics) {
        if (diagnostic.code !== 'pys.null-non-nullable') {
          continue;
        }
        const key = `${document.uri.toString()}:${diagnostic.range.start.line + 1}:${diagnostic.code}`;
        const meta = errorMeta.get(key);
        const suggested = meta && meta.suggested_fix;
        if (!suggested) {
          continue;
        }
        const fix = new vscode.CodeAction('Make type nullable', vscode.CodeActionKind.QuickFix);
        fix.diagnostics = [diagnostic];
        fix.isPreferred = true;
        fix.edit = new vscode.WorkspaceEdit();
        const line = document.lineAt(diagnostic.range.start.line);
        fix.edit.replace(document.uri, line.range, suggested);
        actions.push(fix);
      }

      for (const diagnostic of diagnostics) {
        if (diagnostic.code !== 'pys.nullable-use-before-check') {
          continue;
        }
        const line = document.lineAt(diagnostic.range.start.line);
        const match = /\b([A-Za-z_]\w*)\s*\./.exec(line.text);
        if (!match) {
          continue;
        }
        const name = match[1];
        const indent = line.text.match(/^\s*/)?.[0] || '';
        const body = line.text.trim();
        const fix = new vscode.CodeAction('Surround with null check', vscode.CodeActionKind.QuickFix);
        fix.diagnostics = [diagnostic];
        fix.isPreferred = true;
        fix.edit = new vscode.WorkspaceEdit();
        fix.edit.replace(
          document.uri,
          line.range,
          `${indent}if (${name} != null) {\n${indent}\t${body}\n${indent}}`,
        );
        actions.push(fix);
      }

      for (const diagnostic of diagnostics) {
        if (diagnostic.code !== 'pys.null-redundant-check') {
          continue;
        }
        const key = `${document.uri.toString()}:${diagnostic.range.start.line + 1}:${diagnostic.code}`;
        const warning = warningMeta.get(key);
        const suggested = warning && warning.suggested_fix;
        if (suggested) {
          const fix = new vscode.CodeAction('Remove redundant null check', vscode.CodeActionKind.QuickFix);
          fix.diagnostics = [diagnostic];
          fix.edit = new vscode.WorkspaceEdit();
          fix.edit.replace(document.uri, diagnostic.range, suggested);
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
    refreshMainFileUi();
    if (editor && editor.document.languageId === 'pys') {
      syncErrorDecorations(editor.document);
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
    if (event.affectsConfiguration('pys.emitTarget')) {
      refreshEmitTargetUi();
    }
    if (event.affectsConfiguration('pys.intellisense')) {
      refreshIntellisenseUi();
    }
  }));
  const manifestWatcher = vscode.workspace.createFileSystemWatcher('**/pys.toml');
  context.subscriptions.push(
    manifestWatcher,
    manifestWatcher.onDidCreate(refreshMainFileUi),
    manifestWatcher.onDidChange(refreshMainFileUi),
    manifestWatcher.onDidDelete(refreshMainFileUi),
  );

  for (const document of vscode.workspace.textDocuments) {
    if (document.languageId === 'pys') {
      scheduleValidate(document);
    }
  }

  refreshMainFileUi();
  refreshEmitTargetUi();

  async function saveAllFiles() {
    try {
      return vscode.workspace.saveAll();
    } catch (error) {
      console.error('Failed to save all files before run/debug:', error);
      return false;
    }
  }

  function getPythonExecutable() {
    return probePython() || (process.platform === 'win32' ? 'python' : 'python3');
  }

  /** @type {Set<string>} session-local "don't ask again" for missing runtimes on Run */
  const runtimePromptDismissed = new Set();

  /**
   * @param {'python' | 'node'} kind
   * @param {{ force?: boolean }} [options]
   * @returns {Promise<boolean>} true when the runtime is available (or install was started)
   */
  async function ensureRuntimeKind(kind, options = {}) {
    const force = Boolean(options.force);
    const found = kind === 'node' ? probeNode() : probePython();
    if (found) {
      return true;
    }
    if (!vscode.workspace.isTrusted) {
      vscode.window.showErrorMessage(
        kind === 'node'
          ? 'Trust this workspace before installing Node.js.'
          : 'Trust this workspace before installing Python.',
      );
      return false;
    }
    if (!force && runtimePromptDismissed.has(kind)) {
      vscode.window.showErrorMessage(
        kind === 'node'
          ? 'Node.js was not found on PATH. Install Node, then reload the IDE.'
          : 'Python was not found on PATH. Install Python, then reload the IDE.',
      );
      return false;
    }
    const label = kind === 'node' ? 'Node.js' : 'Python';
    const choice = await vscode.window.showErrorMessage(
      `${label} is not on PATH. Install a stable version now?`,
      'Install',
      'Not now',
    );
    if (choice !== 'Install') {
      if (!force) {
        runtimePromptDismissed.add(kind);
      }
      return false;
    }
    const versions = stableVersionsFor(kind);
    const picked = await vscode.window.showQuickPick(
      versions.map((v) => ({
        label: v.label,
        description: v.description,
        detail: v.id,
        versionId: v.id,
      })),
      {
        title: `Select ${label} version`,
        placeHolder: 'Stable releases shipped with the extension catalog',
      },
    );
    if (!picked) {
      return false;
    }
    const plan = installPlan(kind, picked.versionId, process.platform);
    const term = vscode.window.createTerminal({
      name: `Install ${label}`,
    });
    term.show();
    term.sendText(terminalInstallLine(plan), true);
    vscode.window.showInformationMessage(
      `${plan.hint} After install completes, reload the window so PATH updates.`,
    );
    // Install is asynchronous in a terminal; Create/Run should not continue as if ready.
    return false;
  }

  /**
   * @param {string} emitTarget
   * @param {{ force?: boolean }} [options]
   * @returns {Promise<boolean>}
   */
  async function ensureRuntimesForTarget(emitTarget, options = {}) {
    const needs = resolveToolchainNeeds(emitTarget);
    if (needs.python) {
      const ok = await ensureRuntimeKind('python', options);
      if (!ok) {
        return false;
      }
    }
    if (needs.node) {
      const ok = await ensureRuntimeKind('node', options);
      if (!ok) {
        return false;
      }
    }
    return true;
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

  async function lockDepsFile(filePath) {
    if (!filePath) {
      vscode.window.showErrorMessage(
        'No dependency file selected. Right-click pys.toml (or legacy pys.deps) in the explorer.',
      );
      return;
    }
    if (!vscode.workspace.isTrusted) {
      vscode.window.showErrorMessage('Trust this workspace before locking PYS dependencies.');
      return;
    }
    const workspace = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
    if (!workspace) {
      vscode.window.showErrorMessage('Open a workspace before locking PYS dependencies.');
      return;
    }
    filePath = resolveWorkspaceFile(workspace.uri.fsPath, filePath);
    if (!filePath) {
      vscode.window.showErrorMessage('Dependency file must resolve inside the workspace.');
      return;
    }
    const base = path.basename(filePath);
    if (base !== 'pys.toml' && base !== 'pys.deps') {
      vscode.window.showErrorMessage(
        'Run Deps Lock only works on pys.toml (or legacy pys.deps).',
      );
      return;
    }
    const bundled = ensureBundledTranspiler();
    if (!bundled) {
      return;
    }
    if (!fs.existsSync(filePath)) {
      vscode.window.showErrorMessage(`Dependency file not found: ${filePath}`);
      return;
    }
    if (base === 'pys.toml') {
      try {
        const text = fs.readFileSync(filePath, 'utf8');
        const hasNpm = /\[dependencies\.npm\]/.test(text);
        const hasInterpreter = /\[interpreter\]/.test(text);
        // Python package pins sit under [dependencies] but not [dependencies.npm].
        const depsBlock = text.match(/\[dependencies\]([\s\S]*?)(?=\n\[|$)/);
        const pythonDepLines = depsBlock
          ? depsBlock[1]
              .split(/\r?\n/)
              .map((line) => line.trim())
              .filter((line) => line && !line.startsWith('#') && !line.startsWith('['))
          : [];
        if (hasNpm && !hasInterpreter && pythonDepLines.length === 0) {
          vscode.window.showInformationMessage(
            'This pys.toml only has [dependencies.npm]. No pys.lock — npm packages install on Run Project / Run into ~/.pys/repository/npm/.',
          );
          return;
        }
      } catch (_error) {
        // Fall through to CLI lock for parse/read failures.
      }
    }
    const saved = await saveAllFiles();
    if (!saved) {
      vscode.window.showErrorMessage('Unable to save files before locking dependencies.');
      return;
    }
    filePath = resolveWorkspaceFile(workspace.uri.fsPath, filePath);
    if (!filePath) {
      vscode.window.showErrorMessage('Dependency file left the workspace before lock.');
      return;
    }
    const pythonExecutable = getPythonExecutable();
    const workDir = path.dirname(filePath);
    const term = vscode.window.createTerminal({
      name: 'PYS Deps',
      cwd: workDir,
      env: buildRunEnv(bundled, workspace.uri.fsPath),
    });
    term.show();
    term.sendText(
      `${pythonExecutable} -m transpiler deps lock ${shellQuote(filePath)}`,
      true
    );
  }

  function resolveTargetDepsFile(file) {
    let filePath = resolveFilePath(file);
    if (!filePath && vscode.window.activeTextEditor) {
      const active = vscode.window.activeTextEditor.document;
      const base = path.basename(active.uri.fsPath);
      if (base === 'pys.toml' || base === 'pys.deps') {
        filePath = active.uri.fsPath;
      }
    }
    const workspace = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
    if (!filePath || !workspace) {
      return null;
    }
    return resolveWorkspaceFile(workspace.uri.fsPath, filePath);
  }

  async function reconcileConfiguredEntrypoint(filePath, workspacePath, verb) {
    const manifest = findProjectManifest(filePath, workspacePath);
    const configured = resolveManifestMain(manifest);
    if (!configured || path.resolve(configured) === path.resolve(filePath)) {
      return filePath;
    }
    const choice = await vscode.window.showErrorMessage(
      `${path.basename(filePath)} is not the configured entrypoint (${path.basename(configured)}).`,
      `${verb} configured entrypoint`,
      'Set as entrypoint',
    );
    if (choice === 'Set as entrypoint') {
      await vscode.commands.executeCommand('pys.setAsEntrypoint', vscode.Uri.file(filePath));
      return null;
    }
    if (choice === `${verb} configured entrypoint`) {
      return configured;
    }
    return null;
  }

  async function runPysFile(filePath, options = {}) {
    if (!filePath) {
      vscode.window.showErrorMessage('No PYS file to run. Set an entrypoint or open a .pys file.');
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
    if (!options.skipEntrypointReconcile) {
      filePath = await reconcileConfiguredEntrypoint(
        filePath,
        workspace.uri.fsPath,
        'Run',
      );
      if (!filePath) {
        return;
      }
    }
    const emitTarget = options.emitTarget || getEmitTarget();
    if (!(await ensureRuntimesForTarget(emitTarget))) {
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
      name: emitTarget === 'javascript' ? 'Run PYS (Node)' : 'Run PYS',
      cwd: workDir,
      env: buildRunEnv(bundled, workspace.uri.fsPath),
    });
    term.show();
    term.sendText(
      `${pythonExecutable} -m transpiler run ${shellQuote(filePath)} --target ${emitTarget}`,
      true
    );
  }

  async function runProjectFromToml(file) {
    const manifestPath = resolveTargetDepsFile(file);
    if (!manifestPath || path.basename(manifestPath).toLowerCase() !== 'pys.toml') {
      vscode.window.showErrorMessage('Select a pys.toml file to run the project.');
      return;
    }
    let relativeMain = '';
    let emitTarget = 'python';
    try {
      const text = fs.readFileSync(manifestPath, 'utf8');
      relativeMain = readProjectMain(text);
      emitTarget = readProjectTarget(text) || 'python';
    } catch (error) {
      const message = error && error.message ? String(error.message) : String(error);
      vscode.window.showErrorMessage(message);
      return;
    }
    if (!relativeMain) {
      vscode.window.showErrorMessage(
        'Set [project].main in pys.toml before using Run Project.',
      );
      return;
    }
    const mainPath = resolveManifestMain(manifestPath);
    if (!mainPath || !fs.existsSync(mainPath)) {
      vscode.window.showErrorMessage(
        `Configured entrypoint does not exist: ${relativeMain}`,
      );
      return;
    }
    await runPysFile(mainPath, {
      emitTarget,
      skipEntrypointReconcile: true,
    });
  }

  async function debugPysFile(filePath, mode = 'pys') {
    const emitTarget = getEmitTarget();
    const debugMode = debugModeOptions(mode, emitTarget);
    if (!filePath) {
      vscode.window.showErrorMessage('No PYS file to debug. Set an entrypoint or open a .pys file.');
      return;
    }
    if (!vscode.workspace.isTrusted) {
      vscode.window.showErrorMessage('Trust this workspace before debugging PYS files.');
      return;
    }
    if (!(await ensureRuntimesForTarget(emitTarget))) {
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
    filePath = await reconcileConfiguredEntrypoint(
      filePath,
      workspace.uri.fsPath,
      'Debug',
    );
    if (!filePath) {
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

    if (emitTarget === 'python') {
      const pythonExt = vscode.extensions.getExtension('ms-python.python');
      if (!pythonExt) {
        vscode.window.showErrorMessage(
          'Install the Microsoft Python extension to debug PYS (source-level stepping uses debugpy).',
        );
        return;
      }
      if (!pythonExt.isActive) {
        await pythonExt.activate();
      }
    }

    const outDir = fs.mkdtempSync(path.join(os.tmpdir(), 'pys-debug-'));
    const pythonExecutable = getPythonExecutable();
    const env = buildRunEnv(bundled, workspace.uri.fsPath);
    let prepared;
    try {
      prepared = await runJsonProcess(
        pythonExecutable,
        [
          '-m',
          'transpiler.ide',
          '--prepare-debug',
          outDir,
          filePath,
          '--target',
          emitTarget,
        ],
        { cwd: path.dirname(filePath), env },
        { timeoutMs: 60_000 },
      );
    } catch (error) {
      try {
        fs.rmSync(outDir, { recursive: true, force: true });
      } catch (_err) {
        /* ignore */
      }
      vscode.window.showErrorMessage(
        `Failed to prepare PYS debug session: ${error && error.message ? error.message : error}`,
      );
      return;
    }
    if (!prepared || !prepared.ok) {
      try {
        fs.rmSync(outDir, { recursive: true, force: true });
      } catch (_err) {
        /* ignore */
      }
      const msg =
        (prepared && prepared.error && prepared.error.message) ||
        (prepared && prepared.message) ||
        'prepare_debug failed';
      vscode.window.showErrorMessage(`Cannot debug PYS: ${msg}`);
      return;
    }

    const registry = loadMapRegistry(prepared.maps || {});
    const runEnv = buildRunEnv(bundled, workspace.uri.fsPath);
    const prepend = prepared.pythonpath_prepend;
    if (prepend) {
      const existing = runEnv.PYTHONPATH || '';
      runEnv.PYTHONPATH = existing
        ? `${prepend}${path.delimiter}${existing}`
        : prepend;
    }

    pendingPysDebug = {
      dir: outDir,
      registry,
      bpReqPysBySeq: new Map(),
      remapSource: debugMode.remapSource,
      stepFilter: new PysStepFilter({
        enabled: debugMode.pysOnlyStepping,
      }),
    };
    if (debugMode.revealGenerated) {
      await vscode.window.showTextDocument(vscode.Uri.file(prepared.main), {
        preview: false,
      });
    }
    // Student program is the launch target (not `transpiler run` subprocess).
    const launchConfig = buildLaunchConfig({
      prepared,
      debugMode,
      runEnv,
      cwd: path.dirname(filePath),
      emitTarget,
    });
    const started = await vscode.debug.startDebugging(workspace, launchConfig);
    if (!started) {
      pendingPysDebug = null;
      try {
        fs.rmSync(outDir, { recursive: true, force: true });
      } catch (_err) {
        /* ignore */
      }
    }
  }

  async function fetchFrameLocalValues(session, frameId) {
    /** @type {Map<string, string>} */
    const values = new Map();
    if (!session || typeof frameId !== 'number') {
      return values;
    }
    try {
      const scopesResp = await session.customRequest('scopes', { frameId });
      const scopes = (scopesResp && scopesResp.scopes) || [];
      for (const scope of scopes) {
        if (!scope || scope.expensive) {
          continue;
        }
        const label = String(scope.name || '').toLowerCase();
        // Locals / arguments only — not Globals / Builtins / Module.
        if (
          label.includes('global') ||
          label.includes('builtin') ||
          label.includes('module')
        ) {
          continue;
        }
        const varsResp = await session.customRequest('variables', {
          variablesReference: scope.variablesReference,
        });
        for (const v of (varsResp && varsResp.variables) || []) {
          if (!v || typeof v.name !== 'string' || typeof v.value !== 'string') {
            continue;
          }
          if (shouldHideInlineName(v.name)) {
            continue;
          }
          values.set(v.name, formatPysDebugValue(v.value));
        }
      }
    } catch (_err) {
      /* ignore — fall back to empty (no inline values) */
    }
    return values;
  }

  function shouldHideInlineName(name) {
    return (
      name.startsWith('_pys_') ||
      name.startsWith('__pys_') ||
      name.startsWith('_Pys') ||
      name.startsWith('__')
    );
  }

  function truncateInlineValue(text, max = 80) {
    const s = String(text);
    if (s.length <= max) {
      return s;
    }
    return `${s.slice(0, max - 1)}…`;
  }

  async function processPysStepStop(session, entry, message) {
    try {
      const result = await entry.stepFilter.handleStopped(
        message,
        async (threadId) => {
          if (typeof threadId !== 'number') {
            return null;
          }
          entry.captureStepProbe = true;
          entry.stepProbeLocation = null;
          try {
            await session.customRequest('stackTrace', {
              threadId,
              startFrame: 0,
              levels: 1,
            });
          } finally {
            entry.captureStepProbe = false;
          }
          const location = entry.stepProbeLocation;
          if (!location) {
            return null;
          }
          return {
            line: location.pysLine,
            source: { path: location.pysPath },
            generatedSource: {
              path: location.pyPath,
              line: location.pyLine,
            },
          };
        },
        async (command, args) => {
          await session.customRequest(command, args);
        },
      );
      if (result === 'limit') {
        vscode.window.showWarningMessage(
          `PYS-only stepping stopped after ${DEFAULT_MAX_SKIPS} generated steps. ` +
            'Disable the PYS-only toolbar filter to inspect this code.',
        );
      }
    } catch (error) {
      entry.stepFilter.cancelOperation();
      const detail = error && error.message ? `: ${error.message}` : '';
      vscode.window.showWarningMessage(
        `PYS-only stepping could not continue${detail}`,
      );
    }
  }

  context.subscriptions.push(
    vscode.languages.registerInlineValuesProvider('pys', {
      async provideInlineValues(document, viewPort, context) {
        const cfg = vscode.workspace.getConfiguration('pys');
        if (cfg.get('debug.inlineValues') === false) {
          return [];
        }
        const session = vscode.debug.activeDebugSession;
        if (!session || session.name !== PYS_DEBUG_SESSION_NAME) {
          return [];
        }
        const localValues = await fetchFrameLocalValues(session, context.frameId);
        if (!localValues.size) {
          return [];
        }
        const stoppedLine0 = context.stoppedLocation.end.line;
        const stoppedLine1 = stoppedLine0 + 1;
        const skipTypes = [...PYS_TYPES, 'list', 'dict', 'tuple', 'set'];
        let sites = collectInlineValueSites(document.getText(), stoppedLine1, {
          keywords: PYS_KEYWORDS,
          types: skipTypes,
        });
        sites = filterInlineValueSitesByScope(sites, localValues);
        const start = viewPort.start.line;
        const end = Math.min(viewPort.end.line, stoppedLine0);
        const out = [];
        for (const site of sites) {
          if (site.line < start || site.line > end) {
            continue;
          }
          const value = localValues.get(site.name);
          if (value === undefined) {
            continue;
          }
          out.push(
            new vscode.InlineValueText(
              new vscode.Range(site.line, site.column, site.line, site.column + site.length),
              `${site.name}: ${truncateInlineValue(value)}`,
            ),
          );
        }
        return out;
      },
    }),
  );

  function createPysDebugAdapterTracker(session) {
    if (!isPysDebugSession(session.name)) {
      return {};
    }
    if (pendingPysDebug) {
      if (!pendingPysDebug.bpReqPysBySeq) {
        pendingPysDebug.bpReqPysBySeq = new Map();
      }
      if (!pendingPysDebug.stepFilter) {
        pendingPysDebug.stepFilter = new PysStepFilter({
          enabled: pendingPysDebug.remapSource,
        });
      }
      pysDebugSessions.set(session.id, pendingPysDebug);
      pendingPysDebug = null;
      void syncPysStepContexts(session);
    }
    return {
      onWillReceiveMessage(message) {
        const entry = pysDebugSessions.get(session.id);
        if (!entry || !message) {
          return;
        }
        entry.stepFilter.observeRequest(message);
        if (
          message.command === 'stackTrace' &&
          entry.captureStepProbe
        ) {
          entry.stepProbeRequestSeq = message.seq;
          entry.captureStepProbe = false;
        }
        if (message.command === 'setBreakpoints' && message.arguments) {
          const src = message.arguments.source && message.arguments.source.path;
          if (src && String(src).toLowerCase().endsWith('.pys')) {
            entry.bpReqPysBySeq.set(message.seq, src);
          }
          message.arguments = remapSetBreakpointsArgs(
            entry.registry,
            message.arguments,
          );
        }
        if (
          entry.remapSource &&
          message.command === 'evaluate' &&
          message.arguments
        ) {
          const expr = message.arguments.expression;
          const rewritten = rewriteEvaluateExpression(entry.registry, expr);
          if (rewritten !== expr) {
            message.arguments = {
              ...message.arguments,
              expression: rewritten,
            };
          }
        }
      },
      onDidSendMessage(message) {
        const entry = pysDebugSessions.get(session.id);
        if (!entry || !message) {
          return;
        }
        if (
          entry.remapSource &&
          message.type === 'response' &&
          message.command === 'stackTrace' &&
          message.body &&
          message.body.stackFrames
        ) {
          const rawTop = message.body.stackFrames[0];
          const rawPath = rawTop && rawTop.source && rawTop.source.path;
          const exactLocation =
            rawPath && typeof rawTop.line === 'number'
              ? mapExactPyStackFrame(
                  entry.registry,
                  rawPath,
                  rawTop.line,
                )
              : null;
          entry.stepFilter.recordTopFrame(
            exactLocation
              ? {
                  line: exactLocation.pysLine,
                  source: { path: exactLocation.pysPath },
                  generatedSource: {
                    path: rawPath,
                    line: rawTop.line,
                  },
                }
              : null,
          );
          if (message.request_seq === entry.stepProbeRequestSeq) {
            entry.stepProbeLocation =
              exactLocation && rawPath
                ? {
                    ...exactLocation,
                    pyPath: rawPath,
                    pyLine: rawTop.line,
                  }
                : null;
            entry.stepProbeRequestSeq = null;
          }
          message.body.stackFrames = remapStackFrames(
            entry.registry,
            message.body.stackFrames,
          );
        }
        if (
          message.type === 'response' &&
          message.command === 'setBreakpoints' &&
          message.body
        ) {
          const pysPath = entry.bpReqPysBySeq.get(message.request_seq);
          entry.bpReqPysBySeq.delete(message.request_seq);
          message.body = remapSetBreakpointsResponse(
            entry.registry,
            message.body,
            pysPath,
          );
        }
        if (
          entry.remapSource &&
          message.type === 'event' &&
          message.event === 'breakpoint' &&
          message.body &&
          message.body.breakpoint
        ) {
          message.body.breakpoint = remapBreakpoint(
            entry.registry,
            message.body.breakpoint,
          );
        }
        if (
          entry.remapSource &&
          message.type === 'response' &&
          message.command === 'variables' &&
          message.body &&
          message.body.variables
        ) {
          message.body.variables = remapVariables(
            entry.registry,
            message.body.variables,
          );
        }
        if (
          entry.remapSource &&
          message.type === 'response' &&
          message.command === 'evaluate' &&
          message.body &&
          typeof message.body.result === 'string'
        ) {
          message.body.result = formatPysDebugValue(message.body.result);
        }
        if (
          message.type === 'event' &&
          message.event === 'stopped'
        ) {
          void processPysStepStop(session, entry, message);
        }
      },
    };
  }

  // Same tracker for debugpy (python) and js-debug (pwa-node).
  for (const adapterType of debugAdapterTypes()) {
    context.subscriptions.push(
      vscode.debug.registerDebugAdapterTrackerFactory(adapterType, {
        createDebugAdapterTracker: createPysDebugAdapterTracker,
      }),
    );
  }

  context.subscriptions.push(
    vscode.debug.onDidChangeActiveDebugSession((session) => {
      void syncPysStepContexts(session);
    }),
  );

  context.subscriptions.push(
    vscode.debug.onDidTerminateDebugSession((session) => {
      const entry = pysDebugSessions.get(session.id);
      if (!entry) {
        return;
      }
      entry.stepFilter.cancelOperation();
      pysDebugSessions.delete(session.id);
      const active = vscode.debug.activeDebugSession;
      void syncPysStepContexts(
        active && active.id !== session.id ? active : null,
      );
      try {
        fs.rmSync(entry.dir, { recursive: true, force: true });
      } catch (_err) {
        /* ignore */
      }
    }),
  );

  context.subscriptions.push(vscode.commands.registerCommand('pys.moveToSuggestedPackagePath', async (uri, suggestedRel) => {
    if (!uri || !suggestedRel) {
      return;
    }
    const fsPath = uri.fsPath || uri;
    let dir = path.dirname(fsPath);
    let projectRoot = null;
    while (true) {
      if (fs.existsSync(path.join(dir, 'pys.toml'))) {
        projectRoot = dir;
        break;
      }
      const parent = path.dirname(dir);
      if (parent === dir) {
        break;
      }
      dir = parent;
    }
    if (!projectRoot) {
      const wf = vscode.workspace.getWorkspaceFolder(uri);
      projectRoot = wf ? wf.uri.fsPath : path.dirname(fsPath);
    }
    const targetPath = path.join(projectRoot, suggestedRel);
    const targetUri = vscode.Uri.file(targetPath);
    await fs.promises.mkdir(path.dirname(targetPath), { recursive: true });
    const edit = new vscode.WorkspaceEdit();
    edit.renameFile(uri, targetUri, { overwrite: false });
    const ok = await vscode.workspace.applyEdit(edit);
    if (!ok) {
      vscode.window.showErrorMessage(`Could not move file to ${suggestedRel}`);
    }
  }));

  context.subscriptions.push(vscode.commands.registerCommand('pys.findUsages', async () => {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document.languageId !== 'pys') {
      return;
    }
    // Uses the ReferenceProvider registered above (Peek / References view).
    await vscode.commands.executeCommand('editor.action.referenceSearch.trigger');
  }));

  context.subscriptions.push(vscode.commands.registerCommand('pys.createProject', async () => {
    if (!vscode.workspace.isTrusted) {
      vscode.window.showErrorMessage('Trust this workspace before creating a PYS project.');
      return;
    }
    const targetPick = await vscode.window.showQuickPick(
      [
        {
          label: 'Python',
          description: 'CPython emit / run (reference)',
          detail: 'Writes [project].target = "python"',
          target: 'python',
        },
        {
          label: 'JavaScript',
          description: 'Node.js emit / run',
          detail: 'Writes [project].target = "javascript" (still needs Python for the transpiler)',
          target: 'javascript',
        },
      ],
      {
        title: 'PYS project emit target',
        placeHolder: 'Which backend should this project target?',
      },
    );
    if (!targetPick) {
      return;
    }
    const emitTarget = targetPick.target;
    if (!(await ensureRuntimesForTarget(emitTarget, { force: true }))) {
      vscode.window.showWarningMessage(
        'Create Project cancelled until the required runtime is installed. Run Create PYS Project again after install.',
      );
      return;
    }
    const folders = await vscode.window.showOpenDialog({
      canSelectFiles: false,
      canSelectFolders: true,
      canSelectMany: false,
      openLabel: 'Create PYS Project Here',
      title: 'Select a folder for the new PYS project',
    });
    if (!folders || !folders.length) {
      return;
    }
    const folderPath = folders[0].fsPath;
    try {
      const result = createPysProjectScaffold(folderPath, { target: emitTarget });
      const open = 'Open Folder';
      const choice = await vscode.window.showInformationMessage(
        `PYS project created in ${result.root} (src/, tests/, pys.toml, target=${result.target}).`,
        open,
      );
      if (choice === open) {
        await vscode.commands.executeCommand('vscode.openFolder', vscode.Uri.file(result.root), {
          forceNewWindow: false,
        });
      } else {
        await vscode.commands.executeCommand('revealInExplorer', vscode.Uri.file(result.root));
      }
    } catch (error) {
      const message = error && error.message ? String(error.message) : String(error);
      vscode.window.showErrorMessage(message);
    }
  }));

  context.subscriptions.push(vscode.commands.registerCommand('pys.lockDeps', async (file) => {
    await lockDepsFile(resolveTargetDepsFile(file));
  }));

  context.subscriptions.push(vscode.commands.registerCommand('pys.runProject', async (file) => {
    await runProjectFromToml(file);
  }));

  context.subscriptions.push(vscode.commands.registerCommand('pys.runFile', async (file) => {
    await runPysFile(resolveTargetPysFile(file));
  }));

  context.subscriptions.push(vscode.commands.registerCommand('pys.selectEmitTarget', async () => {
    const current = getEmitTarget();
    const picked = await vscode.window.showQuickPick(
      [
        {
          label: 'Python',
          description: 'CPython (reference backend)',
          detail: 'python -m transpiler run … --target python',
          target: 'python',
        },
        {
          label: 'JavaScript',
          description: 'Node.js MVP backend',
          detail: 'python -m transpiler run … --target javascript',
          target: 'javascript',
        },
      ],
      {
        title: 'PYS emit target',
        placeHolder: current === 'javascript' ? 'Current: JavaScript' : 'Current: Python',
      },
    );
    if (!picked) {
      return;
    }
    await vscode.workspace.getConfiguration('pys').update(
      'emitTarget',
      picked.target,
      vscode.ConfigurationTarget.Workspace,
    );
    refreshEmitTargetUi();
    vscode.window.setStatusBarMessage(`PYS emit target: ${picked.label}`, 2500);
    if (!(await ensureRuntimesForTarget(picked.target))) {
      return;
    }
  }));

  context.subscriptions.push(vscode.commands.registerCommand('pys.debugFile', async (file) => {
    await debugPysFile(resolveTargetPysFile(file));
  }));

  context.subscriptions.push(vscode.commands.registerCommand('pys.debugTranspiledFile', async (file) => {
    await debugPysFile(resolveTargetPysFile(file), 'python');
  }));

  async function setPysOnlyStepping(enabled) {
    const session = vscode.debug.activeDebugSession;
    const entry = activeNormalPysEntry(session);
    if (!entry) {
      vscode.window.showInformationMessage(
        'PYS-only stepping is available during a normal Debug PYS session.',
      );
      return;
    }
    entry.stepFilter.setEnabled(enabled);
    await syncPysStepContexts(session);
    vscode.window.setStatusBarMessage(
      `PYS-only stepping ${enabled ? 'enabled' : 'disabled'}`,
      3000,
    );
  }

  context.subscriptions.push(
    vscode.commands.registerCommand('pys.enablePysOnlyStepping', async () => {
      await setPysOnlyStepping(true);
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('pys.disablePysOnlyStepping', async () => {
      await setPysOnlyStepping(false);
    }),
  );

  context.subscriptions.push(vscode.commands.registerCommand('pys.clearAllBreakpoints', async () => {
    const all = vscode.debug.breakpoints;
    if (!all.length) {
      vscode.window.showInformationMessage('No breakpoints to clear.');
      return;
    }
    const pysBps = all.filter((bp) => {
      if (bp instanceof vscode.SourceBreakpoint) {
        return bp.location.uri.fsPath.toLowerCase().endsWith('.pys');
      }
      return false;
    });
    // Prefer clearing .pys breakpoints; if none, clear all (common IDE “clear all”).
    const toRemove = pysBps.length ? pysBps : all;
    vscode.debug.removeBreakpoints(toRemove);
    vscode.window.setStatusBarMessage(
      `Cleared ${toRemove.length} breakpoint${toRemove.length === 1 ? '' : 's'}`,
      2500,
    );
  }));

  context.subscriptions.push(vscode.commands.registerCommand('pys.addLogpoint', async () => {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document.languageId !== 'pys') {
      vscode.window.showErrorMessage('Open a .pys file to add a logpoint.');
      return;
    }
    const line = editor.selection.active.line;
    const selected = editor.document.getText(editor.selection).trim();
    const prefill =
      selected && /^[A-Za-z_][A-Za-z0-9_]*$/.test(selected) ? `${selected}={${selected}}` : '';
    const message = await vscode.window.showInputBox({
      title: 'PYS Logpoint',
      prompt: 'Message logged to the Debug Console (no pause). Use {name} for values.',
      placeHolder: 'total={total}',
      value: prefill,
      ignoreFocusOut: true,
    });
    if (message === undefined) {
      return;
    }
    if (!String(message).trim()) {
      vscode.window.showErrorMessage('Logpoint message cannot be empty.');
      return;
    }
    const location = new vscode.Location(
      editor.document.uri,
      new vscode.Position(line, 0),
    );
    // SourceBreakpoint with logMessage = non-suspending logpoint (DAP / debugpy).
    const bp = new vscode.SourceBreakpoint(location, true, undefined, undefined, message);
    vscode.debug.addBreakpoints([bp]);
    vscode.window.setStatusBarMessage(`Logpoint on line ${line + 1}`, 2500);
  }));

  context.subscriptions.push(vscode.commands.registerCommand('pys.runMain', async () => {
    const mainPath = resolveMainFilePath();
    if (!mainPath) {
      vscode.window.showErrorMessage('No entrypoint set. Use “PYS: Set as entrypoint” to update pys.toml.');
      return;
    }
    await runPysFile(mainPath);
  }));

  context.subscriptions.push(vscode.commands.registerCommand('pys.debugMain', async () => {
    const mainPath = resolveMainFilePath();
    if (!mainPath) {
      vscode.window.showErrorMessage('No entrypoint set. Use “PYS: Set as entrypoint” to update pys.toml.');
      return;
    }
    await debugPysFile(mainPath);
  }));

  async function setAsEntrypoint(file) {
    let filePath = resolveFilePath(file);
    if (!filePath && vscode.window.activeTextEditor) {
      filePath = vscode.window.activeTextEditor.document.uri.fsPath;
    }
    if (!filePath || !filePath.toLowerCase().endsWith('.pys')) {
      vscode.window.showErrorMessage('Select a .pys file to set as entrypoint.');
      return;
    }
    if (!vscode.workspace.isTrusted) {
      vscode.window.showErrorMessage('Trust this workspace before updating pys.toml.');
      return;
    }
    const workspace = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0];
    if (!workspace) {
      vscode.window.showErrorMessage('Open a workspace folder to set an entrypoint.');
      return;
    }
    filePath = resolveWorkspaceFile(workspace.uri.fsPath, filePath);
    if (!filePath) {
      vscode.window.showErrorMessage('Entrypoint must resolve inside the workspace folder.');
      return;
    }
    const manifestPath = findProjectManifest(filePath, workspace.uri.fsPath)
      || path.join(workspace.uri.fsPath, 'pys.toml');
    const projectRoot = path.dirname(manifestPath);
    let relative;
    try {
      relative = normalizedRelativeMain(projectRoot, filePath);
    } catch (error) {
      vscode.window.showErrorMessage(error.message || String(error));
      return;
    }
    try {
      const current = fs.existsSync(manifestPath)
        ? fs.readFileSync(manifestPath, 'utf8')
        : '';
      fs.writeFileSync(manifestPath, setProjectMain(current, relative), 'utf8');
    } catch (error) {
      vscode.window.showErrorMessage(`Could not update pys.toml: ${error.message || error}`);
      return;
    }
    refreshMainFileUi();
    vscode.window.showInformationMessage(`PYS entrypoint set to ${relative}`);
  }

  context.subscriptions.push(
    vscode.commands.registerCommand('pys.setAsEntrypoint', setAsEntrypoint),
    // Compatibility alias for older keybindings and command URIs.
    vscode.commands.registerCommand('pys.setAsMainFile', setAsEntrypoint),
  );

  /**
   * On activate: offer Python install if missing; if workspace toml/setting
   * targets JavaScript, offer Node too (once per session when dismissed).
   */
  async function maybePromptHostRuntimesOnActivate() {
    if (!vscode.workspace.isTrusted) {
      return;
    }
    await ensureRuntimeKind('python');
    let needsNode = getEmitTarget() === 'javascript';
    if (!needsNode) {
      const folders = vscode.workspace.workspaceFolders || [];
      for (const folder of folders) {
        const tomlPath = path.join(folder.uri.fsPath, 'pys.toml');
        if (!fs.existsSync(tomlPath)) {
          continue;
        }
        try {
          const emit = readProjectTarget(fs.readFileSync(tomlPath, 'utf8')) || 'python';
          if (emit === 'javascript') {
            needsNode = true;
            break;
          }
        } catch (_error) {
          // Invalid target: ignore on activate; Run Project will surface the error.
        }
      }
    }
    if (needsNode) {
      await ensureRuntimeKind('node');
    }
  }

  void maybePromptHostRuntimesOnActivate();

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
