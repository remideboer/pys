# ADR-015: Grammar-level member and import ordering

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-03 |
| Code detail | [CER-017](../evolution/CER-017-enforced-ordering.md) |
| Source | [`requirements/enforced_ordering.md`](../../requirements/enforced_ordering.md) |

## Context

Style guides (Checkstyle, StyleCop, PEP 8) recommend constants → fields →
constructors → methods and imports-at-top, but mainstream compilers do not
reject out-of-order **kinds**. PYS already makes related conventions structural
(`requires`, `identity(...)`). Free-form class/struct/trait/entity bodies and
scattered imports forced readers to scan for category and taught ordering only
as optional taste.

Rationale (requirement): a fixed position for each kind reduces extraneous
cognitive load (Sweller) — structure itself carries category information so
working memory can focus on what the code does. Refactoring that changes a
member’s role is expected to *physically relocate* the declaration; that is
treated as a feature. Student material must say explicitly that Java/C#/etc.
will *not* reject out-of-order members — only the habit transfers.

## Decision

1. Enforce **kind** order in the recursive-descent parser via a section/phase
   cursor (ordered EBNF groups). Out-of-order members are `FatalParseError`
   with educational messages from the requirement §5 table — not a second
   semantic-only pass.
2. Ordering axis is **kind only**. Visibility (`public` / `private` / …) stays
   unordered within a section.
3. Bodies: class `const` → `fix` → mutable → constructors → methods (incl.
   `abstract`); struct `fix` → mutable; trait `requires` → methods; entity
   identity fields → other `fix` → mutable → constructors → methods.
4. Program: imports-only prefix (blank/comment allowed); late import is a parse
   error.
5. **Do not** enforce positional order inside `tasks { }` — DAG/`await` already
   covers dependency intent.

## Consequences

- Examples and GUI classes must place constructors before methods.
- Class fields may declare `const` / `fix` in their sections; emit reuses
  existing fix/immutability hooks where applicable.
- Teaching frames a **transferable habit**: other languages recommend; only PYS
  rejects at compile time ([S7](../../tutorials/supportive/S7-order-as-habit.md)).

## Rejected alternatives

- Sem-only / linter pass after a free-form grammar (weaker signal; duplicates
  diagnostics).
- Visibility as a second ordering axis (extra cognitive dimension).
- Positional rules inside `tasks` blocks.
