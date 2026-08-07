# 3.1. Formatting output

String concatenation with `+` works, but longer messages get noisy.
PYS can **interpolate** expressions inside a string:

```pys
int a = 3
float f = 1.5
print("a is {a}, f is {f}")
```

Output:

```text
a is 3, f is 1.5
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
float ratio = 0.5
bool active = true
char grade = 'B'
print("#i{x} is an int")
print("#s{greeting} is a string")
print("#f{ratio} is a float")
print("#b{active} is a bool")
print("#c{grade} is a char")
```

Output:

```text
7 is an int
hi is a string
0.5 is a float
True is a bool
B is a char
```


If you write `#i{greeting}`, the compiler rejects it — that is the point.

> **Sidebar — `#o{…}` for objects**
>
> `#o{…}` guards **non-primitive** values (class / struct / `data` /
> `entity` instances). You will use it once those types appear in
> [Session 3](chapter_4_session_objects.md). Until then, stick to `#s` / `#i` / `#f` /
> `#b` / `#c`.

### Exercise

> Print `"score=42 points"` using `#i{…}` for the number and ordinary text
> for the rest. Then deliberately break it with `#s{42}` (or `#i{"x"}`) and
> read the diagnostic.

---

[Previous: Spoiler — files](basics_spoilers_files.md) · [Next: Variables: var, fix, and const](chapter_2_2_variables.md)
