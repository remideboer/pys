# 7.1. tasks, task, and await

A `tasks { … }` block starts concurrent units and **waits** until they all
finish before the code after the block runs.

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

## Await edges form a DAG

`await` draws an arrow: “this task needs that task’s result first.” Those
arrows must form a **DAG** (directed acyclic graph) — a one-way pipeline,
never a loop.

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

[Previous: Session 5](chapter_6.md) · [Next: shared state](chapter_6_2.md)
