# ADR-013: Atomic qualifier (implies shared)

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-03 |
| Code detail | [CER-013](../evolution/CER-013-atomic.md) |
| Source | [`requirements/atomic.md`](../../requirements/atomic.md) |
| Supersedes | Deferred `atomic` note in [ADR-012](ADR-012-lambdas.md) |

## Context

`shared` makes cross-task (and lambda) mutation *visible* but does not guarantee
indivisible read-modify-write. Teaching needs an explicit `atomic` qualifier so
students see the visibility-vs-safety distinction (same class of bug as Java
`volatile` vs `AtomicInteger`).

### Cross-language placement

| Language | Mechanism | Teaching pitfall PYS avoids |
| --- | --- | --- |
| Java | `AtomicInteger` / library classes | Plain `int++` compiles and races silently |
| C++ | `std::atomic` + memory-order knobs | Ordering parameters are a subtle bug surface |
| C# / Go | `Interlocked` / `sync/atomic` utilities | Same “must remember the API” opt-in pitfall |
| Rust | `AtomicUsize` + required `Ordering` | Safest, steepest; PYS keeps type-level atomicity without exposing ordering |

PYS makes atomicity a **type qualifier** (like Rust’s direction) without
memory-order knobs. Rejecting `*=`/`/=`/`%=` on `atomic` variables teaches
*why* those ops are not single RMW instructions, rather than silently omitting
operators as Java’s wrappers do. Spec vs emitter boundary:
[CONCURRENCY.md](../CONCURRENCY.md) § Language contract vs reference emitter.

## Decision

1. Syntax: `atomic <primitive> name = expr` only — not `shared atomic` /
   `atomic shared` (redundant; `atomic` implies shared for capture).
2. Primitives: `int`, `int16`, `int32`, `int64`, `dword`, `bool` (no float/string).
3. Guaranteed ops: `+=`, `-=`, `++`, `--`, plain `=`, `get()`,
   `compareAndSet(expected, new)`.
4. Rejected on atomic: `*=`, `/=`, `%=`.
5. Capture: `atomic` ⊆ mutable-capture set (same as `shared`) for tasks and lambdas.
6. Language contract vs emitter: CONCURRENCY splits target-independent rules from
   Python `_PysAtomic` / ThreadPoolExecutor notes. Do **not** weaken `_PysShared`.
7. Deferred unchanged: memory-order knobs; float atomics; changing task scheduling.

## Consequences

- IDE ≥ 0.0.46; example `examples/atomic.pys`; JIT `J-atomic`.
- Pedagogy: show `shared` + `x = x + 1` race first, then `atomic` + `+=`.

## Rejected alternatives

- Folding atomic into the lambda increment (ADR-012).
- Weakening shared emit to demonstrate races on `+=`.
- Exposing memory-order parameters at language level.
