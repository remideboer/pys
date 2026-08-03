# Code evolution records (CERs)

These notes track **why the code changed**, not system architecture.

They sit between commit messages (too short) and ADRs (system-level decisions
in [`../adr/`](../adr/README.md)): each record describes a concrete pre-behavior,
the measurable or security cost of that behavior, and the post-behavior that
replaced it.

**Project memory (look back + write forward):** consult relevant CERs/ADRs before
changing related code, and **update or add** records in the same change set when
behavior or decisions move. Stale memory is a defect. Enforced by
`.cursor/rules/project-memory.mdc`.

## Format

| Field | Meaning |
| --- | --- |
| Status | `Accepted` once landed on the branch / merge commit |
| Date | When the change landed |
| Commits | Primary git SHA(s) |
| Scope | Files / symbols that moved |

Each record then uses:

1. **Context** — what the code was doing and for whom
2. **Entries** — one subsection per distinct code change:
   - Pre-behavior
   - Why it hurt
   - Post-behavior
   - Evidence (tests, benches, risk)
3. **Trade-offs** — what we deliberately did *not* change

## Index

| ID | Title | Theme |
| --- | --- | --- |
| [CER-001](CER-001-security-boundaries.md) | Harden security boundaries | Security |
| [CER-002](CER-002-compile-performance.md) | Cut redundant parse and filesystem work | Performance |
| [CER-003](CER-003-peg-frontend.md) | Lexer/deps wins + PEG-capable parse front-end | Performance |
| [CER-004](CER-004-structs.md) | Identity-free struct types | Language |
| [CER-005](CER-005-enums-and-warnings.md) | Enums + first-class compiler warnings | Language |
| [CER-006](CER-006-int-literals-bitwise-widths.md) | Binary/hex literals, bitwise, width aliases | Language |
| [CER-007](CER-007-switch-stmt-and-expr.md) | Switch statement and expression | Language |
| [CER-008](CER-008-traits.md) | Traits composition (`uses` / `requires`) | Language |
| [CER-009](CER-009-abstract-classes.md) | Abstract classes (`abstract` / `void`) | Language |
| [CER-010](CER-010-interface-method-access.md) | Interface methods omit access modifiers | Language |
| [CER-011](CER-011-data-and-entity.md) | `data` value objects and `entity` identity types | Language |

Related architecture overview: [`../ARCHITECTURE.md`](../ARCHITECTURE.md).
