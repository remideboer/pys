# JIT — Lambdas

## Forms

```pys
lambda<int, bool> isEven = n => n % 2 == 0
print(isEven(4))

function int apply(int x, lambda<int, int> fn) {
    return fn(x)
}
print(apply(5, n => n * 2))

lambda<int, int, int> safeDivide = (int a, int b) => {
    if (b == 0) {
        return 0
    }
    return a / b
}
```

## Capture (why this rule exists)

| Language | Pitfall | PYS |
|----------|---------|-----|
| Python | Closures re-read the variable at **call** time | Capture **value** at creation |
| JS (`var` loop) | One shared binding → `3,3,3` | Loop vars immutable per iteration |
| Java | Effectively final only | `shared` is the explicit escape hatch |

```pys
list<lambda<int>> callbacks = []
loop (int i in [0, 1, 2]) {
    callbacks = callbacks + [() => print(i)]
}
# Invoking callbacks prints 0, 1, 2 — not 2, 2, 2
```

Mutating a captured name requires `shared` or `atomic`:

```pys
shared int counter = 0
xs.loop(n => { counter += n; return n })

atomic int hits = 0
xs.loop(n => { hits += 1; return n })
```

`shared` makes the mutation **visible**; `atomic` also makes `+=` **indivisible**
under concurrent tasks ([J-atomic](J-atomic.md)).

## Rules

1. `lambda<P…, R>` — last type is return; `lambda<R>` = no parameters  
2. Body: expression (implicit return) or `{ … }` with `return`  
3. Captures read-only unless `shared` or `atomic`  
4. `arr.loop(fn)` → map, not filter  

Full sample: [`examples/lambdas.pys`](../../examples/lambdas.pys).
