# PYS concurrency model

How `tasks`, `task`, `await`, and `shared` work together.

Runnable showcase:

```bash
python -m transpiler run examples/concurrency/main.pys
```

Formal grammar: [`language.ebnf`](language.ebnf) · language overview: [`LANGUAGE.md`](LANGUAGE.md)

---

## Mental model (four words)

| Keyword | Role |
|---------|------|
| **`task`** | One concurrent unit of work |
| **`tasks`** | A **group** of tasks that run together; leaving the block **waits for all** |
| **`await`** | **Wait until** this value is ready (usually a named task’s result) |
| **`shared`** | This variable **may be mutated** by more than one task |

There is no `async function` coloring and no `import threading`. Stay on these keywords.

**Memory:** tasks in the same process share the heap (like OS threads).  
`tasks { }` does **not** isolate memory — it only starts children and joins them.

---

## 1. `tasks` + `task` — run together, wait as a group

A bare `task` is illegal. Every `task` lives inside a `tasks` block.

```pys
tasks {
    task {
        print("A")
    }
    task {
        print("B")
    }
}
print("both finished")   # runs only after A and B complete
```

What happens:

1. Enter `tasks { … }`
2. Start every child `task` (order of *prints* is not guaranteed)
3. On the closing `}`, wait until every child has finished (or failed)
4. Continue with the next statement

That is **structured concurrency**: the block owns the children’s lifetime.

### Locals inside a task

Names declared *inside* a task are private to that task:

```pys
tasks {
    task {
        int x = 10
        print(x)
    }
}
```

---

## 2. `await` — wait until a result is ready

Give a task a **name** to get a handle. Sibling tasks can `await` that handle.

```pys
tasks {
    task answer {
        return 41
    }
    task {
        int n = await answer
        int next = n + 1
        print("awaited #i{n}, next=#i{next}")
    }
}
```

Rules:

- `await` is **only** allowed inside a `task` body
- `await name` waits for the named sibling (or other awaitable) to finish and yields its `return` value
- Prefer **results via `return` + `await`** over poking shared state when you can

### Fan-in (several producers, one consumer)

```pys
tasks {
    task left {
        return 10
    }
    task right {
        return 32
    }
    task {
        int a = await left
        int b = await right
        print(a + b)    # 42
    }
}
```

### Chain (pipeline of results)

```pys
tasks {
    task step1 {
        return 2
    }
    task step2 {
        int x = await step1
        return x * 3
    }
    task {
        int y = await step2
        print(y)        # 6
    }
}
```

Do **not** build cycles (`a` awaits `b` and `b` awaits `a`) — that can deadlock.

---

## 3. Capture rules — read-only unless `shared`

Anything declared **outside** a task and used inside it is a **capture**.

| Capture kind | Read | Write |
|--------------|------|-------|
| Ordinary outer local (`int x = …`) | yes | **no** (transpile error) |
| `shared` outer (`shared int x = …`) | yes | **yes** |
| Local declared inside the task | yes | yes |

### Read-only capture (default)

```pys
string label = "probe"
int seed = 7

tasks {
    task {
        print("label=#s{label} seed=#i{seed}")   # OK: read
        # seed = 8                               # ERROR
    }
}
```

Error message shape:

> Cannot assign to `'seed'` inside task; captured variables are read-only.  
> Declare it `shared` to allow cross-task mutation.

### `shared` — intentional cross-task mutation

```pys
shared int counter = 0

tasks {
    task {
        counter = counter + 1
    }
    task {
        counter = counter + 1
    }
    task {
        counter = counter + 1
    }
}
print(counter)    # 3
```

`shared` is visible in the source on purpose: mutation across tasks is never tribal knowledge.

Under the hood, `shared` values use a locked cell so single read-modify-write updates are safe. Still prefer **small critical updates**; don’t treat `shared` as a substitute for clear data flow.

### Mixing read-only + shared

```pys
string tag = "batch"     # read-only in tasks
shared int hits = 0      # mutable in tasks

tasks {
    task {
        print("tag=#s{tag}")
        hits = hits + 1
    }
    task {
        print("tag=#s{tag}")
        hits = hits + 1
    }
}
print(hits)
```

---

## 4. Sequencing groups (stages)

Each `tasks` block joins before the next statement. Use that for **stages**:

```pys
shared int part_a = 0
shared int part_b = 0

# Stage 1 — produce in parallel
tasks {
    task {
        part_a = 21
    }
    task {
        part_b = 21
    }
}

# Stage 2 — both parts are ready
int combined = part_a + part_b
print(combined)    # 42
```

Or two independent waves:

```pys
tasks {
    task { print("group-1 / a") }
    task { print("group-1 / b") }
}
print("group 1 done")
tasks {
    task { print("group-2 / c") }
    task { print("group-2 / d") }
}
```

---

## 5. Combining `await` and `shared`

Use `await` for **values**, `shared` for **coordination counters / accumulators**:

```pys
shared int seen = 0

tasks {
    task prepared {
        seen = seen + 1
        return 100
    }
    task {
        int value = await prepared
        seen = seen + 1
        print(value)
    }
}
print(seen)    # 2
```

---

## 6. What not to do

| Avoid | Why |
|-------|-----|
| `task { }` outside `tasks` | Illegal — no owning group |
| `await` outside a `task` | Illegal — nowhere to suspend |
| Assigning to a non-`shared` outer name | Capture is read-only |
| `import threading` / `asyncio` for this | Language keywords are the API |
| Deadlock cycles with mutual `await` | Group never finishes |

There is **no** public `run()` / `start()` pair. Lifetime is the `tasks` block; results are `return` + `await`.

---

## 7. Quick reference cheat sheet

```pys
# Group + anonymous workers
tasks {
    task { /* work */ }
}

# Named result
tasks {
    task name { return expr }
    task {
        Type x = await name
    }
}

# Explicit shared mutation
shared int n = 0
tasks {
    task { n = n + 1 }
}
```

---

## 8. Live examples in the repo

| File | Focus |
|------|--------|
| [`examples/concurrency/main.pys`](../examples/concurrency/main.pys) | Runs the full suite |
| [`basics.pys`](../examples/concurrency/basics.pys) | Join, read-only capture, task locals |
| [`awaiting.pys`](../examples/concurrency/awaiting.pys) | `await`, fan-in, chain |
| [`shared_state.pys`](../examples/concurrency/shared_state.pys) | `shared` counters / accumulate |
| [`pipeline.pys`](../examples/concurrency/pipeline.pys) | Stages, mixed await + shared |
| [`more.pys`](../examples/concurrency/more.pys) | Many workers, phased groups |

```bash
python -m transpiler run examples/concurrency/main.pys
```

---

## Runtime note (implementation)

The transpiler lowers `tasks`/`task` to a thread-pool join and `shared` to a locked cell. That is an implementation detail: write PYS with `tasks` / `task` / `await` / `shared`, not with Python’s threading or asyncio APIs.
