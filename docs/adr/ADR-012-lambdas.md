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
captures unless `shared`; lambdas should share that model — one capture story
for the whole language.

### Cross-language capture pitfalls (why by-value + per-iteration)

| Language | Capture pitfall | Consequence | PYS answer |
| --- | --- | --- | --- |
| JavaScript (pre-`let`) | `var` in a loop is function-scoped; all closures share one binding | `for (var i=0;i<3;i++) …` timers print `3,3,3` | Loop binders immutable per iteration; each lambda captures its own value |
| Python | Closures are late-binding: they read the variable at *call* time | `[lambda: i for i in range(3)]` — all return `2` | Capture by value at creation — no late binding |
| Java | Lambdas may only capture “effectively final” locals | Forces `AtomicInteger` / single-element arrays for accumulation | `shared` / `atomic` are explicit mutable-capture escape hatches |
| C++ | `[&]` reference capture can dangle if the lambda outlives its scope | UB in async code | By-value only — no reference-capture form |
| C# (pre-5.0) | `foreach` had one shared binding across iterations | Same symptom as the JS bug | Fixed like modern C#/JS: per-iteration scoping |

Student-facing material should show the JS/Python failure *before* stating the
PYS rule (same pedagogical pattern as `requires` and `identity(...)`).

## Decision

1. Syntax: `params => expr` / `params => { … }`; type `lambda<P…, R>` (last is return).
2. Capture **by value** at creation; captured names read-only unless `shared`
   or `atomic` (atomic implies shared for capture — see [ADR-013](ADR-013-atomic.md)).
3. Foreach loop variables are immutable per iteration (same as C-style counters).
4. Emit: nested `def` with default-arg snapshots for free variables.
5. ~~`atomic` deferred~~ — **superseded by [ADR-013](ADR-013-atomic.md)**.

## Consequences

- One capture story for `tasks` and lambdas.
- IDE ≥ 0.0.45; example `examples/lambdas.pys`; JIT `J-lambda`.
- Indivisible RMW / CAS: [ADR-013](ADR-013-atomic.md).

## Rejected alternatives

- Python-style late binding (defeats the teaching goal).
- Reference capture / `[&]` (dangling risk).
- Folding `atomic` into the lambda increment (delivered separately as ADR-013).
