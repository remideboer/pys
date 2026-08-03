# JIT — Abstract classes

## Form

```pys
abstract class Shape {
    public Shape() {}

    public abstract float area()
}

class Box inherits Shape {
    private float w
    private float h

    public Box(float w, float h) {
        super()
        this.w = w
        this.h = h
    }

    public float area() {
        return this.w * this.h
    }
}
```

## Rules

1. `abstract class` and `sealed` are mutually exclusive
2. Abstract methods: `public abstract R name(...)` — **no** `{` body
3. Concrete subclasses must implement every inherited abstract method
4. Do not write `Shape()`; construct a concrete subclass (ctors may call `super(...)`)
5. Abstract classes **are** types: `Shape s = Box(1.0, 2.0)` is allowed
6. `void` methods must not `return expr`
7. Full sample: [`examples/abstract_classes.pys`](../../examples/abstract_classes.pys)
