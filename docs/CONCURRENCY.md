# PYS concurrency model

How `tasks`, `task`, `await`, `shared`, and `atomic` work together.

This document has two layers:

1. **Language contract** — target-independent observable rules (visibility vs
   indivisible RMW, capture, DAG awaits).
2. **Reference emitter notes** — how the Python backend (`emit/python.py` +
   `concurrency.py`) satisfies that contract today.

Runnable showcase:

```bash
python -m transpiler run examples/concurrency/main.pys
python -m transpiler run examples/concurrency/http/http_main.pys  # Open-Meteo + DownStatus
python -m transpiler run examples/atomic.pys
```

Formal grammar: [`language.ebnf`](language.ebnf) · language overview: [`LANGUAGE.md`](LANGUAGE.md) · railroad: [`language-railroad.html`](language-railroad.html)

---

## Mental model (five words)

| Keyword | Role |
|---------|------|
| **`task`** | One concurrent unit of work (optional name + parameters) |
| **`tasks`** | A **group** of tasks that run together; leaving the block **waits for all** |
| **`await`** | **Wait until** this value is ready (`await name` or `await name(args)`) |
| **`shared`** | This variable **may be mutated** by more than one task (**visibility**, not safety) |
| **`atomic`** | Cross-task cell with **indivisible** `+=`/`-=`/`++`/`--`, `get`, `compareAndSet` (implies shared for capture) |

**Inputs:** pass **parameters** (`task work(int n) { … }` then `await work(3)`).  
**Outputs:** `return` then `await`.  
Do **not** feed tasks through outer captures — that becomes spaghetti. Captures stay for rare read-only constants; mutation uses `shared` or `atomic`.

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
2. Auto-start every **parameterless** `task` / `task name`
3. Parameterized `task name(...)` are **templates** — they run when someone `await name(args)`
4. On the closing `}`, wait until every started child has finished (or failed)
5. Continue with the next statement

That is **structured concurrency**: the block owns the children’s lifetime.

### Locals inside a task

Names declared *inside* a task (including parameters) are private to that task:

```pys
tasks {
    task {
        int x = 10
        print(x)
    }
}
```

---

## 2. How `return` is used — only through `await`

A task’s `return` value is **not** automatically available outside the `tasks`
block. Another task must **`await`** that task; the await expression *is* the
returned value.

```text
  producer                         consumer (another task)
  ────────                         ───────────────────────
  task answer {                    task {
      return 41   ──────►              int n = await answer
  }                                    # n is 41 here
                                   }
```

Same idea with parameters:

```text
  task add(int a, int b) { return a + b }

  int s = await add(10, 32)
  #        └── runs add with 10,32
  #  s  ←── whatever add returned (42)
```

Important:

- `return` inside a task = “this is my result when someone awaits me”
- `await name` / `await name(args)` = “run/wait for that task and give me its return value”
- You **cannot** write `int x = answer` — that is not how results flow
- After the whole `tasks { }` block finishes, those returns are gone unless you
  copied them into an outer/`shared` variable while still inside a consumer task

### Parameterized task — preferred inputs

```pys
tasks {
    task add(int a, int b) {
        return a + b          # output of this task
    }
    task {
        # await add(...)  →  starts add, waits, becomes the returned int
        int s = await add(10, 32)
        print(s)              # 42
    }
}
```

| Form | Meaning |
|------|---------|
| `task name(type p, …) { … }` | Template — runs on `await name(…)` |
| `await name(args)` | Start with args; wait; yield `return` value |
| `task name { … }` | No params — auto-starts; `await name` |
| `task { … }` | Anonymous auto-started unit |

```pys
tasks {
    task greet(string name, int times) {
        print("hello #s{name} x#i{times}")
        return times
    }
    task {
        int n = await greet("Ada", 3)
        print(n)
    }
}
```

### Zero-arg named task

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
- Prefer **parameters in + `return`/`await` out** — not outer captures for inputs
- `await name(args)` requires `task name(...)` (parentheses on the declaration)

### Fan-in

