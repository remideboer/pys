# 5.2. Interfaces

An **interface** is a contract: method names and signatures, no fields, no
bodies. Implementing classes must provide matching **public** methods.
Omit access modifiers on the interface signatures — they are always public
and abstract.

```pys
interface Greeter {
    greet(string name)
}

class ConsoleGreeter implements Greeter {
    public greet(string name) {
        print("Hello, " + name)
    }
}

Greeter g = ConsoleGreeter()
g.greet("Ada")
```

Output:

```text
Hello, Ada
```


`Greeter` is a **type**: you can declare variables of that type and store
any implementing object.

### Exercise

> Add `farewell(string name)` to the interface and implement it on
> `ConsoleGreeter`.

---

[Previous: Classes](chapter_4_1.md) · [Next: Abstract classes](chapter_4_3.md)
