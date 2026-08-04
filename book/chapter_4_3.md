# 5.3. Abstract classes

An **abstract class** is a nominal type that can hold shared fields and
concrete methods, plus `abstract` methods subclasses must implement. You
cannot construct it directly.

```pys
abstract class AbstractList {
    protected int size

    public AbstractList() {
        this.size = 0
    }

    public bool isEmpty() {
        return this.size == 0
    }

    public abstract string get(int index)
    public abstract void add(string item)
}

class ArrayListPys inherits AbstractList {
    public ArrayListPys() {
        super()
    }

    public string get(int index) {
        return ""
    }

    public void add(string item) {
        this.size = this.size + 1
    }
}

AbstractList list = ArrayListPys()
list.add("x")
print(list.isEmpty())
```

**vs interface:** abstract classes can carry fields and partial code.  
**vs trait:** abstract classes **are** types; traits are not.

### Exercise

> Add `public abstract int count()` and implement it on `ArrayListPys`
> using `this.size`.

---

[Previous: Interfaces](chapter_4_2.md) · [Next: Traits](chapter_4_4.md)
