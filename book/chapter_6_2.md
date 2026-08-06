# 8.2. shared state

Outer locals are **read-only** inside a task unless marked `shared` (or
`atomic`). `shared` is **visibility** for mutation across tasks — it does
not by itself make updates race-free.

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

[Previous: tasks, task, and await](chapter_6_1.md) · [Next: atomic updates](chapter_6_3.md)
