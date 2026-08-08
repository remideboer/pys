# CER-046: `open` / `override` / `closed` extension points

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-08 |
| Extends | [ADR-028](../adr/ADR-028-open-override-closed.md) |
| Amends | [CER-009](CER-009-abstract-classes.md) (`sealed` → `closed`) |
| Scope | `lex.py`, `parse.py`, `sem.py`, examples, book, IDE |

## Context

Methods were always overridable by same-name redefinition; `sealed` only sealed
classes.

## Entries

### 1. `sealed` → `closed` at class level

- **Pre-behavior:** `sealed class` rejected further `inherits`.
- **Post-behavior:** `closed class`; same semantics. Keyword `sealed` removed.
- **Evidence:** updated `test_language_spec` / `test_sem`.

### 2. Method extension modifiers + closed-by-default

- **Pre-behavior:** Subclass `public bump()` silently replaced parent.
- **Post-behavior:** Need `open` on ancestor (or abstract/root) and `override`
  / `override closed` on child; otherwise compile error.
- **Evidence:** `tests/test_open_override_closed.py`.

### 3. Implicit root for `toString` / `equals` / `hashCode`

- **Pre-behavior:** No ancestor for `override toString`.
- **Post-behavior:** Semantic root sockets; data/entity synthesized members
  remain banned from hand re-declaration (ADR-011).
- **Evidence:** override-toString tests; data/entity unchanged bans.

## Trade-offs

- Mechanical migrate of every intentional override site in examples/book.
