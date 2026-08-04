# 9.3. Control flow and collections

| PYS | C# | Java |
|-----|----|------|
| `if (c) { }` | `if (c) { }` | `if (c) { }` |
| `unless (c)` | `if (!c)` | `if (!c)` |
| `loop (i=0, i<n, i++)` | `for` | `for` |
| `loop (x in xs)` | `foreach` | enhanced `for` |
| `switch` (no fall-through by default) | `switch` (be careful with fall-through) | `switch` / switch expressions |
| `list<T>` | `List<T>` | `List<T>` |
| `dict<K,V>` | `Dictionary<K,V>` | `Map<K,V>` |
| `T[]` | `T[]` | `T[]` |
| `enum` | `enum` | `enum` |

String interpolation: PYS `{x}` / `#i{x}` vs C# `$"{x}"` vs Java
`"%s".formatted(...)` / string templates (newer).

### Exercise

> Translate a PYS foreach over `list<string>` into both C# `foreach` and
> Java enhanced for-loop on paper.

---

[Previous: Classes and interfaces](chapter_8_2.md) · [Next: What has no direct twin](chapter_8_4.md)
