# 8.1. tasks, task, and await

A `tasks { … }` block starts concurrent units and **waits** until they all
finish before the code after the block runs.

<figure class="concept-diagram" role="img" aria-label="Two tasks run then join before both finished prints">
  <div class="diagram-threads">
    <div class="diagram-box"><strong>task A</strong><span>print "A"</span></div>
    <div class="diagram-box diagram-shared"><strong>tasks { }</strong><span>waits for all</span></div>
    <div class="diagram-box"><strong>task B</strong><span>print "B"</span></div>
  </div>
  <div class="diagram-stack" style="margin-top:0.75rem">
    <div class="diagram-arrow" aria-hidden="true">↓ join</div>
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>both finished</strong>
      <span>runs only after A and B</span>
    </div>
  </div>
  <figcaption>
    Print order of A and B may vary; the line after the block always waits
    for the join.
  </figcaption>
</figure>

```pys
tasks {
    task {
        print("A")
    }
    task {
        print("B")
    }
}
print("both finished")
```

Output:

```text
A
B
both finished
```

*(Task print order may vary; both lines appear before `both finished`.)*



Named tasks can return values; `await` waits for them (**only inside a
`task`**):

```pys
tasks {
    task add(int a, int b) {
        return a + b
    }
    task {
        int s = await add(10, 32)
        print(s)
    }
}
```

Output:

```text
42
```


## Await edges form a DAG

`await` draws an arrow: “this task needs that task’s result first.” Those
arrows must form a **DAG** (directed acyclic graph) — a one-way pipeline,
never a loop.

<figure class="concept-diagram" role="img" aria-label="Await pipeline stepOne to stepTwo to print as a DAG">
  <div class="diagram-stack">
    <div class="diagram-box"><strong>stepOne</strong><span>returns 2</span></div>
    <div class="diagram-arrow" aria-hidden="true">↓ await</div>
    <div class="diagram-box"><strong>stepTwo</strong><span>x + 3</span></div>
    <div class="diagram-arrow" aria-hidden="true">↓ await</div>
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>print(y)</strong>
      <span>5</span>
    </div>
  </div>
  <figcaption>
    One-way arrows only — a cycle would never finish, so PYS rejects it.
  </figcaption>
</figure>

Valid (a pipeline):

```pys
tasks {
    task stepOne() {
        return 2
    }
    task stepTwo() {
        int x = await stepOne()
        return x + 3
    }
    task {
        int y = await stepTwo()
        print(y)
    }
}
```

Output:

```text
5
```


Illegal (a cycle) — rejected at transpile time (`pys.await-cycle`):

```text
task a awaits b
task b awaits a
```

Neither task could ever finish; PYS refuses to emit that program. Deeper
notes: [`docs/CONCURRENCY.md`](../docs/CONCURRENCY.md).

Prefer **parameters** to feed data into tasks instead of grabbing outer
locals.

### Exercise

> Inside one `tasks` block, run two tasks that each print a different
> word, then print `"done"` after the block.

---

[Previous: Passing functions around](chapter_5_3_passing_functions.md) · [Next: shared state](chapter_6_2_shared_state.md)
