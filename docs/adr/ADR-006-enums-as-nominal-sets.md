# ADR-006: Enums as nominal closed sets

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-02 |
| Commits | (enums + warnings increment) |
| Code detail | [CER-005](../evolution/CER-005-enums-and-warnings.md) |

## Context

PYS needed a first-class closed set of named constants distinct from ints,
strings, and classes. Requirements live in `requirements/enums.pys`.

## Decision

1. **`enum`** is a first-class declaration (sibling to `struct` / `class`) with
   optional `top_visibility`. Members are **comma-delimited** with an optional
   trailing comma ([ADR-022](ADR-022-optional-terminators-grammar.md)).
2. **All-or-nothing values:** fully implicit (`enum.auto`) or fully explicit;
   mixed forms are errors.
3. **Homogeneous unique explicit values** (all int or all string); duplicates
   rejected. Alias support, if ever added, must be a **real language construct**
   — not an `@alias` annotation (use real syntax later; library `@expr`
   application is separate — [ADR-026](ADR-026-library-decorators.md)).
4. **Nominal typing:** `EnumName.MEMBER` only; no call ctor; `.value` for
   underlying interchange; `==` only within the same enum.
5. **Naming:** non-`SCREAMING_SNAKE_CASE` members emit a **warning** (non-fatal)
   with tip + suggested rename for IDE quick fix.
6. **Emit:** `enum.Enum` + `auto()`, `IntEnum`, or `StrEnum` (Python 3.11+).
7. **Exhaustiveness / multi-way branch:** delivered as `switch` (stmt + expr) in
   [ADR-008](ADR-008-switch-stmt-and-expr.md) — supersedes the deferred `match`
   idea in [F-002](../TODO-FUTURE.md#f-002-enum-match-exhaustiveness).
   Value aliases via real syntax remain deferred — [F-003](../TODO-FUTURE.md#f-003-enum-value-aliases).

## Consequences

- Requires first-class compiler warnings (`TranspileWarning`) and IDE Warning
  severity / quick-fix plumbing (feature-maturity DoD for diagnostics).
- Pedagogy: JIT `J-enum`; example `examples/enums.pys` (workspace-isolated
  `run_source` per CER-001 §4).
- Security boundaries (ADR-001) unchanged.

## Rejected alternatives

- Treating enums as sugar for `const int` / string unions.
- Fatal error on naming (rejected in favor of warning).
- Shipping a separate `match` keyword (superseded by `switch` / ADR-008).
- **`@alias` (or any `@` annotation)** — PYS does not use decorator-style marks;
  those usually signal a missing language construct. Alias/duplicate naming, if
  needed later, gets proper syntax in a new ADR/CER — not an annotation bolt-on.
