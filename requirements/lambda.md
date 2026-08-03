## PYS Language Specification — Lambdas

### 1. Overview

A lambda is an anonymous, first-class function value. It may appear inline wherever an expression is expected, or be bound to a named variable of type `lambda<...>` — consistent with treating functions as values with types, the same way `int`, `list<T>`, or any `named_type` are values with types. The keyword is lowercase, matching PYS's convention that all built-in type keywords (`int`, `list`, `dict`, `struct`, `enum`) are lowercase; only user-defined type names are capitalized by convention.

### 2. Grammar (EBNF extension)

```ebnf
(* ------------------------- Lambdas ------------------------- *)

lambda_expr       = lambda_params , "=>" , ( expression | block ) ;

lambda_params     = "(" , [ lambda_param_list ] , ")"
                   | identifier ;                 (* single untyped param, no parens *)

lambda_param_list = lambda_param , { "," , lambda_param } ;
lambda_param      = [ type_name ] , identifier ;
(* Type optional — inferred from the expected lambda<...> context
   when omitted, matching how call_suffix arguments are passed
   without redundant annotation. *)

(* ------------------------- Lambda type ------------------------- *)

lambda_type       = "lambda" , "<" , type_expr , { "," , type_expr } , ">" ;
(* Last type_expr is the return type; all preceding type_exprs are
   parameter types, in order. lambda<int> denotes a zero-parameter
   lambda returning int: () => int.
   lambda<int, int, bool> denotes (int, int) => bool. *)
```

Amendment to `type_expr`:

```ebnf
type_expr         = primitive_type
                 | collection_type , [ type_args ]
                 | named_type , [ type_args ]
                 | array_type
                 | lambda_type ;
```

Amendment to `primary`:

```ebnf
primary           = identifier
                 | "this"
                 | "super"
                 | literal
                 | array_literal
                 | "(" , expression , ")"
                 | constructor_call
                 | switch_expr
                 | lambda_expr ;
```

### 3. Static semantics — capture rules

These rules generalize the existing structured-concurrency capture rule (`outer captures are read-only unless declared shared`) from `task` bodies to *every* lambda in the language, so PYS has one capture model rather than two.

1. **Capture is by value, at the moment the lambda value is created.** A lambda reads the current value of every outer variable it references at construction time; it does not re-read the variable later (no late binding, unlike Python closures).
2. **Captured variables are read-only inside the lambda body**, unless the captured variable is declared `shared`. Attempting to assign to (or use a compound-assignment/increment operator on) a non-`shared` captured variable inside a lambda body is a compile-time error:
   `Cannot mutate captured variable 'x' inside lambda — declare it 'shared' if mutation across closures is intended.`
3. **Loop variables** (`c_for_loop`, `foreach_loop`) are already immutable within their loop body per existing PYS semantics. Consequently, a lambda created inside a loop captures a fresh, independent value on every iteration — this eliminates the classic "shared loop variable" closure bug (see §6) without requiring any additional rule.
4. **Return type inference**: if a `lambda_expr` is assigned to a variable of declared type `lambda<...>`, or passed as an argument whose parameter is typed `lambda<...>`, parameter types in `lambda_params` may be omitted and are inferred from the target `lambda_type`.
5. **Body form**: a lambda body may be a single `expression` (implicit return of its value) or a `block` containing `return_stmt` and other statements, matching function-body semantics; a block-form lambda without an explicit `return` yields no value.

### 4. Worked examples

**Structural typing / inline use (no named lambda type needed):**

```pys
int threshold = 10
list<int> filtered = numbers.loop(n => n > threshold)
```

**Named `lambda<...>` type — reusable, benefits from being a first-class value with a type:**

```pys
lambda<int, bool> isEven = n => n % 2 == 0

function int apply(int x, lambda<int, int> fn) {
    return fn(x)
}

int result = apply(5, n => n * 2)
```

**Block-form lambda body with `return`:**

```pys
lambda<int, int, int> safeDivide = (int a, int b) => {
    if (b == 0) {
        return 0
    }
    return a / b
}
```

**Capture correctness — the classic JS/Python closure bug, structurally impossible in PYS:**

