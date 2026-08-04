# 5.4. Traits

A **trait** is reusable behavior mixed into a class with `uses`. It is
**not** a type — you cannot write `Printable p = …` or `implements Printable`.

Host state is declared with `requires` and accessed via `this`. All
`requires` come before methods in the trait body.

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

Product p = Product("Mug")
print(p.label())
```

Output:

```text
Item: Mug
```


## When two traits collide

If two traits define the same method name, the host class **must** override
it. Call `TraitName.method(this)` to pick a side — or combine both:

```pys
trait Loud {
    string greet() {
        return "HEY"
    }
}

trait Soft {
    string greet() {
        return "hi"
    }
}

class Greeter uses Loud, Soft {
    public Greeter() {
    }

    public string greet() {
        return Loud.greet(this) + "/" + Soft.greet(this)
    }
}

Greeter g = Greeter()
print(g.greet())
```

Output:

```text
HEY/hi
```


Without the override, the transpile fails: two traits both want to own
`greet`. The override is where *you* decide the story.

### Exercise

> Add `requires int priceCents` and a method `string priceTag()` that
> returns a short string including the price. Supply the field on
> `Product`.

---

[Previous: Abstract classes](chapter_4_3.md) · [Next: Structs, data, and entity](chapter_4_5.md)
