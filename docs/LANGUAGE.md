# PYS language documentation

Formal grammar: [`language.ebnf`](language.ebnf) (EBNF).  
Visual railroad diagrams: [`language-railroad.html`](language-railroad.html) (open in a browser).  
Toolchain architecture: [`ARCHITECTURE.md`](ARCHITECTURE.md).

PYS is a typed teaching language with a shared front end (lex → parse → sem)
and **dual emit backends**: **Python** (reference — full surface, deps, DAP)
and **JavaScript** / Node (teaching-core + DAP via js-debug; see
[ADR-030](adr/ADR-030-javascript-emit-target.md)). Prefer **brace style**
(`{` … `}`), as in `examples/main.pys`. Indentation style and legacy `then:` /
`do:` forms remain for compatibility (see Appendix A in the EBNF).

Select the backend with CLI `--target python|javascript` or the extension
setting `pys.emitTarget`. Target-specific packages live under
`examples/by-target/` (`pys.toml` `[dependencies]` / `[dependencies.npm]` →
central repository).

Statements end at newline by default. An optional `;` terminator is allowed
after any statement; it is **required** only when two statements share one
physical line (`int x = 10; int y = 20`). A trailing `;` alone on a line is
fine. Identifiers are case-sensitive. Use **4 spaces** for indentation when
not using braces; tabs are illegal. In **brace mode**, structure still comes
from `{ }`, but sibling members and nested bodies must stay on a consistent
4-space grid (`pys.indent` — transpile error with tip / IDE quick fix).

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
only for a **local or script-top declaration** when the initializer makes the
type obvious. `var` is **not** a type — it cannot appear as a return type,
parameter type, field type, or generic argument ([ADR-025](adr/ADR-025-var-declaration-only.md)).

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
| `object` | opaque foreign or dynamically shaped value (sockets, locks, driver cells); anything may assign into `object` |
| `nullable<T>` | may hold a `T` value or the literal `null` (absence) |
| `null` | absence literal for `nullable<T>` only (Python `None` at runtime) |

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

**Display other bases** (hardware dumps; [ADR-024](adr/ADR-024-base-display-builtins.md)):

| Builtin | Meaning |
|---------|---------|
| `toBin(value)` / `toBin(value, widthBits)` | Binary digits as `string` |
| `toHex(value)` / `toHex(value, widthDigits)` | Lowercase hex digits |
| `toOct(value)` / `toOct(value, widthDigits)` | Octal digits |

No `0b` / `0x` / `0o` prefix in the result (source literals still use those
prefixes). Optional width left-pads with `'0'`; if the value needs more digits
than `width`, the full form is kept (no truncation). Values must be
non-negative int-like. Typed interpolation `#b{…}` remains **bool**, not binary.

```pys
byte flags = 0b1011_1101
print(flags)             # 189 (decimal)
print(toBin(flags))      # 10111101
print(toHex(flags))      # bd
print(toBin(0b1010, 8))  # 00001010
print(toHex(0xA, 2))     # 0a
```

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
2. `var` — **declaration form only** (`var name = expression`); type must be
   inferable from the initializer. Legal at script/module top and inside
   function/method bodies. **Illegal** as a return type, parameter type, field
   type, or generic argument (use an explicit type, omit a parameter type, or
   use `object` for foreign values).
3. `const` — fixed at compile time; no reassignment
4. `fix` — evaluated once, then immutable

```pys
# Good
var count = 0
object cell = row[0]          # foreign / opaque
function void serve(conn) {   # omitted param type at a foreign boundary
    print(conn)
}

# Illegal
# public var lookup(dict c, string e) { ... }
# function int f(var x) { return 1 }
# private var q
# list<var> bad = []
```

#### One declaration, one name

Every PYS declaration binds exactly one name; an initializer, when present,
belongs only to that name. Write separate statements when two variables start
with the same value:

```pys
int x = 10
int y = 10
```

PYS rejects both `int x, y = 10` and `int x = 10, y = 10`. Neither form adds
expressive power, and the first has conflicting cross-language expectations:

| Language | Local declaration or assignment | Result |
| --- | --- | --- |
| C / C++ | `int x, y = 10;` | Only `y` is initialized; an automatic local `x` has an indeterminate value and must not be read |
| Java / C# | `int x, y = 10;` | Only `y` is initialized; reading local `x` before assignment is a compile-time error |
| Go | `var x, y int = 10, 10` | Initializer values correspond to names by position |
| Python | `x, y = 10, 10` | Assignment unpacks two values by position; this is not a typed declaration |

