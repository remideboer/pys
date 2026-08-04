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
