# CER-059: Make class abstract QuickFix + Create Class QF scoping

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-11 |
| Extends | [ADR-010](../adr/ADR-010-abstract-classes.md); [CER-056](CER-056-intellisense-completions.md) |
| Scope | `sem.py` (`pys.abstract-method` / `offer_create_class`); `pys-language/extension.js`; `class-header.js`; `refactor.js` |

## Context

`public abstract int greet()` inside a concrete `class` correctly raised
`pys.abstract-method`, but the lightbulb offered **Create Class** (from the
always-on refactor catalog QuickFix) and never **Make class abstract**.

### Pre-behavior

- Tips only on `pys.abstract-method` (no `suggested_fix`, no CodeAction)
- `refactor.js` always listed Create Class as `QuickFix` (no diagnostic gate)
- Preferred Create Class fired on any `pys.unknown-type`

### Post-behavior

- `pys.abstract-method` carries `suggested_fix=abstract class Name`
- Preferred QuickFix: Make class `Name` abstract — inserts `abstract ` before
  enclosing `class` (or replaces `closed class` with `abstract class`)
- Create Class QuickFix only when `suggested_fix=create-class` (annotations +
  PascalCase instantiate); inherits/cast/trait/array-alloc unknown types stay
  fail-closed without that QF
- Command `pys.generate.createClass` remains available from the palette

### Evidence

- `tests/test_abstract_class.py` (`suggested_fix`)
- `tests/test_unknown_type_sites.py` (sentinel on/off)
- `pys-language/test/quickfix-abstract.test.js`

## Trade-offs

- Does not change when `pys.unknown-type` is emitted (CER-057)
- Alternate tip (give the method a body) stays tip-only