C/C++ objects with static storage and Java/C# fields have separate default-
initialization rules; the table describes local variables. PYS avoids making
students infer whether one initializer belongs to one name or several. This
single-name rule also applies to `var`, `fix`, `const`, `shared`, `atomic`, and
fields. Parameter lists remain comma-separated because each parameter has its
own explicit type-and-name slot and no declaration-time initializer.

See [ADR-020](adr/ADR-020-one-name-per-declaration.md).

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

**Statement** — `case LABEL:` then either a bare statement sequence or an
explicit `{ … }` block. Multiple labels may share one arm with commas
(`case MONDAY, FRIDAY:`). A trailing bare `continue` falls through to the next
case (nested-loop `continue` keeps loop meaning). `break` is not required.
Bare enum labels (`MONDAY`) resolve from the subject type (also `Day.MONDAY`).
An explicit block body introduces nested lexical scope (locals do not leak to
sibling arms); a bare sequence shares the enclosing switch scope. Non-exhaustive
enum/primitive switches without `default` emit a **warning**.

```pys
switch (day) {
    case MONDAY, FRIDAY:
        continue
    case SUNDAY:
        numLetters = 6
    case WEDNESDAY: {
        numLetters = 9
        print("wed")
    }
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
loop (int i = 0; i < 3; i++) {
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

#### Why the C-style form has one counter

The C-style `loop` deliberately models one induction variable: its initializer,
condition, and step must name the same variable, and the body cannot modify it.
That keeps the condition that controls termination and the step that advances
toward termination visibly connected.

Java and C++ permit compact headers such as this (this is not PYS):

```java
for (int x = 0, y = 10; x < 10; x++, y++) {
    System.out.println(x + ", " + y);
}
```

The compiler accepts changes such as `y += 2` in the step or an additional
`y++` in the body. The condition still checks only `x`, so keeping `x` and `y`
in sync is a programmer-maintained invariant rather than a language guarantee.
(C++ uses its comma operator in the update expression; Java uses a
comma-separated list of update expressions.)

PYS does not add multi-counter or `{x, y}` header syntax. Use the while-style
form when several mutable values participate:

```pys
int x = 0
int y = 10

loop (x < 3) {
    print("#i{x}, #i{y}")
    x++
    y++
}
```

This prints `0, 10`, `1, 11`, and `2, 12`. Initialization and mutation remain
ordinary visible statements; the narrow C-style form keeps its single-counter
immutability guarantee. See [ADR-019](adr/ADR-019-single-counter-loops.md).

**Foreach** (binder type is required and must match the collection element
type — `T[]`, `list<T>`, `set<T>`, `dict<K,V>` keys, or a uniform tuple):

```pys
loop (tuple<string, string> row in rows) {
    print(row)
}
```

`loop (x in xs)` without a type, or a binder type that does not match the
elements (e.g. `loop (string x in int[])`), is a compile error.

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
4. **Call arguments** are either all positional or all named — never mixed
   (`greet("Ada", times=2)` is illegal; `greet(name="Ada", times=2)` is fine).
   The same rule applies to methods, class/`entity` constructors, and
   `struct`/`data` construction. Unknown library calls may still use Python-style
   mixed kwargs at the foreign boundary.
5. Visibility on the function controls who may import it (see §7)
6. Void functions (no value returned) may omit the return type, or write `void`
   explicitly. A `void` body must not `return expr`.

Inside a **class**, do not write `function` / `func` — methods use member access
modifiers instead (`public name(…) { … }` or `public void name(…) { … }`).

### Library decorators

PYS allows **applying** library callables with `@` above a `function`, `class`,
or method ([ADR-026](adr/ADR-026-library-decorators.md)):

```pys
function object mark(f) {
    return f
}

@mark
function void hello() {
    print("hi")
}
```

Stacked `@expr` lines are allowed. Do **not** invent missing language features
with `@` (no `@alias`, no Lombok-style `@Data` — use real keywords such as
`data` / `abstract`). Decorators do not apply to fields or ordinary statements.

### Explicit absence: `nullable<T>`

Ordinary types are **non-null by default**. Only `nullable<T>` may hold either a
present `T` or the literal `null`. Absence is not zero, not `""`, and not an
empty collection — those are present values. SQL `NULL` maps to PYS `null` and
back; Data Mappers must not invent defaults.

```pys
string requiredName = "Sanne"
nullable<string> preferredName = null
preferredName = "Ada"

