## PYS Language Specification — `atomic`

### 0. A prior question this construct cannot be specified without answering

Before writing the grammar: `docs/CONCURRENCY.md` describes `tasks`/`task`/`await` as *structured concurrency*, but the EBNF gives no indication of whether `task` bodies actually run on separate OS threads/processes, or run cooperatively on a single thread (Python `asyncio`-style), yielding only at `await` points. This distinction is not cosmetic — it entirely determines what `atomic` needs to guarantee:

- **If tasks are cooperative (single-threaded, only `await` yields control)**: any code between two `await` points is already atomic with respect to other tasks, by construction — no hardware primitive is needed, because nothing can interleave mid-statement. `atomic` would then only need to protect against interleaving *across* an `await`, which is a narrower and different problem than classic thread-safety.
- **If tasks map to real OS threads or processes**: ordinary compound assignment (`counter += n`) is unsafe at the machine level regardless of `await`, and `atomic` needs to compile to genuine hardware-level indivisible operations (or a lock), exactly like Java's `AtomicInteger` or C++'s `std::atomic`.

The specification below is written for the general (thread-based) case, since that is the more conservative assumption and remains correct even if PYS's execution model turns out to be cooperative — a cooperative model can always implement `atomic` as a no-op-safe pass-through, whereas the reverse is not true. Flagging this because the reference emitter targets Python, where `asyncio`-based `tasks` and `threading`-based `tasks` would compile `atomic` completely differently, and that choice belongs in `docs/CONCURRENCY.md`, not silently assumed here.

### 1. Overview

