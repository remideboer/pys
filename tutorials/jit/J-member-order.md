# JIT — Member and import ordering

## Forms (canonical)

```pys
import math
import greet from toolbox

package class Cart {
    public const int MAX = 10
    private fix string id
    private int count

    public constructor(string id) {
        this.id = id
        this.count = 0
    }

    public bump() {
        this.count = this.count + 1
    }
}

struct Hit {
    fix string type
    int amount
}

trait Printable {
    requires string name
    string label() {
        return this.name
    }
}

entity Customer identity(customerId) {
    private fix int customerId
    public string name

    public constructor(int customerId, string name) {
        this.customerId = customerId
        this.name = name
    }
}
```

## Order tables

| Body | Kind order |
|------|------------|
| File | All `import` / `from … import` → then code |
| `class` | `const` → `fix` → mutable fields → constructors → methods (`abstract` too) |
| `struct` | `fix` → mutable |
| `trait` | `requires` → methods |
| `entity` | Identity fields → other `fix` → mutable → constructors → methods |

Visibility (`public` / `private` / …) is **not** ordered within a section.

## Common errors → fix

| Message cue | Fix |
|-------------|-----|
| Import … after other code | Move every import to the top |
| Method … before the fields/constructor section | Move methods below constructors |
| Field … after a constructor | Move fields above constructors |
| Constant … after non-const | Move `const` fields first |
| Fix field … after mutable | Move `fix` fields above mutable |
| … before trait … `requires` | Put all `requires` above methods |
| … before identity field | Put `identity(...)` fields first |

## Not ordered

Items inside `tasks { }` — dependency order comes from `await`, not from
source position of `task` lines.

Why this is a transferable habit (other langs won’t reject): [S7](../supportive/S7-order-as-habit.md).  
Practice: [P-member-order](../practice/P-member-order.md).  
Language: [`LANGUAGE.md`](../../docs/LANGUAGE.md#enforced-member-ordering).