function string display(nullable<string> name) {
    if (name == null) {
        return "(geen naam)"
    }
    return name.upper()
}
```

Rules:

1. `string name = null` is rejected; write `nullable<string> name = null`.
2. Member access, indexing, arithmetic, and other `T` operations need a
   dominating null check (or an exiting guard) that proves the value is present.
3. `nullable<void>` and `nullable<nullable<T>>` are illegal.
4. Entity `identity(...)` fields must stay non-null. A present struct/data value
   stays complete; wrap with `nullable<Struct>` when the whole value may be absent.
5. `atomic nullable<T>` is illegal. `shared nullable<T>` is allowed, but separate
   shared reads do not narrow — copy a synchronized snapshot to a local first.
6. Use `nullable<T>` for expected absence; use `result<T, E>` for failure.
   `result<nullable<T>, E>` covers found / not-found / failed.
7. PYS-facing print, interpolation, and debugger values show `null`, not Python
   `None`.

See [ADR-023](adr/ADR-023-explicit-nullability.md) and [CER-028](evolution/CER-028-nullable.md).

### Recoverable errors: `result<T, E>`

`result<T, E>` makes recoverable failure visible in a function signature:

- `ok(value)` carries a success value of type `T`
- `error(payload)` carries an error value of type `E`
- `ok()` is valid only for `result<void, E>`; `error` always needs a payload
- `ok` and `error` are reserved constructors, not user-declarable names

Constructors are contextually typed by a declared binding, parameter, lambda,
or return type:

```pys
function result<int, string> parseCount(bool valid) {
    if (valid == false) {
        return error("count is invalid")
    }
    return ok(3)
}

result<int, string> outcome = parseCount(true)
switch (outcome) {
    case ok(value):
        print(value)
    case error(message):
        print(message)
}
```

Output:

```text
3
```

A result switch uses `case ok(name)` and `case error(name)`. Each payload name
exists only inside its arm and has the corresponding `T` or `E` type. The
switch must contain both patterns or a `default`; duplicate patterns and
literal labels on a result are errors. Expression arms must also yield one
common type. Because `error` is a keyword, do not name the failure binding
`error` — prefer `message`, `reason`, or a domain word.

Built-in recoverable parsers return results directly:

- `parseInt(text)` → `result<int, string>`
- `parseFloat(text)` → `result<float, string>`

They succeed or fail according to the active emit target's number parsing
(Python `int`/`float`, or the JS helpers `_pys_parse_int` /
`_pys_parse_float`). Prefer them over bare `int(...)` /
`float(...)` when the caller must handle bad text without crashing.

Console I/O builtins (no import):

- `print(...)` — write a line
- `input()` / `input(prompt)` → `string` — read a line from the keyboard
  (optional prompt). Legacy `import input from builtins` still compiles.

Postfix `propagate` unwraps success and returns failure immediately:

```pys
function result<int, string> doubled(bool valid) {
    int count = parseCount(valid) propagate
    return ok(count * 2)
}
```

The operand must be a result. The enclosing function (or result-typed lambda)
must return a result with **exactly the same error type `E`**. `propagate` is
illegal across `task` boundaries. A `result<T,E>` never implicitly converts to
`T`; handle it with `switch` or `propagate`.

**Why a keyword, not `?`:** a one-character operator is easy to type reflexively
(Swift’s `!` / `try!` are a documented crash vector). `?=>` collides with
lambda/switch `=>`; `try(...)` collides with exception `try`/`catch` (rejected
in PYS). See [ADR-021](adr/ADR-021-result-propagate-panic.md).

At a resolved entrypoint, top-level `propagate` may pass an `error` to the
runtime. This outcome is a **panic**: remaining statements are skipped, stderr
shows the error and PYS propagation sites, and the process exits non-zero.
`panic` is not source syntax.

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

package interface GUIFactory {
    Button createButton()
    Checkbox createCheckbox()
}
```

Return types may be builtins (`int`, `string`, …), `void`, or **nominal** types
(`Button`, `list<string>`, …) — same `return_type` production as elsewhere.

### Classes

