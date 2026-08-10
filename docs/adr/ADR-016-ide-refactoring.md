# ADR-016: IDE educational refactoring (binding-aware plans)

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-03 |
| Code detail | [CER-018](../evolution/CER-018-ide-refactoring.md) |
| Related | [ADR-001](ADR-001-trust-boundaries.md), [ADR-015](ADR-015-enforced-ordering.md) |

## Context

PYS is an educational language. Students need IntelliJ-style refactoring
(preview, conflicts, undo) with Fowler-aligned teaching tips — not blind
search-replace. Find Usages previously used lexical IDENT scans (CER-016),
which is unsafe for Rename.

## Decision

1. **Educational core DoD:** Rename, Extract Variable, Extract Function/Method,
   Inline Variable/Function, Safe Delete, Introduce Parameter.
2. **Binding-aware references** drive Find Usages and all refactors (import graph
   + scopes). Lexical same-folder scan is not the DoD path.
3. Engine lives in `transpiler/refactor/`; IDE process (`python -I`, bundled root,
   `PYS_WORKSPACE_ROOT`) returns `RefactorPlan` JSON; extension applies
   `WorkspaceEdit` after preview (native undo).
4. Teaching catalog metadata (what/why) surfaces in CodeActions / preview.
5. Extract into class/entity respects member kind order (ADR-015).
6. Full Fowler catalog deferred ([F-005](../TODO-FUTURE.md#f-005-full-fowler-refactor-catalog)).
7. **Create Class from call** (CER-056): educational stub generation for an
   unresolved `Type(name: …)` call — not a Fowler refactor; lives beside the
   educational core without expanding F-005.

## Consequences

- Extension ≥ 0.0.57: RenameProvider, refactor CodeActions; context menu keeps
  common techniques flat and rarer ones under “More Refactorings” (≥ 0.0.63).
- Preview dialog shows resulting code (diff) before apply (≥ 0.0.64).
- Extension ≥ 0.0.97: analysis-driven completions + Create Class (CER-056).
- Trust boundary unchanged (ADR-001).

## Rejected alternatives

- Lexical rename with user exclusion only (insufficient for teaching binding).
- Applying edits inside Python (loses editor undo / multi-doc UX).
- Shipping the entire Fowler catalog in one release.
