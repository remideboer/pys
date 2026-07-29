# JIT — Classes and interfaces

## Forms

```pys
package interface Drivable {
    public start()
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
2. No `function` keyword on methods — `public name(args) { … }`  
3. `inherits` one class; `implements` one or more interfaces  
4. `this` / `super` for current / parent  

Model: [S5](../supportive/S5-objects-as-responsibility.md)