```pys
package class Cart implements Drivable {
    private string id

    public constructor(string id) {
        this.id = id
    }

    public start() {
        print("cart #s{this.id}")
    }
}

package class BigCart inherits Cart {
    public constructor(string id) {
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
3. Constructors use the explicit `constructor` keyword:
   `public constructor(...)` (not the type name). Omitting the access
   modifier defaults to **`module`** (same-file teaching boundary), like a
   top-level `class` without `global`/`package`. Write `public constructor`
   when the type should be constructible from other modules. See
   [ADR-027](adr/ADR-027-constructor-keyword.md).
4. One superclass via `inherits` (alias `super` in the header); zero or more
   traits via `uses`; one or more interfaces via `implements`
5. Header order: `inherits` → `uses` → `implements`
6. `this` / `super` for current instance / parent. Subclass constructors that
   omit `super(...)` / `this(...)` get an implicit zero-arg `super()` at the
   start — write `super(args)` when the parent constructor needs arguments.
   Subclasses may call public members of a **library** parent (for example
   `inherits QMainWindow` → `this.setWindowTitle(...)`) when that parent was
   imported via `pys.toml` `[dependencies]` / the standard library.
   Instance fields are accessed as `this.name` inside methods/constructors —
   bare field identifiers are an error.
7. `closed` may mark a class that should not be subclassed further
8. Methods are **closed by default**. Mark extension points with `open`;
   subclasses plug in with `override` or `override closed`. Abstract methods
   are implicitly open sockets. An implicit root provides `toString` /
   `equals` / `hashCode`. See [ADR-028](adr/ADR-028-open-override-closed.md).
9. Optional `static` after visibility marks **class-wide** fields and methods
   (one shared cell / no instance). Static methods cannot use `this`, and
   cannot combine with `open`/`override`. Access as `ClassName.member`.
   See [ADR-029](adr/ADR-029-static-members.md).
10. `abstract` marks a class that cannot be instantiated and may declare
   body-less `abstract` methods; mutually exclusive with `closed`
11. Optional type parameters: `class Pair<T, U> { … }`
12. See `examples/classes.pys` for fields, constructors, `inherits`,
    `open`/`override`, `closed`, and `static`

### Abstract classes

An **abstract class** is a nominal type with shared fields/concrete methods plus
variation points declared as `abstract` methods (no `{ … }` body). Subclasses
must implement every inherited abstract method. Direct construction
(`AbstractName(...)`) is rejected; constructors may still run via `super(...)`.

```pys
abstract class AbstractList {
    protected int size

    public constructor() {
        this.size = 0
    }

    public bool isEmpty() {
        return this.size == 0
    }

    public abstract string get(int index)
    public abstract void add(string item)
}

class ArrayListPys inherits AbstractList {
    public constructor() { super() }
    public override string get(int index) { return "" }
    public override void add(string item) { this.size = this.size + 1 }
}
```

**Litmus test:** prefer an abstract class when shared code must call back into a
method that varies per subclass (template method — e.g. `contains` → `get`).
If you only need horizontal reuse with no `is-a` polymorphism, use a **trait**;
if you need only a contract with no bodies/fields, use an **interface**.
See [ADR-010](adr/ADR-010-abstract-classes.md).

Rules:

1. Abstract methods only inside `abstract class`; need access + `abstract` + return type
2. Concrete subclasses must mark implementations `override`
3. `void` means no value: do not `return expr` (bare `return` is fine)
4. Abstract classes **are** types (unlike traits) — usable for bindings / polymorphism
5. See `examples/abstract_classes.pys` and JIT [J-abstract](../tutorials/jit/J-abstract.md)

### Traits

A **trait** is reusable behavior composed onto a class with `uses`. It is **not**
a nominal type (cannot appear in `implements`, as a variable type, or as
`Trait()`). Methods are always public; host state is declared with `requires`
and accessed via `this`. `requires` makes every host dependency explicit
(classical trait composition; Schärli et al., 2003) — not duck-typed mixins.
`uses A, B` and `uses B, A` are equivalent when there is no collision.

```pys
trait Printable {
    requires string name

    string label() {
        return "Item: " + this.name
    }
}

class Product uses Printable {
    private string name

    public constructor(string name) {
        this.name = name
    }
}

# Host field names may differ — remap requires only (not trait methods):
class CatalogItem uses Printable(name: title) {
    private string title

    public constructor(string title) {
        this.title = title
    }
}
```

Rules:

1. Every `this.x` in a trait method must be listed in that trait's `requires`
   (or be another method of the same trait)
2. **Body order** (parse-enforced): all `requires` before any method
3. The host class (or an ancestor) must supply each `requires` field/method
4. **Requires remapping (opt-in):** `uses Trait(reqName: hostMember, …)` maps
   a trait `requires` name onto a differently named host member. Unmapped
   requirements still match by exact name. Multiple entries are allowed
   (`x: a, y: b`). Remaps apply to member access **and** to `{this.req}` /
   `#i{this.req}` holes inside interpolated strings. Trait **methods** keep
   their names on every host and cannot appear as remap left-hand sides
   (dependency surface vs offered contract)
