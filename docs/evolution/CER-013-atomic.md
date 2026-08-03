# CER-013: Atomic qualifier

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-03 |
| Commits | (atomic increment) |
| Scope | `lex.py`; `ast_nodes.py`; `parse.py`; `sem.py`; `concurrency.py`; `emit/python.py`; EBNF/railroad; examples; tests; docs; IDE |
| ADRs | [ADR-013](../adr/ADR-013-atomic.md) |

## Context

Need indivisible RMW / CAS for teaching concurrency without conflating
`shared` (visibility) with race-freedom. Spec: `requirements/atomic.md`.

### Pre-behavior

No `atomic` keyword. Capture mutation required `shared` only. CONCURRENCY
described `shared` partly as locked-cell safety. ADR-012 deferred `atomic`.

### Post-behavior

- Keyword `atomic`; `AtomicDecl`; parse rejects redundant `shared` + `atomic`
  and non-primitive / float types; `%=` parses as aug-assign.
- Sem: atomic ⊆ capture-mutable; ban `*=`/`/=`/`%=` (`pys.atomic-op`);
  validate `get` / `compareAndSet`; allow those members in OOP check;
  struct ban mirrors `shared`.
- Emit: `_PysAtomic` (lock-backed); Identifier → `.get()`; RMW → `iadd`/`isub`;
  assign → `set`; method calls bypass double `.get()`.
- `_PysShared` unchanged; teaching race uses `shared` + `x = x + 1`.
- Docs: CONCURRENCY language contract vs Python emitter notes; ADR-013;
  IDE 0.0.46; `examples/atomic.pys`.

### Evidence

`tests/test_atomic.py` (deterministic 2000, CAS, SA rejects, workspace-isolated
`run_source`).

## Trade-offs

- No float atomics / memory-order knobs (deferred).
- Entity identity cannot be `atomic` (grammar already requires `fix` fields).