```pys
list<lambda<int>> callbacks = []
loop (int i in [0, 1, 2]) {
    callbacks = callbacks + [() => print(i)]
}
# i is immutable per iteration (existing PYS rule) -> each callback
# captures its OWN i value at creation time.
# Output when invoked: 0, 1, 2 — never 2, 2, 2 as in Python,
# and never 3, 3, 3 as in pre-ES6 JavaScript with `var`.
```

**Mutation attempt without `shared` — rejected at compile time:**

```pys
int counter = 0
numbers.loop(n => counter += n)   # ERROR: counter is not shared

shared int counter = 0
numbers.loop(n => counter += n)   # allowed — intent made explicit
```

**Lambdas inside `tasks` — same rule, no special case needed:**

```pys
tasks {
    task fetchPrice(string symbol) {
        return api.get(symbol)
    }
    Price p = await fetchPrice("BTC")
    onResult(p => print("Price: " + p.value))   # p is a read-only capture
}
```

### 5. Delivered: `atomic` (see `docs/CONCURRENCY.md` / ADR-013)

`shared` makes mutation of a captured variable *visible* in the source, but it
does not by itself guarantee true atomicity under concurrent access. That
concern is specified in [`requirements/atomic.md`](atomic.md) and delivered as
`atomic` ([ADR-013](../docs/adr/ADR-013-atomic.md)): indivisible `+=`/`-=`/`++`/`--`,
`get` / `compareAndSet`, with `shared` kept as the visibility qualifier.
### 6. Cross-language design comparison (rationale for the capture rule)

| Language | Capture pitfall | Consequence | PYS's answer |
|---|---|---|---|
| JavaScript (pre-`let`) | `var` in a loop is function-scoped; all closures share one binding | `for(var i=0;i<3;i++) setTimeout(()=>print(i))` prints `3,3,3` | Loop variables are immutable per iteration; each lambda captures its own value |
| Python | Closures are late-binding: they read the variable at call time, not creation time | `[lambda: i for i in range(3)]` — all three return `2` | Capture is by value at creation time — no late binding possible |
| Java | Lambdas may only capture "effectively final" locals — no mutation at all | Forces awkward workarounds (`AtomicInteger`, single-element arrays) for legitimate accumulation | `shared` provides a controlled, explicit escape hatch Java lacks |
| C++ | `[&]` reference capture can dangle if the lambda outlives its scope | Undefined behavior in async code | PYS captures by value only — no reference-capture form exists |
| C# (pre-5.0) | `foreach` loop variable had one shared binding across iterations | Same symptom as the JS bug | Fixed identically to modern C#/JS: per-iteration scoping |

### 7. Comparison table — full construct family, updated

| Construct | Owns state | Identity | Equality | Mutability | Inheritance | Typical use |
|---|---|---|---|---|---|---|
| `struct` | Yes | No | None generated | Field-level | No | Ad-hoc grouped data |
| `data` | Yes | No | Structural, auto-generated | Fully immutable | No | DDD Value Objects |
| `entity` | Yes | Yes (`identity(...)`) | Identity-only, auto-generated | Key fields `fix`, others mutable | Yes | Database rows, domain entities |
| `class` | Yes | Implicit (reference) | Reference, overridable | Unrestricted | Yes (single) | General-purpose objects |
| `abstract class` | Yes | Implicit (reference) | — | Unrestricted | Yes (single, enforced) | Polymorphic variation point |
| `interface` | No | — | — | — | Multiple | Pure contract |
| `trait` | No (borrows host's) | — | — | — | Multiple (`uses`) | Horizontal behavior reuse |
| `lambda<...>` | Captured state only, by value | No | Reference (per closure instance) | Captures read-only unless `shared` | N/A | First-class function values, callbacks, strategy parameters |

### 8. Note for student-facing material (flagged, not yet written)

The capture concept — by-value, fixed at creation time, read-only unless `shared` — is the conceptually hardest part of this feature and requires dedicated explanatory material, not a passing mention. It should explicitly walk through the JavaScript/Python closure bugs in §6 side by side with PYS's behavior, so students see *why* the rule exists (a documented, recurring source of real bugs) before being asked to internalize *what* the rule is — the same pedagogical pattern already used for `requires` in traits and `identity(...)` in entities.