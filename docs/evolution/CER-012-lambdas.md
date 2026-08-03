# CER-012: Lambdas with by-value capture

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-03 |
| Commits | (lambda increment) |
| Scope | `lex.py`; `ast_nodes.py`; `parse.py`; `sem.py`; `emit/python.py`; EBNF/railroad; examples; tests; docs; IDE |
| ADRs | [ADR-012](../adr/ADR-012-lambdas.md) |

## Context

Need first-class anonymous functions per `requirements/lambda.md`, with a
single capture model shared with tasks.

### Pre-behavior

No `=>` lambda expressions; `=>` only in switch arms. Foreach loop variables
were writable. `.loop(fn)` accepted only identifier callees in practice for
teaching samples.

### Post-behavior

- Keyword `lambda`; `LambdaExpr`; parse `n =>` / `(…) =>` / block bodies.
- Type `lambda<…>`; param inference from binding/call targets.
- Capture SA (`pys.lambda-capture`); foreach vars frozen like C-style counters.
- Emit `def _pys_lam_N(... , _c_free=free)` for by-value snapshots.
- Docs/IDE 0.0.45; `examples/lambdas.pys` (DoD elaborate + Python pitfall contrast).
- ~~`atomic` deferred~~ — delivered in [CER-013](CER-013-atomic.md) / ADR-013.

### Evidence

`tests/test_lambdas.py`; workspace-isolated `run_source` (CER-001 §4).

## Trade-offs

- Expression-body `print(i)` becomes `return print(...)` in Python (harmless).
- Capture mutation escape hatches: `shared` (visibility) and `atomic` (indivisible RMW).
