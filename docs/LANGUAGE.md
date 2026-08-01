# PYS language documentation

Formal grammar: [`language.ebnf`](language.ebnf) (EBNF).  
Visual railroad diagrams: [`language-railroad.html`](language-railroad.html) (open in a browser).  
Toolchain architecture: [`ARCHITECTURE.md`](ARCHITECTURE.md).

PYS is a typed teaching language that transpiles to Python. Prefer **brace style**
(`{` … `}`), as in `examples/main.pys`. Indentation style and legacy `then:` / `do:`
forms remain for compatibility (see Appendix A in the EBNF).

Statements end at newline — there is no `;`. Identifiers are case-sensitive.
Use **4 spaces** for indentation when not using braces; tabs are illegal.

---

## 1. Program structure (procedural)

A `.pys` file is a sequence of top-level items: imports, declarations, and
statements. Execution runs top to bottom, like a script.

```pys
import math

int n = 3
print(n + 1)
```

### Comments

```pys
# single-line comment
## multi-line comment
   may span several lines
/#
```

### Statements

Typical procedural statements:

| Form | Role |
|------|------|
| Declarations | Bind names (`int x = 1`, `var`, `const`, `fix`, `shared`) |
| Assignment | `x = …`, `x += 1`, `x++` / `x--` |
| Expression statement | Call a function or method |
| `print` / `return` | Output / leave a function |
| `break` / `continue` / `pass` | Loop control / empty body |
| `tasks` / `task` / `await` | Structured concurrency (see §11) |

`print` accepts a bare expression or parentheses:

```pys
print("hello")
print greeting
```

---

## 2. Static typing and declarations

Every value has a type. Prefer an explicit type on the left-hand side; use `var`
only when the initializer makes the type obvious.

### Primitive types

| Type | Literals / notes |
|------|------------------|
| `int` | `10` |
| `float` | `3.14` |
| `char` | `'A'` (single character) |
| `string` | `"hello"` or `'hello'` |
| `bool` | `true` / `false` |
| `null` | null reference (`None` in Python) |

### Declaration forms

```pys
int x = 10
float t = 20.5
string label = "probe-A"
bool ok = true
char grade = 'B'

var inferred = x + 1          # type taken from initializer

const int MAX = 100           # compile-time constant; do not reassign
fix int locked = x + MAX     # assign once from an expression, then locked
```

Rules:

1. Typed name: `type name = expression`
2. `var` — type must be inferable from the initializer
3. `const` — fixed at compile time; no reassignment
4. `fix` — evaluated once, then immutable

Top-level `const` / `fix` may take a visibility prefix (`global`, `package`, `module`):

```pys
global const float PI = 3.14159
```

### Named and collection types

Classes, interfaces, and library types are named types. Collections use angle
brackets for element types:

```pys
list<int> scores = [1, 2, 3]
dict<string, int> ages = {}
tuple<int, string, string> row = (1, "a", "b")
set<string> tags = {"a", "b"}
```

`list`, `dict`, `tuple`, and `set` map to the Python counterparts.

### Casts

Explicit casts use `(type) expression`:

```pys
float f = 3.14
int a = (int) f
```

---

## 3. Arrays

Fixed-element arrays of primitives (and `string`) use `T[]` / `T[n]` syntax.
They are meant as a teaching form for contiguous sequences (backed by
`array.array` for numeric/bool primitives, and lists for strings).

```pys
int[] numbers = [1, 2, 3, 4, 5]
float[] floats = [1.1, 2.2, 3.3]
string[] names = ["John", "Jane", "Jim"]
bool[] flags = [true, false, true]

int[3] primes = [2, 3, 5]     # sized: length must match exactly
```

### Indexing and slicing

Index with `[i]`. Slices use `start:end` with an **inclusive** end index
(adjusted when transpiling to Python). An optional step is allowed:

```pys
int[] arr = [1, 2, 3, 4, 5, 6, 7]
print(arr[1:5])
print(arr[3:])
print(arr[:3])
print(arr[1:6:2])
```

