# 7.4. Lambdas and capture rules

Lambdas capture outer names **by value** when created. Captured names are
read-only unless they were declared `shared` or `atomic`.

Loop variables are immutable **per iteration** — each lambda created in a
loop gets that iteration’s value (no Python late-binding surprise).

```pys
list<lambda<int, int>> adders = []
loop (int i = 0, i < 3, i++) {
    adders.append((int x) => x + i)
}
print(adders[0](10))
print(adders[1](10))
print(adders[2](10))
```

Output:

```text
10
11
12
```


Together with `tasks`, this keeps concurrent and higher-order code
predictable: say when mutation crosses a boundary (`shared` / `atomic`),
otherwise treat captures as snapshots.

### Exercise

> Build three `lambda<string, string>` values that prefix `"A: "`, `"B: "`,
> and `"C: "` respectively, store them in a list, and call each on
> `"ok"`.

---

[Previous: atomic updates](chapter_6_3.md) · [Next: Session 6](chapter_7.md)
