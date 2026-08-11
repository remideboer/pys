# 10.2. Classes, interfaces, and members

| PYS | C# | Java |
|-----|----|------|
| `class Foo` | `class Foo` | `class Foo` |
| `inherits Base` | `: Base` | `extends Base` |
| `implements I` | `: I` (same list) | `implements I` |
| `uses Trait` | (no direct twin — mixins rare; prefer interfaces + defaults) | (no direct twin) |
| `abstract class` | `abstract class` | `abstract class` |
| `interface` | `interface` | `interface` |
| `public` / `private` / `protected` / `module` | same idea (`internal` ≈ `module`) | same idea (package-private ≈ `module`) |
| Omitted member access | defaults to `module` (same-file) | package-private when omitted (Java) / explicit preferred (C#) |
| `package` (type export) | `internal` (assembly) | package-private (default) |
| Constructor declaration `Foo(...)` | `Foo(...)` — same idea | `Foo(...)` — same idea |
| Create instance | `Foo(...)` (**no** `new`) | `new Foo(...)` | `new Foo(...)` |
| `this` / `super` | `this` / `base` | `this` / `super` |
| Enforced member order | Style / analyzers | Style / Checkstyle |

Member order in PYS is **parse-enforced**. In C#/Java, teams rely on
analyzers and code review — you already have the habit.

`data` ≈ immutable record / value object patterns.  
`entity` ≈ identity equality by key (DDD entity).  
`struct` in PYS is a value type without methods — closer to a simple C#
`struct` or a Java record used only as data, not to C#’s full feature set.

### Exercise

> Take the `Counter` class from Session 3 and sketch the C# and Java
> versions, keeping fields before constructors before methods.

---

[Previous: Types and declarations](chapter_8_1_types_declarations.md) · [Next: Control flow and collections](chapter_8_3_control_flow_collections.md)
