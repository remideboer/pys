# 3.2. Variables: var, fix, and const

Three declaration styles you will use constantly:

```pys
int count = 0              # typed, reassignable
var inferred = count + 1   # type taken from the initializer
fix int locked = count    # assign once, then locked
const int MAX = 100        # compile-time constant
```

*Compiles; no output.*



| Form | Meaning |
|------|---------|
| `type name = …` | Explicit type; can reassign unless also `fix`/`const` |
| `var name = …` | Infer type from initializer; reassignable |
| `fix …` | Evaluate once, then immutable |
| `const …` | Fixed at compile time; use `SCREAMING_SNAKE_CASE` |

Rule of thumb: reach for `fix` when the value should not change; use
`var` or a typed binding when it must; use `const` for true constants
like limits and configuration numbers.

```pys
const int MAX_RETRIES = 3
fix string mode = "demo"
var attempt = 0
attempt = attempt + 1
print("mode=#s{mode} attempt=#i{attempt} max=#i{MAX_RETRIES}")
```

Output:

```text
mode=demo attempt=1 max=3
```

## One declaration per name

When two variables need the same starting value, write two complete
declarations:

```pys
int x = 10
int y = 10
print("#i{x}, #i{y}")
```

Output:

```text
10, 10
```

These compact forms are intentionally **not** PYS:

```text
int x, y = 10
int x = 10, y = 10
```

*Both lines are compile errors in PYS.*

Why reject even the second, unambiguous form? It saves one line but adds no
new capability, while every PYS declaration currently introduces exactly one
name. More importantly, comma declarations teach conflicting habits: in a
Java or C-style local declaration, `int x, y = 10;` initializes only `y`;
Python's different `x, y = 10, 10` assignment gives both names a value by
position. Separate PYS declarations avoid making punctuation carry a
language-dependent guess.


### Exercise

> Declare `const int TEAM_SIZE = 4` and a `fix string coach` with your
> name. Try reassigning each and explain the errors.

---

[Previous: Formatting output](chapter_2_1.md) · [Next: Static types and casts](chapter_2_3.md)