5. If two used traits define the same method name, the class must override it;
   call `TraitName.method(this)` from the override to pick a side
6. See `examples/traits.pys` and JIT [J-trait](../tutorials/jit/J-trait.md)

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
    public constructor(T first, U second) {
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
`inherits` / `super` / `closed` / `implements`. They compare and copy by value.

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
3. Canonical constructor from field order — positional **or** named args
   (`Type(...)`, never `new`); never mix styles in one call; fields with
   defaults must be trailing
4. Pass-by-value: assignment, call arguments, and returns copy the instance
   (nested struct fields are deep-copied)
5. `==` is field-wise (not reference identity)
6. No `shared <Struct>`; plain struct fields and bindings reject `null`
   (`nullable<Struct>` and nullable fields are allowed — ADR-023)
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
methods), but nominal typing, fixed fields, no implicit nullability, and optional
per-field / type-level `fix`. Who may use the type is controlled by the
struct’s top-level visibility — not per-field modifiers. Construct with
`Damage(...)`, not brace literals. Prefer a **class** when the type has
behavior or inheritance. Use `nullable<Struct>` when the whole value may be
absent.

### `data` (value objects) and `entity` (identity keys)

Two first-class constructs separate **structural** vs **identity** equality —
deliberately distinct from `struct` (no generated VO/Entity contract) and
`class` (reference equality by default). This is Evans’s Value Object vs Entity
split (2003) as language constructs, not framework annotations. Full rationale
and production citations (Hibernate/`HashSet`, EF Core, Lombok `@Data`):
[`DATA_ENTITY.md`](DATA_ENTITY.md) · [ADR-011](adr/ADR-011-data-and-entity.md).

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

    public constructor(int customerId, string name) {
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

Anonymous first-class functions. Type form `lambda<P… -> R>` (parameters left
of `->`, return type right). Sugar `lambda<int>` means zero parameters
returning `int`; write `lambda<-> int>` for the same shape without sugar.

```pys
lambda<int -> bool> isEven = n => n % 2 == 0
int doubled = apply(5, n => n * 2)

lambda<int, int -> int> safeDivide = (a, b) => {
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

**Why these capture rules:** other languages commonly hit shared-loop-binding
(JS `var`, pre-C#5 `foreach`) or late binding (Python closures). PYS captures
by value at creation and keeps loop binders per-iteration; mutate only through
`shared` / `atomic`. Cross-language table: [ADR-012](adr/ADR-012-lambdas.md).

See [`examples/lambdas.pys`](../examples/lambdas.pys) and JIT
[`J-lambda`](../tutorials/jit/J-lambda.md). For race-free `+=` across tasks,
use [`atomic`](#11-concurrency-tasks--task--await--shared--atomic)
([CONCURRENCY](CONCURRENCY.md), [J-atomic](../tutorials/jit/J-atomic.md)).

### Enums

Enums are **nominal closed sets** of named constants. Members are immutable.
Optional `global` / `package` / `module` on the declaration (same as structs).

```pys
enum Priority {
    LOW,
    MEDIUM,
    HIGH
}

enum HttpStatus {
    OK = 200,
    CREATED = 201
}

enum Method {
    GET = "GET",
    POST = "POST"
}

HttpStatus s = HttpStatus.OK
print(s == HttpStatus.CREATED)
print(s.value)
```

Rules:

1. Body must be non-empty; members are **comma-delimited** (optional trailing
   comma). Layout — one line, wrapped, or one-per-line — has no semantic meaning
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
| `global` | Any importer |
| `module` | Explicit module scope (same file family) |

### Project manifest (`pys.toml`)

One file holds entrypoint, source roots, interpreter constraint, and
dependencies (Python and optional npm):

```toml
[project]
main = "src/app.pys"
# Optional emit/runtime target for Run Project and bare `transpiler run`
# (default: python). Status-bar `pys.emitTarget` still applies to Run File.
# target = "python"  # or "javascript"

[source_roots]
main = "src"
test = "tests"

[interpreter]
version = ">=3.10"

[dependencies]
"mysql-connector-python" = { version = "8.0.33", build = "run" }

[dependencies.npm]
mysql2 = "^3.11.0"
```

Without `[source_roots]`, same-folder remains the package rule. Mismatched
packages emit `pys.package-mismatch` with a move-file quick fix in the IDE.

Python pins require a sibling hashed `pys.lock` (ADR-002). npm pins install on
Run into `~/.pys/repository/npm/<fingerprint>/` (no student-facing
`package.json`). Legacy indented `pys.deps` / silo `package.json` still load
with a deprecation warning.

When `[project].main` exists, Run and Debug reject a different selected file
under the application source roots. Files under a declared
`[source_roots]` entry named `test` / `tests` may still be run directly
(suite entrypoints). Without `[project].main`, a directly invoked `.pys` file
is the entrypoint. A bare directory run requires `[project].main`. The
configured path must resolve to an existing `.pys` file inside the manifest
directory; lexical and realpath escapes are rejected. The IDE action **Set as
entrypoint** writes this same field.

Optional `[project].target` is `"python"` or `"javascript"` (default
`python`). **Create PYS Project** writes this field after a target QuickPick
and may prompt to install missing Python / Node (ADR-001). **Run Project**
(context menu on `pys.toml`) runs `[project].main` with that target and does
not use the workspace status-bar emit selector. Bare
`python -m transpiler run <file>` without `--target` also reads
`[project].target` from the nearest `pys.toml`.

Only the resolved entrypoint receives top-level `propagate`/panic semantics.
Imported modules do not: top-level `propagate` in an imported file is a compile
error and must be replaced by explicit result handling.

Applies to functions, classes, structs, `data`, `entity`, enums, interfaces, and top-level `const` / `fix`.
(`lambda<…>` bindings use the same top-level visibility rules as other typed decls.)

### Member access (inside classes)

| Keyword | Intent |
|---------|--------|
| `public` | Usable from outside the class |
| `private` | Only this class |
| `protected` | This class and subclasses |
| `module` | Same module / teaching module boundary |

These rules apply to every use site the analyzer sees — including member
reads inside string interpolations (`"…{obj.field}…"` / `#s{obj.field}`), not
only bare assigns and expression statements.

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
import tkinter as tk            # stdlib / locked package with alias
import mysql.connector          # package from pys.toml [dependencies]
```

- Local `.pys` modules: file / folder discovery; only `package` / `global`
  names are importable.
- Python packages: stdlib or entries in `pys.toml` `[dependencies]` (see README). Alias `as` is
  for those packages.

---

## Enforced member ordering

PYS rejects out-of-order **kinds** at parse time (educational `FatalParseError`),
not as a linter warning. The axis is **kind** only — `public` / `private` / …
may appear in any order within a section. Framing for teaching: *PYS enforces
this because it is good practice everywhere; most other languages only
recommend it* (habit transfers; Java/C# will not reject the same layout).
Fixed kind positions also reduce scanning cost for readers (Sweller). Decision
record: [ADR-015](adr/ADR-015-enforced-ordering.md).
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

**`+` overload (string concatenate):** left-associative.

| Operands | Meaning |
|----------|---------|
| Both non-string (e.g. `int` / `float`) | Arithmetic add |
| Either side is `string` | Concatenation; the other operand(s) are coerced to text |

```pys
print(3 + 10)                          # 13 — arithmetic
print("age=" + 18)                     # age=18 — coerce int
print(1990 + " was a year")            # 1990 was a year
fix int birthYear = 1990
print("born in " + birthYear)          # born in 1990 — no str(...) needed
```

Emit lowers coerced operands with the Python target’s `str(...)`. Explicit
`str(x)` remains valid when you need a `string` without a concatenate
(e.g. `string label = str(n)`). Typed interpolation (`#i{…}`, …) is unchanged
— those tags are type *guards*, not this coerce rule.

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
    public constructor(string make, string model, int year, string color) {
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
| `examples/classes.pys` | Classes: fields, ctors, inherits, open/override, closed, static |
| `examples/interfaces.pys` | Interfaces + implements (vehicle domain) |
| `examples/abstract_classes.pys` | Abstract classes / template method |
| `examples/concurrency/` | Concurrency showcase (`main.pys` offline; `http/http_main.pys` live HTTPS package) |
| `transpiler/language_spec.py` | Line translation rules |
| `pys.toml` | Project entrypoint, source roots, and dependencies (not language syntax) |
| `pys.lock` | Hashed Python lock sibling (ADR-002) |