```pys
tasks {
    task left(int n) {
        return n
    }
    task right(int n) {
        return n
    }
    task {
        int a = await left(10)
        int b = await right(32)
        print(a + b)    # 42
    }
}
```

### Chain

```pys
tasks {
    task step1(int n) {
        return n
    }
    task step2(int x) {
        return x * 3
    }
    task {
        int mid = await step1(2)
        int y = await step2(mid)
        print(y)        # 6
    }
}
```

Do **not** build cycles (`a` awaits `b` and `b` awaits `a`) — the transpiler
**rejects** await cycles (they would deadlock).

---

## 2b. Deadlocks and await cycles (rejected)

The concurrency model does **not** prevent every possible hang, but the
transpiler **rejects await cycles** inside a `tasks` group.

**Illegal (mutual wait):**

```pys
tasks {
    task a {
        int x = await b    # ERROR: cycle a → b → a
        return 1
    }
    task b {
        int y = await a
        return 2
    }
}
```

**Illegal (self-wait):**

```pys
tasks {
    task a {
        int x = await a    # ERROR
        return 1
    }
}
```

**Proper use — acyclic producer → consumer:**

```pys
tasks {
    task produce(int n) {
        return n * 2
    }
    task {
        int v = await produce(21)   # consumer waits on producer only
        print(v)
    }
}
```

**Proper use — stages (separate groups):**

```pys
tasks {
    task stage1 { return 1 }
    task {
        int x = await stage1
        # copy out via shared if needed later
    }
}
tasks {
    task stage2(int n) { return n + 1 }
    task {
        int y = await stage2(1)
    }
}
```

Rules of thumb:

1. Await dependencies must form a **DAG** (no loops).
2. Prefer one **consumer** that awaits producers — not peers awaiting each other.
3. Use a later `tasks` block for the next stage instead of circular waits.
4. Structured `tasks { }` still joins children; cycles are about *await edges*, not forgotten joins.

---

## 3. Capture rules — last resort (prefer parameters)

Anything declared **outside** a task and used inside it is a **capture**.
**Prefer task parameters for inputs.** Captures are easy to overuse and create
spaghetti. Keep them for read-only constants; use `shared` only for intentional
cross-task mutation.

| Capture kind | Read | Write |
|--------------|------|-------|
| Ordinary outer local (`int x = …`) | yes | **no** (transpile error) |
| `shared` outer (`shared int x = …`) | yes | **yes** (visibility only) |
| `atomic` outer (`atomic int x = …`) | yes | **yes** + indivisible RMW ops |
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
> Declare it `shared` or `atomic` to allow cross-task mutation.

### `shared` — visibility of cross-task mutation

```pys
shared int counter = 0

tasks {
    task {
        counter = counter + 1
    }
    task {
        counter = counter + 1
    }
}
print(counter)
```

`shared` is visible in the source on purpose: mutation across tasks is never tribal knowledge.

**Language contract:** `shared` is a *visibility* qualifier — the mutation is declared, not hidden. It does **not** make `counter = counter + 1` (or even `+=`) race-free under concurrent tasks. That is the same teaching trap as Java `volatile` vs true atomics.

### `atomic` — indivisible RMW (implies shared for capture)

```pys
atomic int counter = 0

tasks {
    task {
        loop (int i = 0, i < 1000, i++) {
            counter += 1
        }
    }
    task {
        loop (int i = 0, i < 1000, i++) {
            counter += 1
        }
    }
}
print(counter)  # deterministically 2000
```

| Allowed on `atomic` | Rejected |
|---------------------|----------|
| `+=`, `-=`, `++`, `--`, plain `=` | `*=`, `/=`, `%=` |
| `get()`, `compareAndSet(expected, new)` | redundant `shared atomic` / `atomic shared` |

Primitives: `int`, `int16`, `int32`, `int64`, `dword`, `bool` (no float/string).

CAS sample (while form):

```pys
atomic int highScore = 0
function void reportScore(int candidate) {
    bool done = false
    loop (!done) {
        int current = highScore.get()
        if (candidate <= current) {
            done = true
        } else {
            done = highScore.compareAndSet(current, candidate)
        }
    }
}
```

