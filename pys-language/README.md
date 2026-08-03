# PYS Language Extension

VS Code / Cursor extension for the PYS teaching language. The **transpiler is
bundled** in the VSIX — students do not `pip install` this repo.

## Features

- `*.pys` language association and TextMate syntax highlighting
- Brace-based indentation and `##` … `/#` block comments
- Snippets for functions, classes, loops, `inherits`, and interpolation
- Keyword / type completions and hover hints
- Go to Definition / **Find Usages** (editor context menu on the identifier under the cursor)
- Language / file icons for `.pys`
- Markdown ` ```pys ` fences: editor + preview highlighting
- **Run** and **Debug** using the bundled transpiler
  - Debug: breakpoints / step / inline values / Variables on `.pys` (halts at BPs; Clear All Breakpoints in context/gutter/tab; needs Microsoft Python extension)
  - `Ctrl+Shift+R` / `Ctrl+Shift+D` — run/debug current `.pys` file
  - `Ctrl+Alt+R` / `Ctrl+Alt+D` — run/debug configured main file
  - Setting `pys.mainFile` (or right-click **Set as Main File**)
- Libraries: project `pys.deps` → shared `~/.pys/repository` (no venv)

## Install (students)

**Marketplace (preferred):** Extensions → **PYS Language Support**  
(`ext install remideboer.pys-language`). Leave auto-update on.

**ELO / offline:** unzip `pys-student-<version>.zip` → `install.cmd` / `install.sh` → reload.

Requires **system Python 3.10+** on PATH. The extension bundles the transpiler.

## Publish (maintainers)

See [`PUBLISH.md`](PUBLISH.md): Marketplace tag publish + ELO zip on the GitHub Release.

## Develop (contributors)

From the repo root:

```powershell
cd pys-language
npm run prepare
npm run package
```

`prepare` copies `../transpiler` into `bundled/transpiler` (gitignored). Then F5
in the extension host, or install the built `.vsix`.

Live diagnostics still resolve `transpiler.ide` via workspace `PYTHONPATH` until
a later phase; **Run always uses the bundled copy**.
