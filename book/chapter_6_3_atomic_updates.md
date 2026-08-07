# 8.3. atomic updates

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

Output:

```text
2
```

*(Concurrent task print order may vary.)*



Reach for `atomic` when many tasks bump the same counter; reach for
`await` pipelines when you can avoid shared mutation entirely.

> **Sidebar — `shared` is not enough**
>
> `shared` only makes cross-task mutation *visible*. It does not make
> `counter += 1` race-free — the same confusion as Java `volatile` (visibility)
> versus a true atomic counter. Use `atomic` when the update itself must be
> indivisible.

### Exercise

> Start `atomic int total = 0`. In a `tasks` block, run three tasks that
> each do `total += 10`. Print `total` afterward (expect `30`).

---

[Previous: shared state](chapter_6_2_shared_state.md) · [Next: Lambdas and capture rules](chapter_6_4_lambdas_capture.md)