DoD sample: [`examples/atomic.pys`](../examples/atomic.pys) · JIT: [`J-atomic`](../tutorials/jit/J-atomic.md).

### Mixing read-only + shared

```pys
string tag = "batch"     # read-only in tasks
shared int hits = 0      # mutable in tasks (visibility)

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
| Assigning to a non-`shared`/`atomic` outer name | Capture is read-only |
| `import threading` / `asyncio` for this | Language keywords are the API |
| Await cycles (`a`↔`b`, or `await` self) | **Rejected** at transpile time (`pys.await-cycle`) |
| Treating `shared` as race-free | Visibility only — use `atomic` for indivisible RMW |

There is **no** public `run()` / `start()` pair. Lifetime is the `tasks` block; results are `return` + `await`.

---

## 7. Quick reference cheat sheet

```pys
# Group + anonymous workers
tasks {
    task { /* work */ }
}

# Parameters in, return/await out
tasks {
    task work(int x, string label) {
        print(label)
        return x + 1
    }
    task {
        int y = await work(3, "job")
    }
}

# Zero-arg named auto task
tasks {
    task ready { return 1 }
    task {
        int n = await ready
    }
}

# Explicit shared mutation (visibility; not race-free by itself)
shared int n = 0
tasks {
    task bump(int d) { n = n + d }
    task {
        int ignored = await bump(1)
    }
}

# Atomic RMW (indivisible +=)
atomic int hits = 0
tasks {
    task { hits += 1 }
    task { hits += 1 }
}
```

---

## 8. Live examples in the repo

| File | Focus |
|------|--------|
| [`examples/concurrency/main.pys`](../examples/concurrency/main.pys) | Runs the full offline suite |
| [`basics.pys`](../examples/concurrency/basics.pys) | Join, task parameters, task locals |
| [`awaiting.pys`](../examples/concurrency/awaiting.pys) | `await`, parameterized fan-in / chain / args |
| [`shared_state.pys`](../examples/concurrency/shared_state.pys) | `shared` + parameterized bumps |
| [`pipeline.pys`](../examples/concurrency/pipeline.pys) | Stages, mixed await + shared |
| [`more.pys`](../examples/concurrency/more.pys) | Many workers, phased groups |
| [`http/`](../examples/concurrency/http/) (`http_main.pys`) | Live HTTPS package: Open-Meteo + DownStatus (package visibility) |
| [`examples/atomic.pys`](../examples/atomic.pys) | Race teaching + `atomic` / CAS / lambda |

```bash
python -m transpiler run examples/concurrency/main.pys
python -m transpiler run examples/concurrency/http/http_main.pys   # needs network
python -m transpiler run examples/atomic.pys
```

---

## Language contract vs reference emitter

### Language contract (target-independent)

- `tasks` / `task` / `await` structured lifetime and DAG awaits (already in EBNF).
- Capture: outer names read-only unless `shared` or `atomic`.
- `shared`: mutation is **declared** across tasks — not a race-freedom guarantee.
- `atomic`: `+=`/`-=`/`++`/`--` and plain `=` are indivisible w.r.t. other tasks;
  `get` / `compareAndSet` for non-RMW patterns; `*=`/`/=`/`%=` rejected;
  implies shared for capture (no `shared atomic`).

Emitters may use hardware atomics, locks, or (on a cooperative single-threaded
target) rely on no preemption between `await` points — as long as the contract
holds.

### Reference emitter notes (Python)

Today’s Python backend uses `ThreadPoolExecutor` for `tasks`, `_PysShared` for
`shared`, and `_PysAtomic` for `atomic` (lock-backed `get` / `set` / `iadd` /
`isub` / `compareAndSet`). Identifier reads on atomics become `.get()`.

`_PysShared` also locks `+=` / `set` for practicality, but **`shared_counter =
shared_counter + 1` can still lose updates** (unlocked `.value` read + locked
`set`). That is the intentional teaching race before introducing `atomic`.

Write PYS with `tasks` / `task` / `await` / `shared` / `atomic`, not with
Python’s threading or asyncio APIs.
