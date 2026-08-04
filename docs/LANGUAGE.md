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

A `.pys` file is a sequence of top-level items. **All imports must appear
first** (blank lines and comments may sit among them). After the first
declaration or statement, a later `import` / `from … import` is a parse
error — not a style warning. See [Enforced member ordering](#enforced-member-ordering).

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
| Declarations | Bind names (`int x = 1`, `var`, `const`, `fix`, `shared`, `atomic`) |
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
| `int` | `10`, `0b1010`, `0xFF` (optional `_` separators) |
| `byte` | unsigned 8-bit alias of `int` (0..255) |
| `nibble` | unsigned 4-bit alias of `int` (0..15) |
| `int16` | unsigned 16-bit alias of `int` (0..65535) |
| `int32` / `dword` | unsigned 32-bit alias of `int` |
| `int64` | unsigned 64-bit alias of `int` |
| `float` | `3.14` |
| `char` | `'A'` (single character) |
| `string` | `"hello"` or `'hello'` |
| `bool` | `true` / `false` |
| `null` | null reference (`None` in Python) |

Width aliases emit as Python `int`. Out-of-range literal assigns are rejected.

```pys
int i = 0b1010
byte b = 0b1011_1101
nibble n = 0xA
print(i & 0b0101)
print(i xor 0b0101)
print(i shift left 1)
```

Bitwise operators: `& | ^ ~ << >>`, plus word forms `xor` and `shift left` /
`shift right`. Logical `and` / `or` / `not` stay short-circuit boolean (not
bitwise). Rotate (`<<<` / `>>>`) is deferred.

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
dict<string, int> known = {"Ada": 36, "Tom": 41}
tuple<int, string, string> row = (1, "a", "b")
tuple<int> one = (42,)
set<string> tags = {"a", "b"}
set<string> emptyTags = {}
```

`list`, `dict`, `tuple`, and `set` map to the Python counterparts.

**Brace dual-use:** unkeyed `{…}` and empty `{}` are resolved from the
**expected type** of the binding (or `T[]` array context):

| Expected type | `{}` / `{a, b}` |
| --- | --- |
| `dict<…>` | empty dict / must use `key: value` pairs |
| `set<…>` | empty `set()` / set elements |
| `list<…>` | empty list / list elements (braces allowed like `[…]`) |
| `T[]` / nested array init | Java-style array initializer (CER-019) |

Untyped `var x = {}` is an error — type the binding. Struct/data field brace
literals are **not** supported (use constructors).

### Casts

Explicit casts use `(type) expression`:

```pys
float f = 3.14
int a = (int) f
```

---

## 3. Arrays

Fixed-element arrays of primitives (and `string`) use unsized `T[]` / `T[][]`…
syntax. Length comes from the initializer (or from a right-hand-side allocation
like `int[2][3]`). A sized type on the **declaration** (`int[3] xs = …`) is
invalid. Innermost numeric/bool storage is `array.array` (Python lists only for
`string` and for outer ranks that hold nested arrays). Prefer `list<T>` when
you need library-shaped collections rather than array teaching.

```pys
int[] numbers = [1, 2, 3, 4, 5]
float[] floats = [1.1, 2.2, 3.3]
string[] names = ["John", "Jane", "Jim"]
bool[] flags = [true, false, true]

int[] primes = [2, 3, 5]     # length 3 from the initializer

# Multi-dimensional: nested [] or {} initializers (Java-style braces OK)
int[][] myNumbers = { {1, 4, 2}, {3, 6, 8} }
int[][] grid = [[1, 2], [3, 4]]

# Allocate ranks (like Java `new int[3][][]` / `new int[2][3]`, without `new`)
int[][][] arr = int[3][][]
int[][] zeros = int[2][3]
print(myNumbers[0][1])
```

### Indexing and slicing

Index with `[i]` (chain for higher ranks: `a[i][j]`). Slices use `start:end`
with an **inclusive** end index (adjusted when transpiling to Python). An
optional step is allowed:

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

Nested ranks use nested `loop` (typed array binders allowed):

```pys
loop (int[] row in myNumbers) {
    loop (int cell in row) {
        print(cell)
    }
}
```

Prefer `list<T>` / `tuple<…>` when working with library return values (e.g. DB
rows). Prefer `T[]` / `T[][]` when teaching array ideas.

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

### `switch` — statement and expression

Multi-way branch on an enum or equality-comparable primitive (`int` / width
aliases, `string`, `char`, `bool`, `float`). **No implicit fall-through.**

**Statement** — `case LABEL:` then statements. A trailing bare `continue` falls
through to the next case (nested-loop `continue` keeps loop meaning). `break`
is not required. Bare enum labels (`MONDAY`) resolve from the subject type
(also `Day.MONDAY`). Non-exhaustive enum/primitive switches without `default`
emit a **warning**.

```pys
switch (day) {
    case MONDAY:
        continue
    case FRIDAY:
        continue
    case SUNDAY:
        numLetters = 6
    case WEDNESDAY:
        numLetters = 9
    default:
        numLetters = 0
}
```

**Expression** — assignable RHS; arms use `=>`. Multi-label with commas.
Every path must yield the same type. Exhaustiveness is **required**: cover all
enum members or provide `default` (non-enum subjects always need `default`).

```pys
numLetters = switch (day) {
    case MONDAY, SUNDAY, FRIDAY => 6
    case WEDNESDAY => 9
    default => 0
}
```

Do not mix `:` and `=>` in one switch. See example `examples/switch.pys`.

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

Loop binders and any variables declared inside `{ … }` are **block-scoped**:
they do not exist after the closing brace. A later `int row = 0` is a new
binding (Python emit mangles the inner name so it cannot leak).

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
5. Void functions (no value returned) may omit the return type, or write `void`
   explicitly. A `void` body must not `return expr`.

Inside a **class**, do not write `function` / `func` — methods use member access
modifiers instead (`public name(…) { … }` or `public void name(…) { … }`).

---

## 6. Classes, interfaces, and traits

### Interfaces

No fields, no bodies — only method signatures. Interface methods are always
public and abstract, so **omit** access modifiers on the signatures. Implementing
classes must provide matching **public** methods.

```pys
package interface Drivable {
    start()
    move()
    stop()
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
2. **Member kind order** (parse-enforced): `const` fields → `fix` fields →
   mutable fields → constructors → methods (including `abstract` methods).
   Visibility is unordered within a section. See
   [Enforced member ordering](#enforced-member-ordering).
3. Constructor name equals the class name
4. One superclass via `inherits` (alias `super` in the header); zero or more
   traits via `uses`; one or more interfaces via `implements`
5. Header order: `inherits` → `uses` → `implements`
6. `this` / `super` for current instance / parent. Subclass constructors that
   omit `super(...)` / `this(...)` get an implicit zero-arg `super()` at the
   start — write `super(args)` when the parent constructor needs arguments.
   Subclasses may call public members of a **library** parent (for example
   `inherits QMainWindow` → `this.setWindowTitle(...)`) when that parent was
   imported via `pys.deps` / the standard library.
7. `sealed` may mark a class that should not be subclassed further
8. `abstract` marks a class that cannot be instantiated and may declare
   body-less `abstract` methods; mutually exclusive with `sealed`
9. Optional type parameters: `class Pair<T, U> { … }`
10. See `examples/classes.pys` for fields, constructors, `inherits`, and `sealed`

### Abstract classes

An **abstract class** is a nominal type with shared fields/concrete methods plus
variation points declared as `abstract` methods (no `{ … }` body). Subclasses
must implement every inherited abstract method. Direct construction
(`AbstractName(...)`) is rejected; constructors may still run via `super(...)`.

```pys
abstract class AbstractList {
    protected int size

    public AbstractList() {
        this.size = 0
    }

    public bool isEmpty() {
        return this.size == 0
    }

    public abstract string get(int index)
    public abstract void add(string item)
}

class ArrayListPys inherits AbstractList {
    public ArrayListPys() { super() }
    public string get(int index) { return "" }
    public void add(string item) { this.size = this.size + 1 }
}
```

Rules:

1. Abstract methods only inside `abstract class`; need access + `abstract` + return type
2. `void` means no value: do not `return expr` (bare `return` is fine)
3. Abstract classes **are** types (unlike traits) — usable for bindings / polymorphism
4. See `examples/abstract_classes.pys` and JIT [J-abstract](../tutorials/jit/J-abstract.md)

### Traits

A **trait** is reusable behavior composed onto a class with `uses`. It is **not**
a nominal type (cannot appear in `implements`, as a variable type, or as
`Trait()`). Methods are always public; host state is declared with `requires`
and accessed via `this`.

```pys
trait Printable {
    requires string name

    string label() {
        return "Item: " + this.name
    }
}

class Product uses Printable {
    private string name

    public Product(string name) {
        this.name = name
    }
}
```

Rules:

1. Every `this.x` in a trait method must be listed in that trait's `requires`
   (or be another method of the same trait)
2. **Body order** (parse-enforced): all `requires` before any method
3. The host class (or an ancestor) must supply each `requires` field/method
4. If two used traits define the same method name, the class must override it;
   call `TraitName.method(this)` from the override to pick a side
5. See `examples/traits.pys` and JIT [J-trait](../tutorials/jit/J-trait.md)

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

### Structs

Structs are **identity-free value types**: fields only, no methods, no
`inherits` / `super` / `sealed` / `implements`. They compare and copy by value.

```pys
package struct Damage {
    int amount
    string type
}

fix struct DamageFix {
    int amount
    string type
}

struct Pair<T, U> {
    T first
    U second
}

Damage d1 = Damage(20, "physical")
Damage d2 = Damage(amount=20, type="physical")
fix Damage d3 = Damage(21, "physical")
var d4 = Damage(20, "electric")
```

Rules:

1. Fields are always public — no per-field `public` / `private` / …; use
   `global` / `package` / `module` on the **struct** to control who can import
   the type
2. **Field kind order** (parse-enforced): all `fix` fields before mutable fields
3. Canonical constructor from field order — positional and/or named args
   (`Type(...)`, never `new`); fields with defaults must be trailing
4. Pass-by-value: assignment, call arguments, and returns copy the instance
   (nested struct fields are deep-copied)
5. `==` is field-wise (not reference identity)
6. No `shared <Struct>`; struct fields and struct bindings reject `null`
7. IDE: type and field go-to, keyword highlighting, semantic type coloring,
   hover/snippets for `struct`
8. Mutability matrix (also applies to nested paths like `o.inner.x`):

| Declaration | Binding | Field `fix` | Field writes |
|-------------|---------|--------------|--------------|
| `struct S` | typed / `var` | no | allowed |
| `struct S` | typed / `var` | yes | rejected |
| `struct S` | `fix` | (any) | rejected |
| `fix struct S` | (any) | (any) | rejected |

9. Hashable only when the type is `fix struct` or every field is `fix`
10. Optional type parameters: `struct Pair<T, U> { … }` (erased at emit, like classes)

**Struct vs `dict`:** same idea as a schema-fixed data bag (value equality, no
methods), but nominal typing, fixed fields, no `null` fields, and optional
per-field / type-level `fix`. Who may use the type is controlled by the
struct’s top-level visibility — not per-field modifiers. Construct with
`Damage(...)`, not brace literals. Prefer a **class** when the type has
behavior or inheritance.

### `data` (value objects) and `entity` (identity keys)

Two first-class constructs separate **structural** vs **identity** equality —
deliberately distinct from `struct` (no generated VO/Entity contract) and
`class` (reference equality by default). Full rationale:
[`DATA_ENTITY.md`](DATA_ENTITY.md).

```pys
data Money {
    int amountCents
    string currency
}

Money m1 = Money(10000, "USD")
Money m2 = Money(10000, "USD")
# m1 == m2 → true (all fields); fields are immutable

entity Customer identity(customerId) {
    private fix int customerId
    public string name

    public Customer(int customerId, string name) {
        this.customerId = customerId
        this.name = name
    }
}

Customer a = Customer(7, "Ana")
Customer b = Customer(7, "Ana B.")
# a == b → true (customerId only); name may change
```

Rules (summary):

1. **`data`**: fields only (implicitly `fix` + public); implicit ctor like
   `struct`; copy on assign/call/return; `==` / hash / string form over **all**
   fields; no `inherits` / `uses` / `implements` / hand `equals`
2. **`entity`**: explicit ctor; fields need `member_access`; root requires
   `identity(...)`; every identity field must be `fix`; **body order**
   (parse-enforced): identity fields → other `fix` → mutable → constructors →
   methods; `==` / hash / string form over identity fields only (parent keys
   then local); may `inherits` another **entity** (optional local `identity`
   appends to the parent key); no `uses` / `implements`; hand `equals` /
   `hashCode` / `toString` rejected
3. Prefer **`struct`** for ad-hoc bags without a VO/Entity contract; **`data`**
   for immutable interchangeable values; **`entity`** for lifecycle rows;
   **`class`** for general OOP

| Construct | Equality | Identity | Inheritance |
|-----------|----------|----------|-------------|
| `struct` | Field-wise (no VO contract) | No | No |
| `data` | All fields, generated | No | No |
| `entity` | Identity fields only | `identity(...)` | Entity-only |
| `class` | Reference (manual override) | Implicit | Yes |

### Lambdas

Anonymous first-class functions. Type form `lambda<P…, R>` (last type is the
return; `lambda<int>` means zero parameters returning `int`).

```pys
lambda<int, bool> isEven = n => n % 2 == 0
int doubled = apply(5, n => n * 2)

lambda<int, int, int> safeDivide = (int a, int b) => {
    if (b == 0) {
        return 0
    }
    return a / b
}
```

Rules:

1. Forms: `n => expr`, `(params) => expr`, `(params) => { … }`, `() => …`
2. Param types may be omitted when the target type is `lambda<…>`
3. **Capture by value** at creation; captured names are read-only unless
   `shared` or `atomic` (same model as `tasks`)
4. Foreach / C-style loop variables are immutable per iteration — each lambda
   in a loop gets its own captured value (no Python late-binding bug)
5. `name.loop(fn)` still maps: `list(map(fn, name))`

See [`examples/lambdas.pys`](../examples/lambdas.pys) and JIT
[`J-lambda`](../tutorials/jit/J-lambda.md). For race-free `+=` across tasks,
use [`atomic`](#11-concurrency-tasks--task--await--shared--atomic)
([CONCURRENCY](CONCURRENCY.md), [J-atomic](../tutorials/jit/J-atomic.md)).

### Enums

Enums are **nominal closed sets** of named constants. Members are immutable.
Optional `global` / `package` / `module` on the declaration (same as structs).

```pys
enum Priority {
    LOW
    MEDIUM
    HIGH
}

enum HttpStatus {
    OK = 200
    CREATED = 201
}

enum Method {
    GET = "GET"
    POST = "POST"
}

HttpStatus s = HttpStatus.OK
print(s == HttpStatus.CREATED)
print(s.value)
```

Rules:

1. Body must be non-empty
2. All-or-nothing values: every member has `=` or none do (implicit →
   `enum.auto()`)
3. Explicit values are homogeneous (all `int` or all `string`) and unique
   (duplicate aliases, if added later, will be a real language form — PYS does
   not use `@` annotations)
4. Access only as `EnumName.MEMBER` (no call constructor / `new`)
5. Nominal typing: no implicit assign from bare `int` / `string`; use `.value`
   for the underlying value
6. `==` / `!=` only between members of the **same** enum
7. Member names should be `SCREAMING_SNAKE_CASE` (compiler **warning**, with IDE
   tip + rename quick fix) — compile still succeeds
8. Emit: implicit → `enum.Enum` + `auto()`; int → `IntEnum`; string → `StrEnum`
9. **Deferred:** `match` / exhaustiveness checking (follow-up)

---

## 7. Visibility and modules

### Top-level exports (`global` / `package` / `module`)

| Keyword | Who can import it |
|---------|-------------------|
| (default / omit) | Nobody outside this file (module-private) |
| `package` | Other `.pys` files in the **same package**: same folder by default, or the same path relative to a declared `pys.toml` `[source_roots]` entry (e.g. `src/billing` and `tests/billing`) — see [ADR-017](adr/ADR-017-source-roots-same-package-tests.md) and `examples/source_roots/` |

### Project source roots (`pys.toml`)

Optional project-manifest (not a language keyword). Declares roots whose
relative paths define package identity:

```toml
[source_roots]
main = "src"
test = "tests"
```

Without `[source_roots]`, same-folder remains the package rule. Mismatched
packages emit `pys.package-mismatch` with a move-file quick fix in the IDE.
| `global` | Any importer |
| `module` | Explicit module scope (same file family) |

Applies to functions, classes, structs, `data`, `entity`, enums, interfaces, and top-level `const` / `fix`.
(`lambda<…>` bindings use the same top-level visibility rules as other typed decls.)

### Member access (inside classes)

| Keyword | Intent |
|---------|--------|
| `public` | Usable from outside the class |
| `private` | Only this class |
| `protected` | This class and subclasses |
| `module` | Same module / teaching module boundary |

---

## 8. Imports

**Placement:** every `import` / `from … import` must sit in the import prefix
at the top of the file (before any declaration or statement). Late imports are
a parse error — see [Enforced member ordering](#enforced-member-ordering).

```pys
import interfaces               # whole .pys module (same folder / discovery)
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

## Enforced member ordering

PYS rejects out-of-order **kinds** at parse time (educational `FatalParseError`),
not as a linter warning. The axis is **kind** only — `public` / `private` / …
may appear in any order within a section. Framing for teaching: *PYS enforces
this because it is good practice everywhere; most other languages only
recommend it.* Full rationale: [`requirements/enforced_ordering.md`](../requirements/enforced_ordering.md).
JIT: [J-member-order](../tutorials/jit/J-member-order.md).

| Body | Required kind order |
|------|---------------------|
| File (top level) | All imports → declarations / statements |
| `class` | `const` fields → `fix` fields → mutable fields → constructors → methods (`abstract` included) |
| `struct` | `fix` fields → mutable fields |
| `trait` | `requires` → methods |
| `entity` | Identity fields → other `fix` → mutable → constructors → methods |

**Not enforced:** positional order of items inside `tasks { }` (DAG / `await`
already structures dependency intent).

Changing a member’s role (e.g. mutable → `fix`) means **relocating** it to
the correct section — that relocation is intentional.

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

## 11. Concurrency (`tasks` / `task` / `await` / `shared` / `atomic`)

**Full guide with examples:** [`CONCURRENCY.md`](CONCURRENCY.md)

One concurrent unit, structured lifetime, explicit shared mutation. Tasks in the
same process **share memory**; a `tasks` block joins children — it does not
isolate memory.

| Keyword | Meaning |
|---------|---------|
| `task { … }` | One concurrent unit (must be inside `tasks`) |
| `tasks { … }` | Group; leaving the block waits for all |
| `await expr` | Wait until ready (only inside a `task`) |
| `shared` | Outer name may be mutated across tasks (**visibility**, not race-freedom) |
| `atomic` | Indivisible `+=`/`-=`/`++`/`--` / `get` / `compareAndSet` (implies shared) |

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

atomic int counter = 0
tasks {
    task { counter += 1 }
    task { counter += 1 }
}
```

Outer locals are **read-only** inside a task unless declared `shared` or
`atomic`. Prefer **parameters** for inputs. Await edges in a group must form a
**DAG** — cycles are **rejected** (`pys.await-cycle`). Runnable suite:
`examples/concurrency/main.pys`; atomic DoD: `examples/atomic.pys`.

---

## 12. Quick example (dense)

```pys
import interfaces
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

For a full walkthrough, see `examples/main.pys`, `examples/classes.pys`, and
`examples/interfaces.pys`.

---

## Related project files

| File | Role |
|------|------|
| `docs/language.ebnf` | Formal EBNF (includes concurrency) |
| `docs/language-railroad.html` | Railroad diagram visuals |
| `docs/CONCURRENCY.md` | `tasks` / `task` / `await` / `shared` / `atomic` guide |
| `tutorials/` | Distributable learning track (4C/ID, JIT, scaffolding) |
| `examples/main.pys` | Dense feature showcase (not the curriculum path) |
| `examples/classes.pys` | Classes: fields, ctors, inherits, sealed |
| `examples/interfaces.pys` | Interfaces + implements (vehicle domain) |
| `examples/abstract_classes.pys` | Abstract classes / template method |
| `examples/concurrency/` | Concurrency showcase (`main.pys` offline; `http/http_main.pys` live HTTPS package) |
| `transpiler/language_spec.py` | Line translation rules |
| `pys.deps` | External Python dependencies (not language syntax) |
