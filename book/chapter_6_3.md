# 7.3. atomic updates

`atomic` marks a cell whose `+=` / `-=` / `++` / `--` updates are
**indivisible**. It also implies shared capture for tasks.

> **Sidebar — `get` / `compareAndSet`**
>
> Beyond `+=`, atomics expose `get()` and `compareAndSet(expected, new)`.
> Those deserve their own walkthrough — see
> [`docs/CONCURRENCY.md`](../docs/CONCURRENCY.md) when you need them.

```pys
atomic int counter = 0

tasks {
    task {
        counter += 1
    }
    task {
        counter += 1
    }
}
print(counter)
```

Reach for `atomic` when many tasks bump the same counter; reach for
`await` pipelines when you can avoid shared mutation entirely.

### Exercise

> Start `atomic int total = 0`. In a `tasks` block, run three tasks that
> each do `total += 10`. Print `total` afterward (expect `30`).

---

[Previous: shared state](chapter_6_2.md) · [Next: Lambdas and capture rules](chapter_6_4.md)
