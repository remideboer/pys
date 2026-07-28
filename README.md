# Python Transpiler for Students

This project is a starter transpiler for a simple Python-like teaching language. It lets you write student-friendly code in `.pys` files and run it through an on-demand transpile step to standard Python.

## Goals
- Teach a new, simpler syntax that compiles into Python
- Enable VS Code "Run" / debug configurations via a wrapper
- Minimize the need for a separate build step for students
- Show how to integrate with IDE run/play tools

## Getting Started

### Install
Use your normal Python environment:

```bash
python -m pip install -e .
```

### Run a sample file

```bash
python -m transpiler run examples/hello.pys
```

### Transpile only

```bash
python -m transpiler transpile examples/hello.pys .transpiled/hello.py
```

## VS Code Integration

This repository includes `.vscode/launch.json` and `.vscode/tasks.json`.

- Use the `Run .pys file` debug configuration to execute the active `.pys` file in the debugger.
- The wrapper transpiles the current file and executes the generated Python code.

## Language Features

Supported `.pys` syntax:

- `# comment` → comment
- `let x = 1` → `x = 1`
- `func name(args):` → `def name(args):`
- `if condition then:` → `if condition:`
- `elif condition then:` → `elif condition:`
- `else:` → `else:`
- `for x in range(5) do:` → `for x in range(5):`
- `while x < 5 do:` → `while x < 5:`
- `repeat 3 times:` → `for _ in range(3):`
- `print hello` → `print("hello")`
- `return value` → `return value`
- `pass` → `pass`

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
