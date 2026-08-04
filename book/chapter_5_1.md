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

### Exercise

> Write `function bool isEven(int n)` and print the result for `n = 4` and
> `n = 5`.

---

[Previous: Choosing the right construct](chapter_4_6.md) · [Next: Lambdas](chapter_5_2.md)
