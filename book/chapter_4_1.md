# 5.1. Classes and member order

A **class** is a blueprint for objects with fields, a constructor, and
methods.

```pys
class Counter {
    public const int DEFAULT_STEP = 1
    private fix string label
    private int value

    public Counter(string label) {
        this.label = label
        this.value = 0
    }

    public void bump() {
        this.value = this.value + Counter.DEFAULT_STEP
    }

    public int getValue() {
        return this.value
    }
}

Counter c = Counter("demo")
c.bump()
print(c.getValue())
```

Output:

```text
1
```


## Why member order is enforced

Inside a class body, PYS requires this **kind** order:

1. `const` fields  
2. `fix` fields  
3. mutable fields  
4. constructors  
5. methods  

Visibility (`public` / `private` / …) may vary within a section, but you
cannot put a method above a field or a mutable field above a `fix` field.
If the order is wrong, you get a **parse error**, not a polite lint.

Why? Good practice in C# and Java is the same order; PYS makes the habit
impossible to skip so you learn it once.

Constructor name equals the class name. Use `this.field` for members.

### Exercise

> Add `public string getLabel()` to `Counter` (still after the constructor).
> Intentionally move a method above a field and read the error.

---

[Previous: Enums and switch](chapter_3_5.md) · [Next: Interfaces](chapter_4_2.md)
