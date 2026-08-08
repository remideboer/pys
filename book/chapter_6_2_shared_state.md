# 8.2. shared state

Outer locals are **read-only** inside a task unless marked `shared` (or
`atomic`). `shared` is **visibility** for mutation across tasks — it does
not by itself make updates race-free.

<figure class="concept-diagram" role="img" aria-label="Two tasks both reach the same shared hits cell">
  <div class="diagram-threads">
    <div class="diagram-box"><strong>task</strong><span>hits = hits + 1</span></div>
    <div class="diagram-box diagram-shared"><strong>shared hits</strong><span>one mutable cell</span></div>
    <div class="diagram-box"><strong>task</strong><span>hits = hits + 1</span></div>
  </div>
  <figcaption>
    Both flows can see and write the same name — visibility granted; races
    still possible without atomics.
  </figcaption>
</figure>

```pys
shared int hits = 0

tasks {
    task {
        hits = hits + 1
    }
    task {
        hits = hits + 1
    }
}
print(hits)
```

Output:

```text
2
```

*(Concurrent task print order may vary.)*



Use `shared` when two tasks must update the same outer name and you accept
responsibility for the interaction — or prefer returning values with
`await` instead of sharing.

### Exercise

> Have two tasks each set a `shared string lastWriter` to their own label.
> Print `lastWriter` after the block (the winner is not determined — that
> is the lesson).

---

[Previous: tasks, task, and await](chapter_6_1_tasks_await.md) · [Next: atomic updates](chapter_6_3_atomic_updates.md)
