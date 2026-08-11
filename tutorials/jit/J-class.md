# JIT — Classes and interfaces

## Forms

```pys
package interface Drivable {
    start()
}

package class Cart implements Drivable {
    private string id
    public constructor(string id) {
        this.id = id
    }
    public start() {
        print("cart #s{this.id}")
    }
}

package class BigCart inherits Cart {
    public constructor(string id) {
        super(id)
    }
}
```

## Rules

1. Class members may omit access: omitted ⇒ `module` (same-file); or write `public` / `private` / `protected` / `module`  
2. Interface method signatures have **no** access modifier (always public/abstract)  
3. No `function` keyword on methods — `public name(args) { … }` on classes  
4. `inherits` one class; `implements` one or more interfaces  
5. `this` / `super` for current / parent  
6. **Member order** (const → fix → fields → ctor → methods): [J-member-order](J-member-order.md)

Bag of fields with no behavior → use a [struct](J-struct.md), not a class.

Examples: [`examples/classes.pys`](../../examples/classes.pys) (classes in general),
[`examples/interfaces.pys`](../../examples/interfaces.pys) (contracts / implements).

Model: [S5](../supportive/S5-objects-as-responsibility.md)
