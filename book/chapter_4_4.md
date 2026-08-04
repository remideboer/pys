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

If two traits define the same method name, the class must override it and
can disambiguate with `TraitName.method(this)`.

### Exercise

> Add `requires int priceCents` and a method `string priceTag()` that
> returns a short string including the price. Supply the field on
> `Product`.

---

[Previous: Abstract classes](chapter_4_3.md) · [Next: Structs, data, and entity](chapter_4_5.md)
