# 8.3. atomic updates

`atomic` marks a cell whose `+=` / `-=` / `++` / `--` updates are
**indivisible**. It also implies shared capture for tasks.

<figure class="concept-diagram" role="img" aria-label="shared read-modify-write can race versus atomic indivisible plus-equals">
  <div class="diagram-grid-2">
    <div class="diagram-box is-warn" style="border:2px solid #8a6d3b;background:#f5ecd8;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>shared</strong>
      <span>read · add · write can interleave</span>
    </div>
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>atomic</strong>
      <span>+= is one indivisible step</span>
    </div>
  </div>
  <figcaption>
    Visibility alone is not enough — atomics make the update itself safe.
  </figcaption>
</figure>

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