### Functional iteration

```pys
numbers.loop(print)           # → list(map(print, numbers))
```

Prefer `list<T>` / `tuple<…>` when working with library return values (e.g. DB
rows). Prefer `T[]` when teaching array ideas.

---

## 4. Control flow

Blocks use braces. Conditions go in parentheses.

### `if` / `else if` / `else`

```pys
if (x < y) {
    print("x is less than y")
}
else if (x == y) {
    print("x equals y")
}
else {
    print("x is greater than y")
}
```

### `unless` / `if not`

Negated `if`. Both forms transpile to `if not (…)`:

```pys
unless (x > 100) {
    print("x is not greater than 100")
}
# same as unless
if not (x > 100) {
    print("x is not greater than 100")
}
```

`else if not (…)` is also valid (transpiles to `elif not (…)`).

### `loop` — three shapes

**C-style for** (init, condition, step share one loop variable; that variable
is immutable inside the body):

```pys
loop (int i = 0, i < 3, i++) {
    print(i)
}
```

**While** (single condition):

```pys
int counter = 0
loop (counter < 3) {
    print(counter)
    counter++
}
```

**Foreach**:

```pys
loop (tuple<string, string> row in rows) {
    print(row)
}
```

`break` and `continue` work inside loops.

---

## 5. Functions

```pys
global function add(int a, int b) {
    print(a + b)
}

package function int multiply(int a, int b) {
    return a * b
}

function secret() {
    print("only this file can call me")
}
```

Rules:

1. Prefer `function`; short form `func` also exists
2. **Return type is required** when the body returns a value. Place it after
   `function` and before the name: `global function AppStore openStore()` /
   `package function int multiply(…)`
3. Parameters may be typed: `int a`
4. Visibility on the function controls who may import it (see §7)
5. Void functions (no value returned) may omit the return type

Inside a **class**, do not write `function` / `func` — methods use member access
modifiers instead (`public name(…) { … }`).

---

## 6. Classes and interfaces

### Interfaces

No fields, no bodies — only `public` method signatures. Implementing classes
must provide matching methods.

```pys
package interface Drivable {
    public start()
    public move()
    public stop()
}
```

### Classes

```pys
package class Cart implements Drivable {
    private string id

    public Cart(string id) {
        this.id = id
    }

    public start() {
        print("cart #s{this.id}")
    }
}

package class BigCart inherits Cart {
    public BigCart(string id) {
        super(id)
    }
}
```

Rules:

1. Members need an access modifier: `public` / `private` / `protected` / `module`
2. Constructor name equals the class name
3. One superclass via `inherits` (alias `super` in the header); one or more
   interfaces via `implements`
4. `this` / `super` for current instance / parent. Subclass constructors that
   omit `super(...)` / `this(...)` get an implicit zero-arg `super()` at the
   start — write `super(args)` when the parent constructor needs arguments.
5. `sealed` may mark a class that should not be subclassed further
6. Optional type parameters: `class Pair<T, U> { … }`

### Polymorphism

Declare the static type; the runtime value may be a subtype:

```pys
Drivable d = car
d.start()
```

