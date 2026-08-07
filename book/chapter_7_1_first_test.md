# 9.1. Writing a first test

Suppose production code offers a pure function:

```pys
# billing.pys
package function int addCents(int balance, int delta) {
    return balance + delta
}
```

*Compiles; no output.*



A test in the same package folder (or mirrored under `tests/` with source
roots):

```pys
import addCents from billing

int got = addCents(100, 50)
if (got != 150) {
    print("FAIL: expected 150")
} else {
    print("OK")
}
```

*With `billing.pys` in the same folder, running this file prints:*

```text
OK
```



Run with `python -m transpiler run …`. A green print is a humble start;
the important part is **repeatability**.

Do not reach into `private` fields from tests — if you need a value,
expose a query method on the public/`package` API instead.

### Exercise

> Write `package function int clamp(int n, int lo, int hi)` and a test file
> that checks one in-range and one out-of-range case.

---

[Previous: Lambdas and capture rules](chapter_6_4_lambdas_capture.md) · [Next: Better PYS with TDD](chapter_7_2_tdd.md)