`atomic` is a variable qualifier, orthogonal to but layered on top of `shared`. Where `shared` (already specified) only makes cross-task mutability *visible* in the source — a documentation-level guarantee, not a safety guarantee — `atomic` additionally guarantees that the compound operations it permits execute as an indivisible unit with respect to other tasks. Declaring a variable `atomic` implies `shared` (an atomic variable is inherently meant for cross-task access; there is no meaningful single-task use case for it that wouldn't just be a plain variable).

### 2. Grammar (EBNF extension)

```ebnf
(* ------------------------- Atomic ------------------------- *)

atomic_decl       = "atomic" , atomic_primitive , identifier , "=" , expression ;

atomic_primitive  = "int" | "int16" | "int32" | "int64" | "dword" | "bool" ;
(* Restricted to primitives with a well-defined indivisible
   read-modify-write on real hardware/runtime primitives. "float" is
   deliberately excluded: atomic floating-point add is not universally
   available as a single hardware instruction and invites a false
   sense of precision-safety; a float accumulator needing atomicity
   should use a compare-and-swap loop the language does not hide. *)
```

Amendment to `declaration`:

```ebnf
declaration       = var_decl
                 | const_decl
                 | fix_decl
                 | shared_decl
                 | atomic_decl
                 | function_decl
                 | class_decl
                 | struct_decl
                 | enum_decl
                 | interface_decl ;
```

Amendment to the lambda capture rule established in the previous section:

> Captured variables are read-only inside the lambda body, unless the captured variable is declared `shared` **or `atomic`**.

### 3. Static semantics

1. **`atomic` implies `shared`.** Writing both modifiers together (`atomic shared int x = 0`) is redundant and rejected with a compile-time error directing the author to drop `shared` — consistent with the "no silent redundancy" posture already applied elsewhere (e.g. rejecting `identity(...)` re-declaration in `entity` inheritance).
2. **Permitted atomic operations** on an `atomic`-declared variable are exactly the compound-assignment and increment/decrement operators already in the grammar: `+=`, `-=`, `++`, `--`. Each such operation on an `atomic` variable is guaranteed indivisible — no other task can observe or interleave a partial read-modify-write.
3. **Plain `=` assignment to an atomic variable is a full replace, also indivisible**, but does not itself constitute a safe read-modify-write pattern (see point 5, compare-and-swap).
4. **`*=`, `/=`, `%=` are not guaranteed atomic** even on an `atomic` variable — multiply/divide/modulo do not correspond to single hardware read-modify-write instructions on all target platforms as reliably as add/subtract/increment do. Using them on an `atomic` variable is a compile-time error, directing the author to the explicit compare-and-swap form (point 5) instead of silently emitting a non-atomic operation under an `atomic` label.
5. **Compare-and-swap primitive**: every `atomic`-declared variable exposes two built-in methods, callable like ordinary methods, for patterns that a single compound operator cannot express safely (e.g. "increment only if below a cap", "set only if still the expected value"):
   - `bool compareAndSet(T expected, T newValue)` — atomically sets to `newValue` only if the current value equals `expected`; returns whether the swap occurred.
   - `T get()` — atomic read of the current value.
   
   These are not user-declarable methods (an `atomic` variable is not a class instance); they are compiler-synthesized accessors on any identifier of an `atomic`-qualified type, analogous to how `entity`/`data` synthesize `equals`/`hashCode` without the member appearing in `class_body`.
6. **`atomic` variables may not be entity identity fields.** `identity(...)` in `entity_decl` already requires `fix` (immutability); `atomic` implies ongoing mutation across tasks, which is the direct opposite guarantee. Declaring an `identity(...)` field `atomic` is a compile-time error.

### 4. Worked examples

**The race condition `shared` alone does not prevent (motivating example):**

```pys
shared int counter = 0

tasks {
    task incrementMany() {
        loop (int i = 0; i < 1000; i++) {
            counter += 1   # NOT safe: read-modify-write can interleave
                           # between two concurrent tasks, losing updates
        }
    }
    task a { await incrementMany() }
    task b { await incrementMany() }
}
# Final counter value is non-deterministic and typically < 2000 under
# real thread-based execution — the classic "lost update" race.
```

**The same problem, made safe with `atomic`:**

```pys
atomic int counter = 0

tasks {
    task incrementMany() {
        loop (int i = 0; i < 1000; i++) {
            counter += 1   # guaranteed indivisible — no lost updates
        }
    }
    task a { await incrementMany() }
    task b { await incrementMany() }
}
# Final counter value is deterministically 2000.
```

**Compare-and-swap — a pattern no compound operator can express safely:**

```pys
atomic int highScore = 0

function void reportScore(int candidate) {
    loop (bool done = false; !done; ) {
        int current = highScore.get()
        if (candidate <= current) {
            done = true   # not a new high score, nothing to do
        } else {
            done = highScore.compareAndSet(current, candidate)
            # if another task updated highScore between get() and here,
            # compareAndSet fails and the loop retries with a fresh read
        }
    }
}
```

**Capture rule interaction — `atomic` satisfies the lambda mutation exception directly, no separate `shared` needed:**

```pys
atomic int hits = 0
requests.loop(r => hits += 1)   # allowed: hits is atomic, mutation
                                 # inside the lambda is safe and explicit
```

### 5. Cross-language comparison

| Language | Mechanism | Granted guarantee | Notable pitfall it avoids or introduces |
|---|---|---|---|
| Java | `AtomicInteger`, `AtomicLong`, `AtomicReference` — library classes, not language keywords | Indivisible `incrementAndGet`, `compareAndSet` | Requires knowing to reach for the class instead of a plain `int`; a plain `int++` compiles fine and races silently — the language gives no warning |
| C++ | `std::atomic<T>` template | Indivisible ops per the chosen memory-order parameter | Memory-order tuning (`relaxed`, `acquire`, `release`, `seq_cst`) is exposed directly to the programmer — powerful but a well-documented source of subtle bugs when the wrong ordering is chosen |
| C# | `Interlocked.Increment`, `Interlocked.CompareExchange` — static utility methods | Same guarantees as Java's `Atomic*` | Same "must remember to use the utility instead of `++`" pitfall as Java |
| Go | `sync/atomic` package functions (`atomic.AddInt64`, etc.) | Same class of guarantee | Same opt-in-only pitfall; regular `+=` on a shared variable compiles without warning |
| Rust | `std::sync::atomic::AtomicUsize` etc., explicit `Ordering` parameter required on every call | Compile-time enforced — the type itself has no plain `+=` operator, so unsafe usage cannot compile by accident | Steepest learning curve of this group, but structurally the safest: misuse is a compile error, not a silent runtime race |

**Where PYS's design sits relative to this table**: like Rust, PYS makes atomicity a *type qualifier* rather than a library call students must remember to reach for (Java/C#/Go's opt-in pitfall) — but without Rust's explicit memory-ordering parameter, keeping the surface simpler for a teaching language while still making the unsafe path (a plain `shared int` with unguarded `+=`) a distinct, visibly different declaration from the safe one (`atomic int`). The compile error steering `*=`/`/=`/`%=` toward `compareAndSet` is a deliberate design choice not present in Java/C#/Go, where those operators simply aren't offered on the atomic wrapper types at all — PYS makes the same restriction explicit as a rejected operation on a primitive-looking variable, which is more instructive for students (they see *why* multiply isn't atomic) than the alternative (Java's `AtomicInteger` simply has no `*` operator to try in the first place).

