# ADR-008: Switch statement and expression

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-02 |
| Code detail | [CER-007](../evolution/CER-007-switch-stmt-and-expr.md) |

## Context

Java-style multi-way branch is a core teaching construct. A separate `match`
keyword (F-002) was deferred; product choice is a single `switch` with both
statement and expression forms.

## Decision

1. **Both forms:** statement (`case L: …`) and expression (`case L, M => expr`),
   usable as an assignment RHS.
2. **Fall-through:** none by default; trailing bare `continue` falls through.
   Nested-loop `continue`/`break` keep loop meaning. `break` is not required.
3. **Subjects:** enums and equality-comparable primitives; bare enum labels
   resolve from the subject type.
4. **Exhaustiveness:** error for expressions (all enum members or `default`;
   non-enum requires `default`); warning for non-exhaustive statements.
5. **`switch` supersedes F-002 `match`** — no separate `match` keyword in this
   design (see [TODO-FUTURE](../TODO-FUTURE.md#f-002-enum-match-exhaustiveness)).

## Consequences

- Lex/parse/sem/emit + IDE keywords/snippets/hover; example `examples/switch.pys`.
- ADR-006 deferred-match note points here.
- Security boundaries (ADR-001) unchanged.

## Rejected alternatives

- Implicit C-style fall-through (harder to teach; error-prone).
- Shipping a separate `match` keyword alongside `switch` (YAGNI).
- Requiring `break` at end of every case.
