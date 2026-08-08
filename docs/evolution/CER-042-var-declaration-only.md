# CER-042: Ban type-position `var`; formalize `object`

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-08 |
| Scope | `transpiler/parse.py`, `transpiler/sem.py`, examples, book, LANGUAGE |
| Extends | [ADR-025](../adr/ADR-025-var-declaration-only.md) |

## Context

Production-mimic examples (template engines, webserver queues) used `var` as a
signature/field type. Spec and EBNF never allowed that; enforcement was missing.

## Entries

### 1. Reject type-position `var`

- **Pre-behavior:** `public var lookup(...)`, `serveOne(var conn)`,
  `private var q`, `list<var>` parsed and transpiled; `var` treated as
  assignability escape hatch in sem.
- **Post-behavior:** Type-position `var` raises `FatalParseError` /
  `pys.var-as-type`. Declaration-form `var name = expr` (script-top and
  locals) unchanged. Opaque foreign values use `object`; params may omit type.
- **Evidence:** `tests/test_var_as_type.py`; migrated
  `examples/webserver-templates*` / `webserver*` / `rest-api/shop/*`.

## Trade-offs

- `object` is intentionally weak (anything in); prefer concrete class types
  when known (`Router`, …).
- Omitting a parameter type is fine on ordinary methods; on constructors,
  prefer `object name` when mixed with typed params — emit assigns Python
  defaults only to typed ctor params, and a bare name between defaults is
  invalid Python.