### Generics (brief)

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
```

Type arguments are available when constructing (`Pair<Car, Truck>(…)`).

---

## 7. Visibility and modules

### Top-level exports (`global` / `package` / `module`)

| Keyword | Who can import it |
|---------|-------------------|
| (default / omit) | Nobody outside this file (module-private) |
| `package` | Other `.pys` files in the same folder |
| `global` | Any importer |
| `module` | Explicit module scope (same file family) |

Applies to functions, classes, interfaces, and top-level `const` / `fix`.

### Member access (inside classes)

| Keyword | Intent |
|---------|--------|
| `public` | Usable from outside the class |
| `private` | Only this class |
| `protected` | This class and subclasses |
| `module` | Same module / teaching module boundary |

---

## 8. Imports

```pys
import vehicles                 # whole .pys module (same folder / discovery)
import greet from toolbox       # one name
import QApplication, QWidget from PyQt6.QtWidgets   # several names
import all from toolbox         # all package/global exports
import math                     # Python stdlib
import tkinter as tk            # stdlib / pys.deps package with alias
import mysql.connector          # package from pys.deps
```

- Local `.pys` modules: file / folder discovery; only `package` / `global`
  names are importable.
- Python packages: stdlib or entries in `pys.deps` (see README). Alias `as` is
  for those packages.

---

## 9. Operators and expressions

### Arithmetic and comparison

`+` `-` `*` `/` `%`  
`<` `<=` `>` `>=` `==` `!=` `<>`  

`+` also concatenates when a string is involved (numeric parts are coerced).

### Logical

`&&` / `and`, `||` / `or`, `!` / `not`

### Assignment and updates

`=` `+=` `-=` `*=` `/=` `%=`  
postfix / statement forms `++` and `--`

### Calls and members

```pys
obj.method(arg)
TypeName(args)                  # constructor
super(args)                     # parent __init__
this(args)                      # constructor chaining
```

---

## 10. Strings and interpolation

Plain interpolation embeds an expression in `{…}`:

```pys
print("a is {a}, f is {f}")
```

**Typed interpolation** is a type guard (not a cast). The expression must match
the tag or the transpile fails:

| Form | Required type |
|------|----------------|
| `#s{…}` | `string` |
| `#i{…}` | `int` |
| `#f{…}` | `float` |
| `#c{…}` | `char` |
| `#b{…}` | `bool` |
| `#o{…}` | non-primitive object |

```pys
print("#i{x} is an int")
print("#s{greeting} is a string")
print("#o{car} is an object")
print("the \# symbol is for typed interpolation")
```

Tuple / list indexes keep their element types, so `#s{row[0]}` fails if
`row[0]` is `int`.

---

## 11. Concurrency (`tasks` / `task` / `await` / `shared`)

**Full guide with examples:** [`CONCURRENCY.md`](CONCURRENCY.md)

One concurrent unit, structured lifetime, explicit shared mutation. Tasks in the
same process **share memory**; a `tasks` block joins children — it does not
isolate memory.

| Keyword | Meaning |
|---------|---------|
| `task { … }` | One concurrent unit (must be inside `tasks`) |
| `tasks { … }` | Group; leaving the block waits for all |
| `await expr` | Wait until ready (only inside a `task`) |
| `shared` | Outer name may be mutated across tasks |

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

Outer locals are **read-only** inside a task unless declared `shared`.  
Prefer **parameters** for inputs. Await edges in a group must form a **DAG** —
cycles are **rejected** (`pys.await-cycle`). Runnable suite: `examples/concurrency/main.pys`.

---

## 12. Quick example (dense)

```pys
import vehicles
import mysql.connector
import tkinter as tk

global const float PI = 3.14159

int x = 10
var z = x + 1
fix int locked = x + z

list<tuple<string, string>> rows = mycursor.fetchall()
loop (tuple<string, string> row in rows) {
    print(row)
}

package class Car inherits Vehicle implements Drivable {
    private string color
    public Car(string make, string model, int year, string color) {
        super(make, model, year)
        this.color = color
    }
    public start() {
        print("vroom")
    }
}
```

For a full walkthrough, see `examples/main.pys` and `examples/vehicles.pys`.

---

## Related project files

| File | Role |
|------|------|
| `docs/language.ebnf` | Formal EBNF (includes concurrency) |
| `docs/language-railroad.html` | Railroad diagram visuals |
| `docs/CONCURRENCY.md` | `tasks` / `task` / `await` / `shared` guide |
| `tutorials/` | Distributable learning track (4C/ID, JIT, scaffolding) |
| `examples/main.pys` | Dense feature showcase (not the curriculum path) |
| `examples/concurrency/` | Concurrency showcase package |
| `transpiler/language_spec.py` | Line translation rules |
| `pys.deps` | External Python dependencies (not language syntax) |
