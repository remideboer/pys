# PYS — teaching language that transpiles to Python

> The programming language with eyes 👁👁!

Write `.pys` programs with explicit types and brace blocks; run them through an
on-demand transpile step to standard Python. Designed for classroom use with an
IDE run/debug path and a **didactic tutorial track** (not a keyword tour).

## Design philosophy

PYS is a **bridge language**: typed, brace-shaped source that feels closer to
**C# / Java**, while students still run on the familiar **Python** ecosystem
(stdlib, PyPI via `pys.toml` `[dependencies]`, VS Code / Cursor).

| Principle | What it means in practice |
| --- | --- |
| Make the implicit explicit | Types on bindings, `identity(...)` for entities, `shared` / `atomic` for cross-task mutation, ordered class members |
| Habits that transfer | camelCase, visibility, `const` / `fix`, member order — carry into C#/Java even when those compilers stay silent |
| Prefer language forms over workaround annotations | Needs that belong in the language become keywords/declarations; `@` is for framework edges, not filling holes the grammar never grew |
| Student-friendly project config | Project settings live in [TOML](https://toml.io/en/) (`pys.toml`) — obvious, comment-friendly tables that beginners can read without a JSON/YAML maze |
| Protect cognitive load during programming | Learning to program already imposes high intrinsic load [[1]](#ref-1), [[3]](#ref-3), [[5]](#ref-5). Do not add load via complex interfaces, unfamiliar workflows, or implicit toolchain knowledge that experts no longer notice (expert blind spot [[2]](#ref-2)). Prefer a short, visible edit → run → observe → debug cycle; hide or automate chrome that is not needed for the current task [[4]](#ref-4), [[6]](#ref-6), [[7]](#ref-7). |
| Educational failures | Parse/sem errors name the rule and how to fix it |
| Fail closed at boundaries | Hashed `pys.lock`, no surprise workspace `PYTHONPATH`, Run uses the bundled toolchain |
| Teach with whole tasks | Curriculum under `tutorials/` (4C/ID, faded scaffolding); `examples/` is a dense showcase, not lesson 1 |

Goals in one line: simpler typed syntax → Python, one-click Run/debug, minimal
separate build step for students.

## Important features

Short samples of what students meet early and what makes PYS distinct. Fuller
catalog in [Language examples](#language-examples) below.

### Explicit types and braces

```pys
int count = 0
string label = "ready"
loop (int i = 0; i < 3; i++) {
    print("#i{i}")
}
```

`var` still allows inference from an initializer when the type is obvious.

### Console I/O (`print` and `input`)

No import for keyboard or console — same as Python’s builtins, typed as
`string` for `input`:

```pys
string name = input("What is your name? ")
print("Hello, #s{name}")
```

`input()` with no prompt is allowed. At most one prompt argument.

### Numbers from text (`parseFloat` / `parseInt`)

Recoverable parsing (no silent `0` on bad input):

```pys
string raw = input("Celsius: ")
result<float, string> parsed = parseFloat(raw)
switch (parsed) {
    case ok(celsius): {
        print("F=#f{celsius * 9.0 / 5.0 + 32.0}")
    }
    case error(msg): {
        print(msg)
    }
}
```

### `data`, `entity`, and `struct`

Mainstream stacks leave **identity vs value equality** to frameworks
(`@Id`, `[Key]`, Lombok `@Data` on entities). PYS checks the Evans (2003)
distinction in the language:

| Construct | Equality | Mutability | Typical use |
|-----------|----------|------------|-------------|
| `data` | All fields | Immutable | Value objects (`Money`, `Point`) |
| `entity` | `identity(...)` keys only | Keys `fix`; other fields mutable | Domain rows with a lifecycle |
| `struct` | Field-wise copy | Per-field `fix` optional | Ad-hoc bags (not a VO/Entity contract) |

```pys
data Money {
    string currency
    int cents
}

entity Account identity(iban) {
    private fix string iban
    public int balanceCents

    public constructor(string iban, int balanceCents) {
        this.iban = iban
        this.balanceCents = balanceCents
    }
}
```

Full rationale: [`docs/DATA_ENTITY.md`](docs/DATA_ENTITY.md) ·
[`examples/data.pys`](examples/data.pys) · [`examples/entities.pys`](examples/entities.pys).

### Lambdas capture by value

Python/JS often close over **bindings** (late-binding / shared loop vars).
PYS captures **values at creation**; captures are read-only unless `shared` or
`atomic`:

```pys
int n = 10
lambda<void> greeter = () => {
    print(n)   # sees 10 even if n changes later
}
```

[`examples/lambdas.pys`](examples/lambdas.pys) ·
[`tutorials/jit/J-lambda.md`](tutorials/jit/J-lambda.md).

### `shared` and `atomic`

`shared` is **visibility** across tasks. It does **not** make
`counter = counter + 1` race-free — use `atomic` for indivisible `+=` / CAS:

```pys
atomic int hits = 0
hits += 1
```

[`examples/atomic.pys`](examples/atomic.pys) ·
[`docs/CONCURRENCY.md`](docs/CONCURRENCY.md).

### Enforced member ordering

Experts already put constants → fields → constructors → methods. PYS
**rejects** out-of-order kinds (educational parse error). Visibility stays free
within a section.

| Body | Order |
|------|--------|
| File | Imports first |
| `class` | `const` → `fix` → fields → constructors → methods |
| `struct` | `fix` → mutable |
| `trait` | `requires` → methods |
| `entity` | Identity → other `fix` → mutable → constructors → methods |

Not inside `tasks { }`. Spec:
[`docs/LANGUAGE.md`](docs/LANGUAGE.md#enforced-member-ordering).

### Explicit nullability and results

Plain `T` is non-null; absence is `nullable<T>`. Recoverable errors use
`result<T,E>`, `ok` / `error`, and postfix `propagate` — see
[`examples/results.pys`](examples/results.pys).

## Language examples

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
import math                  # Python stdlib — no [dependencies] entry
import tkinter as tk         # stdlib with alias
# import all from funcs.pys
# import hello from funcs.pys
```

Third-party packages need a `pys.toml` `[dependencies]` entry (full
rules: [Dependency management](#dependency-management-pysdeps)):

```
[interpreter]
	version: >=3.10

[dependencies]
	mysql-connector-python
		version: 8.0.33
		build: run
```

Then lock once — CLI `python -m transpiler deps lock`, or in the IDE
right-click **`pys.toml`** → **PYS: Run Deps Lock** — and import:

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
`pys.toml`), as in `examples/main.pys`:

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
int[] primes = [2, 3, 5]            # length from the initializer

numbers.loop(print)

int[] arr = [1, 2, 3, 4, 5, 6, 7]
print(arr[1:5])                     # end index inclusive
print(arr[1:6:2])               # start:stop:step
```

### Control flow

```pys
loop (int i = 0; i < 3; i++) {
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

    public constructor(T first, U second) {
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


## Learn PYS (students)

Start here: **[`tutorials/00-start-here.md`](tutorials/00-start-here.md)**

The track uses **4C/ID**, **faded scaffolding** (worked → completion → conventional),
and **JIT cards**. Teacher notes: [`tutorials/TEACHER.md`](tutorials/TEACHER.md).

## Getting Started

### Students — install the extension

1. Install **Python 3.10+** and ensure `python` / `python3` is on your PATH.
2. Prefer the Marketplace (auto-update):
   - VS Code **Extensions** → **PYS Language Support**, or `ext install remideboer.pys-language`
3. **ELO / offline:** download `pys-student-<version>.zip` from your course site,
   unzip, run `install.cmd` (Windows) or `./install.sh`, then reload VS Code.
4. Open a folder with `.pys` files and use **PYS: Run File**.

Third-party libraries use **`pys.toml`** (no project venv) — see below. First Run may
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
python -m transpiler run examples/js_smoke.pys --target javascript
```

### Transpile only

```bash
python -m transpiler transpile examples/main.pys .transpiled/main.py
```

### Dependency management (`pys.toml`)

PYS does **not** use a project virtualenv or `requirements.txt`. Third-party
packages for `.pys` programs are declared in the project’s **`pys.toml`**
(`[interpreter]` / `[dependencies]`, and `[dependencies.npm]` for JavaScript).
Resolved Python environments live in a local **content-addressable dependency
cache**: each locked tree is stored once under the SHA-256 digest of `pys.lock`,
and any project with that same lock reuses the tree (no per-project copy).

Default cache root (`PYS_REPO` overrides):

| OS | Location |
| --- | --- |
| Windows | `%USERPROFILE%\.pys\repository` (e.g. `C:\Users\<you>\.pys\repository`) |
| macOS | `~/.pys/repository` (e.g. `/Users/<you>/.pys/repository`) |
| Linux | `~/.pys/repository` (e.g. `/home/<you>/.pys/repository`) |

**How it works**

1. On run/transpile, the tool walks upward from the `.pys` file until it finds
   a `pys.toml` with `[interpreter]` / `[dependencies]` (legacy `pys.deps` still
   loads with a deprecation warning).
2. It checks the optional `[interpreter]` version constraint against the
   Python executable that launched the transpiler.
3. It verifies the committed `pys.lock` matches those pins, Python, and platform.
4. Every direct and transitive package is installed from the exact URL and
   SHA-256 in the lock, using pip `--require-hashes --no-deps`.
5. The locked environment is addressed by lock digest in the cache and
   prepended to `PYTHONPATH` for the generated Python process — imports like
   `import matplotlib` then resolve normally.

**Layout** (content-addressable path under the cache root)

```
environments/
  <lock-sha256>/
    .pys-lock.json
    matplotlib/
    ...
```

Override the cache root with env `PYS_REPO` if needed.

**Declare dependencies**

Put pins in `pys.toml` next to `[project]` / `[source_roots]`:

```toml
[interpreter]
version = ">=3.10"

[dependencies]
matplotlib = { version = "3.10.5" }
"mysql-connector-python" = { version = "8.0.33", build = "run" }

# Optional — JavaScript emit target:
# [dependencies.npm]
# mysql2 = "^3.11.0"
```

| Field | Meaning |
| --- | --- |
| package key | PyPI name; required |
| `version` | Exact version (e.g. `8.0.33`); required for Run dependencies |
| `build` | `run`, `test`, or omit (= available for both) |

`interpreter.path` is intentionally not supported in project-controlled
config. To use another interpreter, invoke the transpiler with that Python:
`C:\Python311\python.exe -m transpiler run main.pys`.

After changing dependencies, regenerate and commit the lock for the current
Python/platform:

```bash
python -m transpiler deps lock
# or: python -m transpiler deps lock pys.toml
```

In VS Code / Cursor, right-click **`pys.toml`** → **PYS: Run Deps Lock** (same
command as the CLI).

Run fails closed if the lock is missing, stale, has the wrong platform/Python,
or contains an invalid hash.

Stdlib modules need no entry. Non-stdlib packages must be listed under
`[dependencies]` before you `import` them from `.pys`.

## VS Code Integration

Install the **PYS Language** extension (bundled transpiler). Use **PYS: Run File** /
editor Run controls — no workspace `.vscode/run_pys.py` required. The activity-bar
**PYS** icon offers **Create PYS Project** (`src` / `tests` + unified `pys.toml`),
including a runnable manifest-selected `src/main.pys`. Create Project asks for
the emit **target** (Python / JavaScript) and prompts to install missing
Python (always) or Node (JavaScript) via the OS package manager when PATH is
empty (trusted workspace only — ADR-001 / CER-051). On activate, the extension
also probes Python (and Node when the workspace target is JavaScript).

- Put the authoritative entrypoint in `pys.toml`, for example
  `[project]` / `main = "src/app.pys"`, or use **PYS: Set as entrypoint**.
  Optional `target = "python"` | `"javascript"` (default python) drives
  **Run Project** (right-click `pys.toml`) and bare `transpiler run` without
  `--target`. Status-bar emit still applies to **Run File**.
  `pys.mainFile` remains only as a deprecated fallback for folders without a
  manifest.
- Recoverable errors use `result<T,E>`, `ok` / `error`, exhaustive result
  switches, and postfix `propagate`. An unhandled entrypoint error becomes a
  non-zero panic; see [`examples/results.pys`](examples/results.pys) and
  [`examples/result_panic/`](examples/result_panic/).
- Explicit absence uses `nullable<T>` (plain `T` is non-null); SQL `NULL` maps to
  PYS `null` without collapsing to `""` / `0`.
- Debug prepares generated Python + line maps, launches debugpy on the program,
  and remaps breakpoints/stack/Variables to `.pys` ([ADR-014](docs/adr/ADR-014-pys-dap-stepping.md)).
  PYS-only stepping is on by default: native Step Over/Into/Out skip extra
  generated Python lines and stop at the next mapped PYS statement. Toggle it
  with the filter icon in the debug toolbar; breakpoints/exceptions/Pause are
  never skipped. **PYS Advanced: Debug Transpiled Python** opens the generated
  `.py` and permits stepping into Python internals.
  Halts at user breakpoints (not top-level entry). **Clear All Breakpoints** on
  context / gutter / tab. Requires the Microsoft Python extension.
  Sample: [`examples/debug_step.pys`](examples/debug_step.pys).
- Third-party imports resolve through `pys.toml` `[dependencies]` /
  `~/.pys/repository` on Run.

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
   [`imports.py`](transpiler/imports.py)), or [`emit/javascript.py`](transpiler/emit/javascript.py)
   for the JavaScript MVP (`--target javascript` → Node; [ADR-030](docs/adr/ADR-030-javascript-emit-target.md)).
   The compile path is AST-only
   ([`docs/pipeline-migration.md`](docs/pipeline-migration.md)).

Public entry points (`transpile`, `run_source`) go through
[`transpiler/pipeline.py`](transpiler/pipeline.py) (`compile_pys(..., target="python"|"javascript")`).

Characterization goldens under `tests/golden/` lock emit parity. Regenerate only
via `python tests/golden/regen.py` (never in CI).

Errors include a line number and a short source preview to help fix syntax quickly.

## VS Code / Cursor workspace files

Tracked under `.vscode/` (everything else there stays gitignored for personal
launch configs, tasks, and local snippets):

- `settings.json` — `*.pys` → PYS language id, exclude `pys-language` from npm
  task detection, and `python.analysis.extraPaths` for editing the transpiler
- `extensions.json` — recommends **PYS Language Support** and the Microsoft
  Python extension

Install the PYS extension for Run/debug, highlighting, and snippets (bundled in
the extension — not workspace snippets). Prefer `pys.toml` `[project].main` over
the deprecated `pys.mainFile` setting.

## Extending the language

1. Add/adjust grammar notes in [`docs/language.ebnf`](docs/language.ebnf).
2. Extend the lexer / parser / AST as needed (`transpiler/lex.py`, `parse.py`,
   `ast_nodes.py`).
3. Emit via `transpiler/emit/python.py` (or `emit/javascript.py` / a future backend under `emit/`).
4. Add a golden under `tests/golden/ebnf/…` and run `python tests/golden/regen.py`.
5. Run `python -m pytest -q`.

## References

<a id="ref-1"></a>[1] J. Sweller, "Cognitive load during problem solving: Effects on learning,"
    Cogn. Sci., vol. 12, no. 2, pp. 257–285, 1988.

<a id="ref-2"></a>[2] M. J. Nathan, K. R. Koedinger, and M. W. Alibali, "Expert blind spot among
    preservice teachers," Amer. Educ. Res. J., vol. 40, no. 4, pp. 905–928, 2003.

<a id="ref-3"></a>[3] S. Garner, "Reducing the cognitive load on novice programmers," in
    Proc. ED-MEDIA 2002, Denver, CO, USA, 2002, pp. 578–583.

<a id="ref-4"></a>[4] R. Mason and G. Cooper, "Mindstorms robots and the application of cognitive
    load theory in introductory programming," Comput. Sci. Educ., vol. 23,
    no. 4, pp. 296–314, 2013, doi: [10.1080/08993408.2013.847152](https://doi.org/10.1080/08993408.2013.847152).

<a id="ref-5"></a>[5] R. Duran, A. Zavgorodniaia, and J. Sorva, "Cognitive load theory in computing
    education research: A review," ACM Trans. Comput. Educ., vol. 22, no. 4,
    2022, Art. no. 40, doi: [10.1145/3483843](https://doi.org/10.1145/3483843).

<a id="ref-6"></a>[6] J. Moons and C. De Backer, "The design and pilot evaluation of an interactive
    learning environment for introductory programming influenced by cognitive
    load theory and constructivism," Comput. Educ., vol. 60, no. 1, pp. 368–384,
    2013, doi: [10.1016/j.compedu.2012.08.009](https://doi.org/10.1016/j.compedu.2012.08.009).

<a id="ref-7"></a>[7] M. Kölling and B. Quig, "The BlueJ system and its pedagogy," Comput. Sci.
    Educ., vol. 13, no. 4, pp. 249–268, 2003, doi: [10.1076/csed.13.4.249.17496](https://doi.org/10.1076/csed.13.4.249.17496).
