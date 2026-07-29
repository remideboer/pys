# PYS Language Extension

Local Cursor / VS Code extension for the PYS teaching language.

## Features

- `*.pys` language association and TextMate syntax highlighting
- Brace-based indentation and `##` … `/#` block comments
- Snippets for functions, classes, loops, `inherits`, and interpolation
- Live diagnostics via the workspace transpiler
- Keyword / type completions and hover hints
- Language / file icons for `.pys` (braces + run triangle)
- Markdown ` ```pys ` fences: editor + preview highlighting (grammar injection)
- Run / Debug editor title controls for `.pys` files (same Run slot as Python/Java)
  - `Ctrl+Shift+R` / `Ctrl+Shift+D` — run/debug current `.pys` file
  - `Ctrl+Alt+R` / `Ctrl+Alt+D` — run/debug configured main file
  - Setting `pys.mainFile` (or right-click **Set as Main File**)
  - Status bar shows the current main entry and runs it on click

## Install into Cursor

```powershell
cd pys-language
npx --yes @vscode/vsce package --allow-missing-repository
cursor --install-extension .\pys-language-0.0.28.vsix --force
```

Then reload the window (`Developer: Reload Window`).

## Develop

1. Open this workspace in Cursor.
2. Open the `pys-language` folder.
3. Press `F5` to launch an Extension Development Host.
4. Open a `.pys` file in the host window.
