# 6.3. Passing functions around

Because lambdas are values, you can pass them into helpers:

```pys
function int apply(int value, lambda<int, int> fn) {
    return fn(value)
}

int doubled = apply(5, n => n * 2)
print(doubled)
```

Output:

```text
10
```


Prefer named functions when the logic is non-trivial or reused; prefer
lambdas for short adapters at the call site.

> **Sidebar — `.loop` on arrays**
>
> `numbers.loop(print)` means “call `print` once per element” (it maps to
> Python’s `list(map(...))`). Use an ordinary `loop (… in …)` when you need
> an `if`, `break`, or more than one statement per item — see
> [Loops](chapter_3_2.md).

```pys
int[] numbers = [1, 2, 3]
numbers.loop(print)
```

Output:

```text
1
2
3
```


### Exercise

> Write `function int applyTwice(int value, lambda<int, int> fn)` that
> applies `fn` twice. Call it with `n => n + 1` starting from `0`.

---

[Previous: Lambdas](chapter_5_2.md) · [Next: Session 5](chapter_6.md)
