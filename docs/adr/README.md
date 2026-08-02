# Architecture Decision Records (ADRs)

ADRs capture **system-level** choices: boundaries, trust model, dependency
strategy, packaging, IDE vs CLI contracts. They answer “what shape should the
system keep?” — not “which function was slow?”

Code-level history (pre/post behavior of specific symbols) lives in
[`../evolution/`](../evolution/README.md) as **CERs**. Both are project memory:
**look back** before changing related code, and **write forward** (amend, add,
or supersede) in the same change set when a decision moves. See
`.cursor/rules/project-memory.mdc`.

## When to write or update an ADR

Write or update an ADR when the change:

- Alters a security or trust boundary
- Changes how deps / locks / interpreters are resolved
- Redesigns the compile pipeline stages or IDE helper contract
- Introduces a new backend, packaging channel, or public CLI surface
- Reverses or supersedes a previous ADR

Do **not** use an ADR for a local refactor or a measured micro-optimization —
that belongs in a CER (or a commit message if too small to record).

## Format

```markdown
# ADR-NNN: Title

| | |
| --- | --- |
| Status | Proposed / Accepted / Superseded by ADR-XXX |
| Date | YYYY-MM-DD |
| Commits | optional SHAs |

## Context
## Decision
## Consequences
## Rejected alternatives
```

## Index

| ID | Title | Status |
| --- | --- | --- |
| [ADR-001](ADR-001-trust-boundaries.md) | Trust boundaries for IDE, transpile, and run | Accepted |
| [ADR-002](ADR-002-hashed-dependency-locks.md) | Hashed, fail-closed dependency locks | Accepted |
| [ADR-003](ADR-003-measure-before-optimize.md) | Measure before optimize; record lasting perf fixes as CERs | Accepted |
| [ADR-004](ADR-004-peg-frontend.md) | PEG-capable front-end (lexer separate, packrat optional) | Accepted |
| [ADR-005](ADR-005-structs-as-value-types.md) | Structs as identity-free value types | Accepted |
| [ADR-006](ADR-006-enums-as-nominal-sets.md) | Enums as nominal closed sets | Accepted |
| [ADR-007](ADR-007-int-literals-and-widths.md) | Binary/hex literals, bitwise, width aliases | Accepted |
| [ADR-008](ADR-008-switch-stmt-and-expr.md) | Switch statement and expression | Accepted |
| [ADR-009](ADR-009-traits-composition.md) | Traits as composition (not types) | Accepted |
| [ADR-010](ADR-010-abstract-classes.md) | Abstract classes as nominal incomplete types | Accepted |

Related: [`../ARCHITECTURE.md`](../ARCHITECTURE.md) · [`../evolution/`](../evolution/README.md).
