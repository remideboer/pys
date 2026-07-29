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
| `basics.pys` | Join, read-only capture, task-local vars |
| `awaiting.pys` | Named `await`, fan-in, chain |
| `shared_state.pys` | `shared` counters and accumulation |
| `pipeline.pys` | Sequential groups / stages |
| `more.pys` | Many workers, mixed patterns |
