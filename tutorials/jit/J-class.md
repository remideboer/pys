# JIT — Classes and interfaces

## Forms

```pys
package interface Drivable {
    start()
}

package class Cart implements Drivable {
    private string id
    public Cart(string id) {
        this.id = id
    }
    public start() {
        print("cart #s{this.id}")
    }
}

package class BigCart inherits Cart {
    public BigCart(string id) {
        super(id)
    }
}
```

## Rules

1. Class members need an access modifier (`public` / `private` / `protected` / `module`)  
2. Interface method signatures have **no** access modifier (always public/abstract)  
3. No `function` keyword on methods — `public name(args) { … }` on classes  
4. `inherits` one class; `implements` one or more interfaces  
5. `this` / `super` for current / parent  

Bag of fields with no behavior → use a [struct](J-struct.md), not a class.

Examples: [`examples/classes.pys`](../../examples/classes.pys) (classes in general),
[`examples/interfaces.pys`](../../examples/interfaces.pys) (contracts / implements).

Model: [S5](../supportive/S5-objects-as-responsibility.md)
