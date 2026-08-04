# 9.1. Types and declarations

| PYS | C# (typical) | Java (typical) |
|-----|--------------|----------------|
| `int x = 1` | `int x = 1;` | `int x = 1;` |
| `var x = 1` | `var x = 1;` | `var x = 1;` (newer Java) |
| `fix int x = 1` | `int x = 1;` (no reassign — discipline / `readonly` fields) | `final int x = 1;` |
| `const int MAX = 3` | `const int Max = 3;` | `static final int MAX = 3;` |
| `string` | `string` | `String` |
| `bool` | `bool` | `boolean` |
| `null` | `null` | `null` |
| Statements end at newline | Statements end with `;` | Statements end with `;` |
| Top-level statements run | Need `Main` entry | Need `main` entry |

## Why PYS declares one name at a time

PYS keeps a declaration one-to-one:

```pys
int x = 10
int y = 10
print("#i{x}, #i{y}")
```

Output:

```text
10, 10
```

Several other languages use commas, but they do not all mean the same thing:

| Language | Example | What happens |
| --- | --- | --- |
| C / C++ local | `int x, y = 10;` | Only `y` is initialized; reading automatic local `x` before assignment is unsafe |
| Java / C# local | `int x, y = 10;` | Only `y` is initialized; the compiler rejects reading `x` before assignment |
| Go | `var x, y int = 10, 10` | Initializer values are matched to names by position |
| Python | `x, y = 10, 10` | Two values are unpacked into two assignment targets |

The C/Java-shaped declaration is especially easy to misread as “both are
10.” This Java example proves that the initializer belongs only to `y`:

```java
int x, y = 10;
System.out.println(y);
// System.out.println(x); // compile error: x may not have been initialized
```

Output:

```text
10
```

The declaration itself is legal; Java reports the problem only when code
tries to read `x`. C# locals behave similarly. For C and C++, an uninitialized
automatic local has an indeterminate value, so reading it does not have a
reliable output. Static-storage variables and fields follow different default-
initialization rules, another reason not to import this syntax into PYS.

Go and Python avoid that exact “only the last name” interpretation, but with
different constructs:

```go
var x, y int = 10, 10
fmt.Println(x, y)
```

Go output:

```text
10 10
```

```python
x, y = 10, 10
print(x, y)
```

Python output:

```text
10 10
```

Go declares names against initializer values; Python performs assignment with
iterable unpacking and has no PYS-style type declaration here. Similar commas
do not create one transferable rule.

PYS therefore rejects both `int x, y = 10` and the clearer
`int x = 10, y = 10`. The latter saves a line but adds no expressive power and
would break the consistent one-name shape of `var`, `fix`, `const`, fields,
`shared`, and `atomic`. Function parameter lists are different: every
parameter already has its own type-and-name position, with no initializer to
attach to the wrong name.

Casing you already use:

- Types: `PascalCase` → same in C#/Java.
- Methods / locals: `camelCase` → same.
- Constants: `SCREAMING_SNAKE_CASE` → common in Java; C# often
  `PascalCase` for `const` — check the house style.

### Exercise

> Rewrite a small PYS snippet (`fix string name = "Ada"` plus a print) as
> C# and as Java on paper, including the entry-point wrapper.

---

[Previous: Packages and source roots](chapter_7_3.md) · [Next: Classes, interfaces, and members](chapter_8_2.md)
