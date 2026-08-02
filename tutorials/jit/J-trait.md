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

    public Product(string name) {
        this.name = name
    }
}
```

## Rules

1. Traits are **composition**, not types — use `uses`, never `implements Trait`
2. `requires` lists host fields/methods the trait needs; `this` reads them
3. Multiple traits: `uses A, B` (order does not matter when names do not collide)
4. Name collision → class must override; call `A.method(this)` / `B.method(this)` to choose
5. Header order on classes: `inherits` → `uses` → `implements`
