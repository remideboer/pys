# 6.3. Passing functions around

Because lambdas are values, you can pass them into helpers:

```pys
function int apply(int value, lambda<int, int> fn) {
    return fn(value)
}

int doubled = apply(5, n => n * 2)
print(doubled)
```

Arrays and lists also offer functional-style iteration via `.loop`:

```pys
int[] numbers = [1, 2, 3]
numbers.loop(print)
```

Prefer named functions when the logic is non-trivial or reused; prefer
lambdas for short adapters at the call site.

### Exercise

> Write `function int applyTwice(int value, lambda<int, int> fn)` that
> applies `fn` twice. Call it with `n => n + 1` starting from `0`.

---

[Previous: Lambdas](chapter_5_2.md) · [Next: Session 5](chapter_6.md)
