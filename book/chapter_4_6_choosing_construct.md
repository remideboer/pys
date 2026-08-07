# 5.7. Choosing the right construct

Use this as a pocket card:

| Need | Prefer |
|------|--------|
| Behavior + inheritance + identity by reference | `class` |
| “Can do these methods” as a type | `interface` |
| Shared base code + holes to fill | `abstract class` |
| Mix in reusable methods (not a type) | `trait` (`uses`) |
| Small field bag without VO rules | `struct` |
| Immutable interchangeable value (money, color) | `data` |
| Row with a stable key (customer id) | `entity` |

> **Sidebar — what “VO ceremony” meant**
>
> In [Structs, data, and entity](chapter_4_5_structs_data_entity.md), **VO** means *value object*
> and **ceremony** means the fixed contract `data` gives you: all fields
> immutable, equality over every field, no methods/inheritance. Choosing
> `struct` skips that contract — useful for a simple bag of fields; choose
> `data` when you *want* those VO rules. Frameworks in other languages often
> leave entity identity to annotations (`@Id`, `[Key]`); PYS makes
> `identity(...)` a checked language fact instead — see
> [`docs/DATA_ENTITY.md`](../docs/DATA_ENTITY.md) when you want the longer story.

**interface vs trait vs abstract class (again):**

- **interface** — contract only; is a type.
- **trait** — behavior mixin; **not** a type; `requires` host state.
- **abstract class** — partial class; is a type; may have fields.

When unsure, start with `class` or `data` and refactor when the equality
story becomes clear — Session 6’s tests make that safer.

### Exercise

> Pick one real-world idea (a library book, a bank transfer, a traffic
> ticket). Write three sentences: which construct you would use and why,
> naming equality and behavior.

---

[Previous: Structs, data, and entity](chapter_4_5_structs_data_entity.md) · [Next: Functions that return values](chapter_5_1_functions_return.md)
