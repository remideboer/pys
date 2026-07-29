# PYS — teaching language that transpiles to Python

Write `.pys` programs with explicit types and brace blocks; run them through an
on-demand transpile step to standard Python. Designed for classroom use with an
IDE run/debug path and a **didactic tutorial track** (not a keyword tour).

## Learn PYS (students)

Start here: **[`tutorials/00-start-here.md`](tutorials/00-start-here.md)**

The track uses **4C/ID**, **faded scaffolding** (worked → completion → conventional),
and **JIT cards**. Teacher notes: [`tutorials/TEACHER.md`](tutorials/TEACHER.md).

## Goals
- Teach a simpler typed syntax that compiles into Python
- Enable VS Code / Cursor “Run” / debug via the PYS extension and wrappers
- Minimize a separate build step for students
- Ship a curriculum path separate from the dense `examples/` showcase

## Getting Started

### Install
Use a normal system (or user) Python — **no project venv**:

```bash
python -m pip install -e .
```

### PYS extension (editor)

```powershell
cd pys-language
npx --yes @vscode/vsce package --allow-missing-repository
cursor --install-extension .\pys-language-0.0.25.vsix --force
```

Then reload the window. Set `pys.mainFile` (e.g. `examples/main.pys`) for Run Main.

### Run a tutorial or sample

```bash
python -m transpiler run tutorials/tasks/T1-sensor-log/1-worked.pys
python -m transpiler run examples/main.pys
```

### Transpile only

```bash
python -m transpiler transpile examples/main.pys .transpiled/main.py
```

### Dependency management (`pys.deps`)

PYS does **not** use a project virtualenv or `requirements.txt`. Third-party
packages for `.pys` programs are declared in a `pys.deps` file and resolved
through a **Maven-style central repository** shared across projects.

**How it works**

1. On run/transpile, the tool walks upward from the `.pys` file until it finds
   `pys.deps`.
2. It checks the optional `[interpreter]` constraint (and optional `path`).
3. For each entry under `[dependencies]`, it looks in the central repo:
   `~/.pys/repository/packages/<name>/<version>/`.
4. Missing packages are installed once with `pip install --target` into that
   folder (flyweight cache). Later projects reuse the same install.
5. Those package folders are prepended to `PYTHONPATH` for the generated
   Python process — imports like `import matplotlib` then resolve normally.

**Layout**

```
~/.pys/repository/
  packages/
    matplotlib/
      3.8.0/          # pinned or resolved "latest"
      LATEST          # pointer file when version was omitted
    mysql_connector_python/
      8.0.33/
```

Override the repo root with env `PYS_REPO` if needed.

**Declare dependencies**

Place `pys.deps` in the project root (or any parent of the `.pys` file):

```
[interpreter]
	version: >=3.10
	# path: C:\Python311\python.exe

[dependencies]
	matplotlib
	mysql-connector-python
		version: 8.0.33
		build: run
```

| Field | Meaning |
| --- | --- |
| package name (indented line) | PyPI name; required |
| `version` | Pin (e.g. `8.0.33`). Omit = resolve once as latest and cache |
| `build` | `run`, `test`, or omit (= available for both) |

Stdlib modules need no entry. Non-stdlib packages must be listed in `pys.deps`
before you `import` them from `.pys`.

## VS Code Integration

This repository includes `.vscode/launch.json` and `.vscode/tasks.json`.

- Use the `Run .pys file` debug configuration to execute the active `.pys` file in the debugger.
- The wrapper transpiles the current file and executes the generated Python code.

## Language Features

Formal grammar (EBNF): [`docs/language.ebnf`](docs/language.ebnf) - overview in [`docs/LANGUAGE.md`](docs/LANGUAGE.md), visuals in [`docs/language-railroad.html`](docs/language-railroad.html).

**Curriculum:** [`tutorials/`](tutorials/) — whole-task classes with scaffolding and JIT cards.  
**Showcase:** `examples/main.pys` (dense reference, not lesson 1).  
**Concurrency:** `examples/concurrency/main.pys` (`tasks` / `task` / `await` / `shared`).

Supported `.pys` syntax (see also `examples/main.pys`):

- `# comment` / `## ... /#` block comments
- Typed declarations: `int x = 1`, `var z = 1`, `const` / `fix`
- `function` / `func`, classes, interfaces, `sealed`, `inherits`, `implements`
- `if` / `else if` / `else`, `unless`, `loop` (C-for, while, foreach)
- `print`, string interpolation `{x}` and typed `#i{x}` / `#s{...}` / ...
- Imports: `import mod`, `import name from mod.pys`, external packages via `pys.deps`
- Concurrency: `tasks` / `task` / `await` / `shared` (structured group; see `docs/LANGUAGE.md`)

### Indentation rules

- Use 4 spaces per indentation level.
- Tabs are not supported.
- Blank lines are preserved.

## How this transpiler works

This version is parser-based, not regex-based.

The transpiler parses `.pys` source line-by-line, converts teaching-language constructs into Python source, validates the generated Python with the AST parser, and then executes it with the current Python interpreter.

The pipeline is:
1. Read the `.pys` source file.
2. Parse each line and rewrite teaching constructs to Python.
3. Track indentation blocks using 4-space indent levels.
4. Validate the generated Python with the AST parser.
5. Run the generated code.

Errors include a line number and a short source preview to help students fix syntax quickly.

## VS Code support

This project includes `.vscode/settings.json` and `.vscode/pys.code-snippets` to make `.pys` files feel like a first-class editing experience:

- `.vscode/settings.json` associates `*.pys` with Python syntax highlighting.
- `.vscode/pys.code-snippets` provides quick templates for `let`, `func`, `if`, `repeat`, and `print`.

## Extending the language

To add a new syntax construct:

1. Open `transpiler/transpiler.py`.
2. Add a new branch in the `Parser._parse_line()` method.
3. Add a regression test in `tests/`.
4. Run `python -m pytest -q`.

### Example: add `repeat` syntax

In `transpiler/transpiler.py`, the parser already supports `repeat N times:` and rewrites it as:

```python
for _ in range(N):
    ...
```

Then a source block like:

```pys
repeat 3 times:
    print hello
```

produces:

```python
for _ in range(3):
    print("hello")
```
