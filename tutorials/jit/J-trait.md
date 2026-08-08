# JIT — Traits

## Form

```pys
trait Printable {
    requires string name

    string label() {
        return "Item: " + this.name
    }
}

class Product uses Printable {
    private string name

    public constructor(string name) {
        this.name = name
    }
}

# Remap a requires name onto a differently named host field:
class CatalogItem uses Printable(name: title) {
    private string title

    public constructor(string title) {
        this.title = title
    }
}
```

## Rules

1. Traits are **composition**, not types — use `uses`, never `implements Trait`
2. `requires` lists host fields/methods the trait needs; `this` reads them
3. Optional remap: `uses Trait(req: hostMember)` — only for `requires`, never
   for the trait’s own method names
4. Multiple traits: `uses A, B` (each may carry its own remap list)
5. Name collision → class must override; call `A.method(this)` / `B.method(this)` to choose
6. Header order on classes: `inherits` → `uses` → `implements`
7. **`requires` before methods** — [J-member-order](J-member-order.md)
