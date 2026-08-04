# 5.6. Choosing the right construct

Use this as a pocket card:

| Need | Prefer |
|------|--------|
| Behavior + inheritance + identity by reference | `class` |
| “Can do these methods” as a type | `interface` |
| Shared base code + holes to fill | `abstract class` |
| Mix in reusable methods (not a type) | `trait` (`uses`) |
| Small value bag, no VO ceremony | `struct` |
| Immutable interchangeable value (money, color) | `data` |
| Row with a stable key (customer id) | `entity` |

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

[Previous: Structs, data, and entity](chapter_4_5.md) · [Next: Functions that return values](chapter_5_1.md)
