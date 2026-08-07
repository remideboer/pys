# Session 3 — Objects and composition

Until now values were mostly numbers, strings, and collections. **Objects**
bundle data with behavior — and PYS gives you several shapes on purpose.

1. [Classes and member order](chapter_4_1a_classes.md)
2. [Inheritance and subclasses](chapter_4_1b_inheriting_classes.md)
3. [Interfaces](chapter_4_2_interfaces.md)
4. [Abstract classes](chapter_4_3_abstract_classes.md)
5. [Traits](chapter_4_4_traits.md)
6. [Structs, data, and entity](chapter_4_5_structs_data_entity.md)
7. [Choosing the right construct](chapter_4_6_choosing_construct.md)

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

[Previous: Enums and switch](chapter_3_5_enums_and_switch.md) · [Next: Classes and member order](chapter_4_1a_classes.md)
