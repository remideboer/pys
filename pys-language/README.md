# PYS Language Extension

Local Cursor / VS Code extension for the PYS teaching language.

## Features

- `*.pys` language association and TextMate syntax highlighting
- Brace-based indentation and `##` … `/#` block comments
- Snippets for functions, classes, loops, `inherits`, and interpolation
- Live diagnostics via the workspace transpiler
- Keyword / type completions and hover hints
- Run / Debug code lenses, editor title buttons, and keybindings
  - `Ctrl+Shift+R` — run current `.pys` file
  - `Ctrl+Shift+D` — debug current `.pys` file

## Install into Cursor

```powershell
cd pys-language
npx --yes @vscode/vsce package --allow-missing-repository
cursor --install-extension .\pys-language-0.0.6.vsix --force
```

Then reload the window (`Developer: Reload Window`).

## Develop

1. Open this workspace in Cursor.
2. Open the `pys-language` folder.
3. Press `F5` to launch an Extension Development Host.
4. Open a `.pys` file in the host window.
