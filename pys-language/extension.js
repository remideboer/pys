const vscode = require('vscode');
const cp = require('child_process');
const path = require('path');

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

  context.subscriptions.push(vscode.commands.registerCommand('pys.runFile', (file) => {
    const filePath = resolveFilePath(file);
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
    const term = vscode.window.createTerminal({ name: 'Run PYS' });
    term.show();
    const cmd = `python "${runner}" "${filePath}"`;
    term.sendText(cmd, true);
  }));

  context.subscriptions.push(vscode.commands.registerCommand('pys.debugFile', (file) => {
    const filePath = resolveFilePath(file);
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
