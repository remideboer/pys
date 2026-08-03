# ADR-012: Lambdas with by-value capture

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-03 |
| Code detail | [CER-012](../evolution/CER-012-lambdas.md) |
| Source | [`requirements/lambda.md`](../../requirements/lambda.md) |

## Context

Teaching needs first-class function values without Python/JS closure pitfalls
(late binding, shared loop variables). Task bodies already use read-only outer
captures unless `shared`; lambdas should share that model.

## Decision

1. Syntax: `params => expr` / `params => { … }`; type `lambda<P…, R>` (last is return).
2. Capture **by value** at creation; captured names read-only unless `shared`.
3. Foreach loop variables are immutable per iteration (same as C-style counters).
4. Emit: nested `def` with default-arg snapshots for free variables.
5. `atomic` (indivisible RMW) is **deferred** — documented as future CONCURRENCY work; `shared` is visibility only.

## Consequences

- One capture story for `tasks` and lambdas.
- IDE ≥ 0.0.45; example `examples/lambdas.pys`; JIT `J-lambda`.

## Rejected alternatives

- Python-style late binding (defeats the teaching goal).
- Reference capture / `[&]` (dangling risk).
- Folding `atomic` into this increment.
