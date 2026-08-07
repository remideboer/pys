# 10.3. Control flow and collections

| PYS | C# | Java |
|-----|----|------|
| `if (c) { }` | `if (c) { }` | `if (c) { }` |
| `unless (c)` | `if (!c)` | `if (!c)` |
| `loop (int i=0; i<n; i++)` | `for` | `for` |
| `loop (x in xs)` | `foreach` | enhanced `for` |
| `switch` (no fall-through by default) | `switch` (be careful with fall-through) | `switch` / switch expressions |
| `list<T>` | `List<T>` | `List<T>` |
| `dict<K,V>` | `Dictionary<K,V>` | `Map<K,V>` |
| `T[]` | `T[]` | `T[]` |
| `enum` | `enum` | `enum` |

String interpolation: PYS `{x}` / `#i{x}` vs C# `$"{x}"` vs Java
`"%s".formatted(...)` / string templates (newer).

## Transferring loops without copying every feature

Java and C++ can initialize and update several variables in one `for` header:

```java
for (int left = 0, right = 4; left < right; left++, right--) {
    System.out.println(left + ", " + right);
}
```

Output:

```text
0, 4
1, 3
```

Those languages do not verify that both variables remain synchronized: one
step can change, or the body can update one variable again. PYS therefore
transfers the **algorithm**, not this permissive header feature:

```pys
int left = 0
int right = 4

loop (left < right) {
    print("#i{left}, #i{right}")
    left++
    right--
}
```

Output:

```text
0, 4
1, 3
```

Use PYS's C-style form for one protected counter. Use while-style `loop` for
several changing values. When moving to C# or Java, you may encounter a compact
multi-variable `for`, but you do not need it to express the algorithm.

### Exercise

> Translate a PYS foreach over `list<string>` into both C# `foreach` and
> Java enhanced for-loop on paper.

---

[Previous: Classes and interfaces](chapter_8_2_classes_interfaces.md) · [Next: What has no direct twin](chapter_8_4_no_direct_twin.md)
