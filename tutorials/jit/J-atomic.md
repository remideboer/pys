# JIT — Atomic

Lead with the race, then the fix.

## Visibility vs safety

| Qualifier | Meaning |
|-----------|---------|
| `shared` | Mutation across tasks/lambdas is **declared** (visible) — not race-free |
| `atomic` | Implies shared for capture **and** indivisible `+=` / `-=` / `++` / `--` |

```pys
# Teaching race: unlocked read + locked set can lose updates
shared int shared_counter = 0
tasks {
    task {
        loop (int i = 0; i < 200; i++) {
            shared_counter = shared_counter + 1
        }
    }
    task {
        loop (int i = 0; i < 200; i++) {
            shared_counter = shared_counter + 1
        }
    }
}
# Final value often < 400 — classic lost update

atomic int counter = 0
tasks {
    task {
        loop (int i = 0; i < 1000; i++) {
            counter += 1
        }
    }
    task {
        loop (int i = 0; i < 1000; i++) {
            counter += 1
        }
    }
}
print(counter)  # always 2000
```

## Ops

| Allowed | Rejected |
|---------|----------|
| `+=` `-=` `++` `--` plain `=` | `*=` `/=` `%=` |
| `get()` / `compareAndSet(expected, new)` | `atomic shared` / `shared atomic` |

Primitives: `int`, `int16`, `int32`, `int64`, `dword`, `bool`.

```pys
atomic int highScore = 0
bool done = false
loop (!done) {
    int current = highScore.get()
    if (candidate <= current) {
        done = true
    } else {
        done = highScore.compareAndSet(current, candidate)
    }
}
```

Full sample: [`examples/atomic.pys`](../../examples/atomic.pys) · guide: [`CONCURRENCY.md`](../../docs/CONCURRENCY.md).
