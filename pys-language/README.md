# PYS Language Extension

This folder contains a local VS Code extension for the PYS teaching language.

## What it provides

- `*.pys` file association to the `pys` language
- a TextMate grammar for syntax highlighting
- language configuration for bracket matching and indentation

## How to use it locally

1. Open this workspace in VS Code.
2. Open the `pys-language` folder in the Explorer.
3. Press `F5` to launch an Extension Development Host.
4. Open a `.pys` file in the Extension Development Host window.

Alternatively, package the extension and install it:

```powershell
cd pys-language
npm install -g vsce
vsce package
code --install-extension pys-language-0.0.1.vsix
```

If you do not want to install the extension yet, `.pys` files will still highlight using the Python grammar because the workspace associates them with Python in `.vscode/settings.json`.
