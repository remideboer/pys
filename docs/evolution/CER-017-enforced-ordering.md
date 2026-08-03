# CER-017: Enforced member and import ordering

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-03 |
| Commits | (enforced-ordering increment) |
| Scope | `parse.py` phase cursor; `FieldDecl.is_const`; class emit fix/const hooks; `tests/test_enforced_ordering.py`; GUI ctor relocate; EBNF / LANGUAGE / README / teaching |
| ADRs | [ADR-015](../adr/ADR-015-enforced-ordering.md) |

## Context

Multi-category bodies (`class` / `struct` / `trait` / `entity`) and top-level
imports were free-form. Style was left to authors; diagnostics for disorder did
not exist at parse time.

### Pre-behavior

- `_parse_class` / `_parse_struct` / `_parse_trait` / `_parse_entity` accepted
  members in any kind order.
- `_parse_brace_module_rd` accepted `import` after declarations/statements.
- Class fields were mutable-only (`access type name`); no class-level
  `const` / `fix` field forms.
- EBNF used unordered `{ class_member }` / similar.

### Why it hurt

- Readers scanned entire bodies to find “where are the fields?”.
- Ordering was taught informally while PYS’s philosophy elsewhere is to make
  such conventions structural.
- Refactors could leave kinds in accidental order without a compiler signal.

### Post-behavior

- Phase helpers (`_require_member_phase` + §5 messages) reject earlier kinds
  after a later phase advances.
- Imports must precede the first non-import toplevel (blank/comment ignored for
  the “seen non-import” flag).
- Class parse accepts `const` / `fix` field sections; `FieldDecl.is_const`;
  emit stores fix/const field guards where applicable.
- Consecutive PYS `import Name from mod` lines are not misparsed as Python
  `from mod import` adjacency (look-ahead distinguishes `… import X from`).
- Spec, README “Why enforced member ordering?”, JIT/S7/practice track.

### Evidence

`tests/test_enforced_ordering.py`; full pytest; acceptance examples (ctors
moved above methods in `examples/gui/*/ui.pys`).

## Trade-offs

- Corpus must obey order (GUI apps reordered).
- Tasks blocks remain unordered by design (ADR-015).
- Does not invent new class-const runtime beyond existing fix/const patterns.
