# CER-011: `data` and `entity` types

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-03 |
| Commits | (data/entity increment) |
| Scope | `lex.py`; `ast_nodes.py`; `parse.py`; `sem.py`; `emit/python.py`; `imports.py`; EBNF/railroad; `docs/DATA_ENTITY.md`; README; LANGUAGE; JIT; IDE; tests; examples |
| ADRs | [ADR-011](../adr/ADR-011-data-and-entity.md) |

## Context

Need first-class Value Object (`data`) and identity-keyed (`entity`) constructs
per `requirements/data_entity.md`, without changing `struct`’s identity-free
contract (ADR-005).

### Pre-behavior

Only `struct` / `class` for bundled state. No compiler-enforced identity keys
or immutable VO surface separate from `fix struct`.

### Post-behavior

- Keywords `data`, `entity`, `identity`.
- SA: root `identity` mandatory; identity fields `fix`; entity-only inherits;
  ban hand equals; `data` immutable (fix-struct SA path).
- Emit: frozen dataclass + copy for `data`; class + key `__eq__`/`__hash__`/
  `__repr__` + fix setattr for `entity`.
- Docs/IDE 0.0.44; examples `data.pys` / `entities.pys` (DoD: `data.pys`
  contrasts `struct` mutable bags vs VO immutability).
- Database teaching example `examples/database/`: entity-centric abstract
  Repository contracts (`all/get/add/save/remove`) are separate from Data
  Mappers that own MySQL SQL and row/entity translation. Menus mutate non-key
  entity state then `save`; `identity(...)` keys remain `fix`.

### Evidence

`tests/test_data_entity.py` (examples + SA rejects + composite keys);
workspace-isolated `run_source` (CER-001 §4).
`examples/data.pys` teaches `data` vs `struct` use cases in-file.
The shop acceptance check compiles all modules and asserts SQL/MySQL stay out
of `repositories`, while abstract repositories and concrete mappers emit.

## Trade-offs

- `struct` still has field-wise `==` without the VO contract — intentional
  (ADR-005); use `data` when the contract is the point.
- Timestamps in samples are `string` (no `DateTime` builtin yet).
