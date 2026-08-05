# ADR-022: Optional `;`, C-for `;`, comma enums, multi-label switch arms

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-05 |
| Code detail | [CER-026](../evolution/CER-026-optional-terminators-grammar.md) |
| Requirement | [`requirements/enum_optional_statement_terminator.md`](../../requirements/enum_optional_statement_terminator.md) |

## Context

PYS used newlines as the sole statement boundary, juxtaposed enum members, and
comma separators in C-style `loop` headers. That blocked same-line related
declarations, diverged from C#/Java `for` headers, tied enum layout to line
breaks, and left statement `switch` arms without expression-form multi-labels
or explicit `{ }` bodies.

## Decision

1. **Optional `;` statement terminator** — never required when a statement is
   alone on its line; **mandatory** between two statements on the same physical
   line (`pys.same-line-statements`); trailing `;` always allowed.
2. **`c_for_loop` separators** are `;` (breaking vs prior `,`). Single-counter
   immutability from [ADR-019](ADR-019-single-counter-loops.md) is unchanged —
   only the separator token changes.
3. **Enum members** are comma-delimited with an optional trailing comma
   (breaking vs juxtaposition). Layout has no semantic meaning.
4. **Switch statement arms** allow comma-separated multi-labels (parity with
   expression arms) and either a bare statement sequence or an explicit
   `block`. Block form introduces nested lexical scope ([CER-015](../evolution/CER-015-block-scope.md));
   fall-through remains trailing `continue` only.

## Consequences

- Corpus / book / JIT / goldens migrate C-for `,` → `;` and enum commas.
- Old comma C-for headers and juxtaposed enums are FatalParseError with tips.
- Specs: EBNF, railroad, LANGUAGE; IDE snippets for loop/enum/switch.
- Does **not** restore multi-variable C-for headers or make `;` universal.

## Rejected alternatives

| Alternative | Why rejected |
| --- | --- |
| Mandatory `;` on every statement | Reintroduces ceremony PYS avoided by newline termination |
| Keep `,` in C-for headers | Diverges from C#/Java and from PYS statement `;` |
| Keep juxtaposition enums | Layout still carried grammar weight; no trailing-comma story |
| Invent non-`block` switch grouping | Reuse existing `block` for scope + teaching consistency |

## Related

- Amends [ADR-019](ADR-019-single-counter-loops.md) (separator only)
- Amends [ADR-006](ADR-006-enums-as-nominal-sets.md) / [CER-005](../evolution/CER-005-enums-and-warnings.md)
- Amends [ADR-008](ADR-008-switch-stmt-and-expr.md) / [CER-007](../evolution/CER-007-switch-stmt-and-expr.md)
