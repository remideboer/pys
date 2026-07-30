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
code --install-extension .\pys-language-0.0.29.vsix --force
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

Formal grammar (EBNF): [`docs/language.ebnf`](docs/language.ebnf) · overview
[`docs/LANGUAGE.md`](docs/LANGUAGE.md) · visuals
[`docs/language-railroad.html`](docs/language-railroad.html).

**Curriculum:** [`tutorials/`](tutorials/) — whole-task classes with scaffolding and JIT cards.  
**Showcase:** [`examples/main.pys`](examples/main.pys) (dense reference, not lesson 1).  
**Concurrency:** [`docs/CONCURRENCY.md`](docs/CONCURRENCY.md) · run `examples/concurrency/main.pys`.  
**GUI demo:** `examples/gui/pokemontcg/main.pys`.

Examples below follow the main sections of `examples/main.pys`. Use **4 spaces**
for indentation when not using braces; tabs are illegal.

### Imports

```pys
import funcs                 # sibling .pys module (package/global exports)
import vehicles
import math                  # Python stdlib — no pys.deps entry
import tkinter as tk         # stdlib with alias
# import all from funcs.pys
# import hello from funcs.pys
```

Third-party packages need a `pys.deps` entry (see above). Then:

```pys
import mysql.connector
```

### Python library use (typed returns)

Declare the library return type so PYS stays type-safe. Stdlib example
(`json` / `math` — no extra install):

```pys
import json
import math

dict payload = json.loads("{\"radius\": 3}")
int radius = payload["radius"]
float area = math.pi * radius * radius
print("area=#f{area}")
```

Same pattern with a PyPI package (requires `mysql-connector-python` in
`pys.deps`), as in `examples/main.pys`:

```pys
import mysql.connector

MySQLConnection mydb = mysql.connector.connect(
    host="localhost", user="pys", password="secret", database="demo"
)
MySQLCursor mycursor = mydb.cursor()
mycursor.execute("SELECT id, name FROM items")
list<tuple<int, string>> rows = mycursor.fetchall()
loop (tuple<int, string> row in rows) {
    print("#i{row[0]} #s{row[1]}")
}
mycursor.close()
mydb.close()
```

### Comments

```pys
# single-line comment
## multi-line comment
   spans multiple lines
/#
```

### Variables and types

```pys
int x = 10
float f = 3.14
char letter = 'A'
string greeting = "hello"
bool flag = true
var z = 30                    # type inferred from initializer

const int MAX = 100           # compile-time immutable
fix int fixedSum = x + y     # runtime immutable after init
```

### Explicit casting

```pys
float f = 3.14
int a = (int) f
```

### String interpolation

**Regular** — embed any expression in `{…}`:

```pys
print("a is {a}, f is {f}")
```

**Typed** — type guards (not casts). The expression must match the tag or transpile fails (`#s` string, `#i` int, `#f` float, `#c` char, `#b` bool, `#o` object):

```pys
print("#s{greeting} is a string")
print("#i{x} is an int")
print("#f{f} is a float")
print("#c{letter} is a char")
print("#b{flag} is a bool")
print("the \# symbol is for typed interpolation")   # escape #
print("#i{x} plus {y} equals #i{z}")                # mixed plain + typed
```

### Operators

```pys
print(3.14 + 10 + " is a number")   # + switches numeric / concat
print("sum: " + 3 + 5)
print(true)
print(false)
```

### Arrays

```pys
int[] numbers = [1, 2, 3, 4, 5]
float[] floats = [1.1, 2.2, 3.3]
string[] names = ["John", "Jane", "Jim"]
bool[] flags = [true, false, true]
int[3] primes = [2, 3, 5]           # length must match

numbers.loop(print)

int[] arr = [1, 2, 3, 4, 5, 6, 7]
print(arr[1:5])                     # end index inclusive
print(arr[1:6:2])               # start:stop:step
```

### Control flow

```pys
loop (int i = 0, i < 3, i++) {
    print(i)
}

int counter = 0
loop (counter < 3) {
    print(counter)
    counter++
}

if (x < y) {
    print("x is less than y")
}
else if (x == y) {
    print("x equals y")
}
else {
    print("x is greater than y")
}

unless (x > 100) {
    print("x is not greater than 100")
}
# same as unless
if not (x > 100) {
    print("x is not greater than 100")
}
```

### Functions and visibility

Return type is required when the body returns a value
(`function Type name(...)`).

```pys
global function add(int a, int b) {       # importable from any folder
    print(a + b)
}

package function int multiply(int a, int b) {   # same-folder importers
    return a * b
}

function secret() {                       # this file only
    print("module-private")
}

add(3, 4)
int product = multiply(5, 6)
```

### Classes, interfaces, inheritance

See [`examples/vehicles.pys`](examples/vehicles.pys) and the vehicle section of
`examples/main.pys`:

```pys
Car car = Car("Toyota", "Corolla", 2020)
car.start()
car.move("Alice")

Truck truck = Truck("Ford", "F-150", 2024, 5000)
truck.load(3000)
print(truck.capacity())
```

### Polymorphism

```pys
Drivable d = car
d.start()
d.move()

Vehicle v = truck
v.move()

Flyable flyer = cargo
flyer.takeoff()
flyer.land()
```

### Typed interpolation with objects

```pys
print("#o{car} is an object")
```

### Generics

```pys
class Pair<T, U> {
    private T first
    private U second

    public Pair(T first, U second) {
        this.first = first
        this.second = second
    }

    public T getFirst() {
        return this.first
    }
}

Pair<Car, Truck> pair = Pair<Car, Truck>(car, truck)
pair.getFirst().move()
```

### Concurrency

Not in `main.pys` — see [`docs/CONCURRENCY.md`](docs/CONCURRENCY.md):

```pys
tasks {
    task add(int a, int b) {
        return a + b
    }
    task {
        int s = await add(10, 32)
        print(s)
    }
}
```

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
