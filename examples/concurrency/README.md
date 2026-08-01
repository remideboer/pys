# Concurrency examples

Structured concurrency for PYS: `tasks`, `task`, `await`, `shared`.

**Documentation:** [`docs/CONCURRENCY.md`](../../docs/CONCURRENCY.md)

## Run

```bash
python -m transpiler run examples/concurrency/main.pys
```

## Layout

| File | Demos |
|------|--------|
| `main.pys` | Entry — runs every demo below |
| `interleaving.pys` | Two tasks print in a loop so output **mixes** (time slicing) |
| `basics.pys` | Join, **task parameters**, task-local vars |
| `awaiting.pys` | Named `await`, parameterized fan-in / chain / args |
| `shared_state.pys` | `shared` plus parameterized updates |
| `pipeline.pys` | Sequential groups / stages |
| `more.pys` | Many workers, mixed patterns |

## Input / output pattern

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

Prefer parameters for inputs; use `shared` only for intentional cross-task mutation.

Await edges inside one `tasks` group must form a DAG (no `a`↔`b` cycles) —
the transpiler rejects cycles. See `docs/CONCURRENCY.md` §2b.
