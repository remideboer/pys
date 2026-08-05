# PYS Language Extension

VS Code / Cursor extension for the PYS teaching language. The **transpiler is
bundled** in the VSIX — students do not `pip install` this repo.

## Features

- `*.pys` language association and TextMate syntax highlighting
- Brace-based indentation and `##` … `/#` block comments
- Snippets for functions, classes, loops, results, nullable values, `inherits`, and interpolation
- Keyword / type completions and hover hints
- Go to Definition / **Find Usages** (editor context menu on the identifier under the cursor)
- Language / file icons for `.pys`
- Markdown ` ```pys ` fences: editor + preview highlighting
- **Run** and **Debug** using the bundled transpiler
  - Debug: breakpoints / step / inline values / Variables on `.pys`
  - PYS-only stepping is on by default: native Step Over/Into/Out skip extra
    generated Python lines and stop at the next mapped PYS statement
  - Filter icon in the debug toolbar toggles PYS-only stepping for this session;
    breakpoints, exceptions, and Pause are never skipped
  - **PYS Advanced: Debug Transpiled Python** opens generated `.py` and permits stepping into Python internals
  - Halts at BPs; Clear All Breakpoints in context/gutter/tab; needs Microsoft Python extension
  - `Ctrl+Shift+R` / `Ctrl+Shift+D` — run/debug current `.pys` file
  - `Ctrl+Alt+R` / `Ctrl+Alt+D` — run/debug configured main file
  - `[project].main` in `pys.toml` is authoritative; right-click
    **Set as entrypoint** updates it
  - `pys.mainFile` is a deprecated fallback only when no manifest exists
- `nullable<T>` highlighting, hover, diagnostics, and quick fixes (make nullable /
  surround with null check); debugger Variables show `null` not Python `None`
- `result<T,E>`, `ok` / `err`, `propagate`, and result-pattern highlighting,
  completions, hovers, snippets, diagnostics, and entrypoint conflict fixes
- Libraries: project `pys.deps` → shared `~/.pys/repository` (no venv)
  - Right-click **`pys.deps`** → **PYS: Run Deps** (runs `deps lock` / refreshes `pys.lock`)
- **PYS activity bar** (sidebar icon): **Create PYS Project** — scaffolds a
  runnable `src/main.pys`, `tests/`, `pys.toml` (`[project].main` and
  `[source_roots]`), and a template `pys.deps`

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
