# 6.1. Functions that return values

Return type sits after `function`:

```pys
function int multiply(int a, int b) {
    return a * b
}

function void logSum(int a, int b) {
    print(multiply(a, b))
}

logSum(6, 7)
```

Output:

```text
42
```


Visibility (`package` / `global`) controls imports — see the basics
structuring chapter.

> **Library decorators.** You may write `@expr` above a `function`, `class`, or
> method to apply a **library** callable (for example a web framework route).
> Do not invent new PYS features with `@` — missing language ideas get real
> keywords instead. See [LANGUAGE.md](../docs/LANGUAGE.md) and ADR-026.

### Exercise

> Write `function bool isEven(int n)` and print the result for `n = 4` and
> `n = 5`.

---

[Previous: Choosing the right construct](chapter_4_6_choosing_construct.md) · [Next: Lambdas](chapter_5_2_lambdas.md)
