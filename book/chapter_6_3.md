# 7.3. atomic updates

`atomic` marks a cell whose `+=` / `-=` / `++` / `--` (and helpers like
`get` / `compareAndSet`) are **indivisible**. It also implies shared
capture.

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
