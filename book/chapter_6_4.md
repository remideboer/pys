# 8.4. Lambdas and capture rules

Lambdas capture outer names **by value** when created. Captured names are
read-only unless they were declared `shared` or `atomic`.

Loop variables are immutable **per iteration** — each lambda created in a
loop gets that iteration’s value.

> **Sidebar — why this rule exists**
>
> In Python, a list of `lambda: i` built in a loop often prints the *last*
> `i` for every call (late binding). Older JavaScript `var` loops and early
> C# `foreach` had the same “one shared binding” trap. PYS snapshots the
> value at creation and keeps loop binders per-iteration so that class of
> bug cannot compile into your program.

```pys
list<lambda<int, int>> adders = []
loop (int i = 0; i < 3; i++) {
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

[Previous: atomic updates](chapter_6_3.md) · [Next: Writing a first test](chapter_7_1.md)
