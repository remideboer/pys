# Session 3 — Objects and composition

Until now values were mostly numbers, strings, and collections. **Objects**
bundle data with behavior — and PYS gives you several shapes on purpose.

1. [Classes and member order](chapter_4_1.md)
2. [Interfaces](chapter_4_2.md)
3. [Abstract classes](chapter_4_3.md)
4. [Traits](chapter_4_4.md)
5. [Structs, data, and entity](chapter_4_5.md)
6. [Choosing the right construct](chapter_4_6.md)

Keep this comparison nearby (from the language docs):

| Construct | Equality | Identity | Inheritance |
|-----------|----------|----------|-------------|
| `struct` | Field-wise | No | No |
| `data` | All fields (generated) | No | No |
| `entity` | Identity fields only | `identity(...)` | Entity-only |
| `class` | Reference (manual) | Implicit | Yes |

And for behavior reuse:

| Construct | Role |
|-----------|------|
| `interface` | Contract of method signatures only (a type) |
| `abstract class` | Partial implementation + abstract methods (a type) |
| `trait` | Reusable behavior mixed into a class with `uses` (**not** a type) |

---

[Previous: Enums and switch](chapter_3_5.md) · [Next: Classes and member order](chapter_4_1.md)
