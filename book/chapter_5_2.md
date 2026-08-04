# 6.2. Lambdas

A lambda type lists parameter types and then the return type:
`lambda<int, bool>` means “one `int` in, `bool` out”.

```pys
lambda<int, bool> isEven = n => n % 2 == 0
print(isEven(4))
print(isEven(5))

lambda<int, int, int> safeDivide = (int a, int b) => {
    if (b == 0) {
        return 0
    }
    return a / b
}
print(safeDivide(10, 2))
```

Forms: `n => expr`, `(params) => expr`, `(params) => { … }`, `() => …`.

Captures are **by value** at creation and read-only unless the outer name
is `shared` or `atomic` — concurrency keywords taught in
[shared state](chapter_6_2.md) and [atomic updates](chapter_6_3.md). Until
then, treat captured names as snapshots you can read, not reassign.

### Exercise

> Write `lambda<string, string> shout` that adds `"!"` and call it on
> `"hey"`.

---

[Previous: Functions that return values](chapter_5_1.md) · [Next: Passing functions around](chapter_5_3.md)
