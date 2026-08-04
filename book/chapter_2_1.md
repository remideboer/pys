# 3.1. Formatting output

String concatenation with `+` works, but longer messages get noisy.
PYS can **interpolate** expressions inside a string:

```pys
int a = 3
float f = 1.5
print("a is {a}, f is {f}")
```

The `{a}` slot is replaced by the value of `a`.

## Typed interpolation

Typed slots are a **guard**, not a cast. The expression must already have
the matching type or the transpile fails:

| Form | Required type |
|------|----------------|
| `#s{…}` | `string` |
| `#i{…}` | `int` |
| `#f{…}` | `float` |
| `#c{…}` | `char` |
| `#b{…}` | `bool` |
| `#o{…}` | non-primitive object |

```pys
int x = 7
string greeting = "hi"
print("#i{x} is an int")
print("#s{greeting} is a string")
```

If you write `#i{greeting}`, the compiler rejects it — that is the point.

### Exercise

> Print `"score=42 points"` using `#i{…}` for the number and ordinary text
> for the rest. Then deliberately break it with `#s{42}` (or `#i{"x"}`) and
> read the diagnostic.

---

[Previous: Session 1](chapter_2.md) · [Next: Variables: var, fix, and const](chapter_2_2.md)