### 6. Didactic notes to carry into student-facing material

1. **Lead with the race condition, not the keyword.** The `shared`-without-`atomic` example in §4 should be shown running (or simulated) with a non-2000 result before `atomic` is introduced as the fix — mirroring the pedagogical approach already used for the lambda-capture bug (show the JS/Python failure first, then the PYS guarantee).
2. **`shared` vs `atomic` is a visibility-vs-safety distinction, and conflating the two is a real, documented category of bugs** (e.g. Java's `volatile` keyword guarantees visibility across threads but not atomicity of compound operations — a frequent point of confusion in Java concurrency teaching, since `volatile int x; x++;` still races despite `volatile` "sounding" thread-safe). This exact confusion is worth naming directly, since PYS's `shared` occupies conceptually the same space as `volatile` and risks the same misunderstanding if not addressed head-on.
3. **`compareAndSet` should be taught as "optimistic retry"**, not just as an API — the retry-loop pattern in §4 is the foundation for understanding lock-free data structures later, and is a transferable concept well beyond PYS itself (it appears identically in Java, C++, C#, Go, and Rust).

Correct, en dat is meteen de juiste scheiding van verantwoordelijkheden voor een taalspecificatie die meerdere emit-targets moet kunnen dragen. Vastgelegd:

## Addendum — Specification vs. Implementation Boundary for `atomic` and `tasks`

### Principle

The PYS language specification defines **observable behavioral contracts only**. It does not prescribe execution strategy (threads vs. cooperative scheduling), nor how a given emitter achieves a guarantee (hardware atomic instructions, mutex, lock-free CAS loop, or — for a cooperative single-threaded target — simply relying on the absence of preemption between `await` points). This is consistent with the grammar's own stated architecture: *"The reference emitter is Python (`transpiler/emit/python.py`); other backends may plug in at the emit layer later."* Execution-model decisions belong entirely to that emit layer, per target.

### Specification-level contract for `atomic` (target-independent)

Regardless of backend, an emitter targeting `atomic` **must** guarantee:

1. `+=`, `-=`, `++`, `--` on an `atomic`-declared variable are indivisible with respect to any other concurrently executing `task` — no interleaved partial read-modify-write is observable.
2. `compareAndSet(expected, newValue)` and `get()` are indivisible single operations.
3. `*=`, `/=`, `%=` remain rejected at compile time on `atomic` variables — this is a language-level restriction on what operations exist, not an implementation detail, and holds regardless of target.

**Deliberately unspecified** (left to each emitter):

- Whether this is achieved via OS-level atomic CPU instructions, a mutex/lock, a language-native atomic type (e.g. `java.util.concurrent.atomic.AtomicInteger` for a hypothetical Java target, `std::atomic<int>` for a C++ target, `threading.Lock`-wrapped operations for a thread-based Python target, or an unguarded operation for a cooperative single-threaded Python `asyncio` target where the contract is trivially satisfied between `await` points).
- Memory-ordering semantics beyond the sequential-consistency guarantee implied by "no interleaved partial write" — an emitter targeting a language with configurable memory ordering (e.g. Rust, C++) may choose the strongest available ordering by default, since PYS's contract does not expose ordering as a tunable at the language level (unlike Rust/C++ directly).

### Consequence for the open question in the previous message

This resolves it directly: `docs/CONCURRENCY.md` does **not** need to commit to a thread-based vs. cooperative execution model at the specification level. It only needs to state the contract above. Each emitter's implementation notes — not the language spec — document how that emitter satisfies the contract for its target (e.g. a `transpiler/emit/python.py`-specific note on whether it emits `threading`-based or `asyncio`-based task scheduling, and correspondingly whether `atomic` compiles to a lock-guarded block or a plain operation).

### Where this leaves `docs/CONCURRENCY.md` structurally

Suggest splitting it, going forward, into two clearly labeled parts to keep this boundary visible to future contributors and students:

- **§ Language contract** (target-independent): `tasks`/`task`/`await` structural rules already in the EBNF (DAG requirement, capture rules, `shared`/`atomic` semantics as specified above).
- **§ Reference emitter notes** (Python-specific, non-normative): how `transpiler/emit/python.py` currently realizes that contract — explicitly marked as an implementation choice, not part of the language definition, so a reader does not mistake "how the Python emitter happens to do it today" for "what PYS requires."
