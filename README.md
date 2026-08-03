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

## Why `data` and `entity`?

Mainstream languages leave **identity vs value equality** to frameworks
(Hibernate `@Id`, EF Core `[Key]`, ActiveRecord). That produces a well-known
class of defects: mutable keys in `hashCode`, hand-written `equals` that widen
or NPE, Lombok `@Data` applied to entities. PYS makes the Evans (2003)
distinction first-class and compiler-checked:

| Construct | Equality | Mutability | Typical use |
|-----------|----------|------------|-------------|
| `data` | All fields (structural) | Immutable | Value objects (`Money`, `Point`) |
| `entity` | `identity(...)` keys only | Keys `fix`; other fields mutable | Domain rows with a lifecycle |
| `struct` | Field-wise, not a VO/Entity contract | Per-field `fix` optional | Ad-hoc bags without identity semantics |

Full rationale (Java/C#/Hibernate counterexamples + sources):
[`docs/DATA_ENTITY.md`](docs/DATA_ENTITY.md). Samples:
[`examples/data.pys`](examples/data.pys), [`examples/entities.pys`](examples/entities.pys).

## Why lambdas capture by value

Python and older JS close over **bindings** (late-binding / shared loop vars).
PYS lambdas capture **values at creation**; captured names are read-only unless
`shared` or `atomic` (same visibility rule as `tasks`). Sample:
[`examples/lambdas.pys`](examples/lambdas.pys). JIT: [`tutorials/jit/J-lambda.md`](tutorials/jit/J-lambda.md).

## Why `atomic` exists next to `shared`

`shared` declares cross-task mutation (visibility). It does **not** make
`counter = counter + 1` race-free. Use `atomic` for indivisible `+=` / CAS.
Sample: [`examples/atomic.pys`](examples/atomic.pys). Guide:
[`docs/CONCURRENCY.md`](docs/CONCURRENCY.md). JIT: [`tutorials/jit/J-atomic.md`](tutorials/jit/J-atomic.md).

## Getting Started

### Students — install the extension

1. Install **Python 3.10+** and ensure `python` / `python3` is on your PATH.
2. Prefer the Marketplace (auto-update):
   - VS Code **Extensions** → **PYS Language Support**, or `ext install remideboer.pys-language`
3. **ELO / offline:** download `pys-student-<version>.zip` from your course site,
   unzip, run `install.cmd` (Windows) or `./install.sh`, then reload VS Code.
4. Open a folder with `.pys` files and use **PYS: Run File**.

Third-party libraries use **`pys.deps`** (no project venv) — see below. First Run may
download packages into `~/.pys/repository`.

Maintainers: [`pys-language/PUBLISH.md`](pys-language/PUBLISH.md) (Marketplace + ELO zip).

### Contributors — develop the language / extension

```bash
python -m pip install -e .
./install-extension.bat          # Windows: package + install latest VSIX
./install-extension.sh           # macOS/Linux
# or: pys install extension
#     python -m transpiler install extension
#     ./install-extension.bat --no-build
#     ./install-extension.bat --editor cursor
```

```bash
cd pys-language
npm run prepare          # copies transpiler into bundled/
npm run package          # builds pys-language-*.vsix (also done by install-extension)
```

F5 from `pys-language` after `npm run prepare`. Diagnostics still use a workspace
`PYTHONPATH` / editable install until a later phase.

### Run a tutorial or sample (CLI)

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
2. It checks the optional `[interpreter]` version constraint against the
   Python executable that launched the transpiler.
3. It verifies the committed `pys.lock` matches `pys.deps`, Python, and platform.
4. Every direct and transitive package is installed from the exact URL and
   SHA-256 in the lock, using pip `--require-hashes --no-deps`.
5. The locked environment is cached once by lock digest and prepended to `PYTHONPATH` for the generated
   Python process — imports like `import matplotlib` then resolve normally.

**Layout**

```
~/.pys/repository/
  environments/
    <lock-sha256>/
      .pys-lock.json
      matplotlib/
      ...
```

Override the repo root with env `PYS_REPO` if needed.

**Declare dependencies**

Place `pys.deps` in the project root (or any parent of the `.pys` file):

```
[interpreter]
	version: >=3.10

[dependencies]
	matplotlib
		version: 3.10.5
	mysql-connector-python
		version: 8.0.33
		build: run
```

| Field | Meaning |
| --- | --- |
| package name (indented line) | PyPI name; required |
| `version` | Exact version (e.g. `8.0.33`); required for Run dependencies |
| `build` | `run`, `test`, or omit (= available for both) |

`interpreter.path` is intentionally not supported in project-controlled
`pys.deps`. To use another interpreter, invoke the transpiler with that Python:
`C:\Python311\python.exe -m transpiler run main.pys`.

After changing dependencies, regenerate and commit the lock for the current
Python/platform:

```bash
python -m transpiler deps lock pys.deps
```

Run fails closed if the lock is missing, stale, has the wrong platform/Python,
or contains an invalid hash.

Stdlib modules need no entry. Non-stdlib packages must be listed in `pys.deps`
before you `import` them from `.pys`.

## VS Code Integration

Install the **PYS Language** extension (bundled transpiler). Use **PYS: Run File** /
editor Run controls — no workspace `.vscode/run_pys.py` required.

- Set `pys.mainFile` (e.g. `examples/main.pys`) for Run Main.
- Debug prepares generated Python + line maps, launches debugpy on the program,
  and remaps breakpoints/stack/Variables to `.pys` ([ADR-014](docs/adr/ADR-014-pys-dap-stepping.md)).
  Halts at user breakpoints (not top-level entry). **Clear All Breakpoints** on
  context / gutter / tab. Requires the Microsoft Python extension.
  Sample: [`examples/debug_step.pys`](examples/debug_step.pys).
- Third-party imports resolve through `pys.deps` / `~/.pys/repository` on Run.

## Language Features

Formal grammar (EBNF): [`docs/language.ebnf`](docs/language.ebnf) · overview
[`docs/LANGUAGE.md`](docs/LANGUAGE.md) · visuals
[`docs/language-railroad.html`](docs/language-railroad.html) · architecture
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · code evolution
[`docs/evolution/`](docs/evolution/README.md) · ADRs
[`docs/adr/`](docs/adr/README.md).

**Curriculum:** [`tutorials/`](tutorials/) — whole-task classes with scaffolding and JIT cards.  
**Showcase:** [`examples/main.pys`](examples/main.pys) (dense reference, not lesson 1).  
**Concurrency:** [`docs/CONCURRENCY.md`](docs/CONCURRENCY.md) · run `examples/concurrency/main.pys`.  
**GUI demo:** `examples/gui/pokemontcg/main.pys`.

Examples below follow the main sections of `examples/main.pys`. Use **4 spaces**
for indentation when not using braces; tabs are illegal.

### Imports

```pys
import funcs                 # sibling .pys module (package/global exports)
import interfaces
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

See [`examples/classes.pys`](examples/classes.pys),
[`examples/interfaces.pys`](examples/interfaces.pys), and the vehicle section of
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

Full diagrams (architecture + process flow): **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)**.

The compiler pipeline is:

1. **Lex** — [`transpiler/lex.py`](transpiler/lex.py) turns source into tokens with spans.
2. **Parse** — [`transpiler/parse.py`](transpiler/parse.py) builds a target-neutral AST
   ([`ast_nodes.py`](transpiler/ast_nodes.py)).
3. **Sem** — [`transpiler/sem.py`](transpiler/sem.py) validates the AST (bindings, access,
   interfaces, shared capture, arrays, await rules, …).
4. **Emit** — [`transpiler/emit/python.py`](transpiler/emit/python.py) walks the AST to
   Python (overloads, concurrency preamble, `.pys` imports via
   [`imports.py`](transpiler/imports.py)). The compile path is AST-only
   ([`docs/pipeline-migration.md`](docs/pipeline-migration.md)).

Public entry points (`transpile`, `run_source`) go through
[`transpiler/pipeline.py`](transpiler/pipeline.py) (`compile_pys(..., target="python")`).

Characterization goldens under `tests/golden/` lock emit parity. Regenerate only
via `python tests/golden/regen.py` (never in CI).

Errors include a line number and a short source preview to help fix syntax quickly.

## VS Code support

This project includes `.vscode/settings.json` and `.vscode/pys.code-snippets` to make `.pys` files feel like a first-class editing experience:

- `.vscode/settings.json` associates `*.pys` with Python syntax highlighting.
- `.vscode/pys.code-snippets` provides quick templates for `let`, `func`, `if`, `repeat`, and `print`.

## Extending the language

1. Add/adjust grammar notes in [`docs/language.ebnf`](docs/language.ebnf).
2. Extend the lexer / parser / AST as needed (`transpiler/lex.py`, `parse.py`,
   `ast_nodes.py`).
3. Emit via `transpiler/emit/python.py` (or a future backend under `emit/`).
4. Add a golden under `tests/golden/ebnf/…` and run `python tests/golden/regen.py`.
5. Run `python -m pytest -q`.
