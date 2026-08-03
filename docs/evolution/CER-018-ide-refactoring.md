# CER-018: Binding-aware refs and educational IDE refactoring

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-03 |
| Commits | (ide-refactoring increment) |
| Scope | `transpiler/refactor/*`; `ide.py` find_usages / `--refactor-plan`; `pys-language` RenameProvider + Refactor menu; spans `name_span` / end spans |
| ADRs | [ADR-016](../adr/ADR-016-ide-refactoring.md) |
| Amends | [CER-016](CER-016-find-usages.md) post-behavior |

## Context

Find Usages was package-folder lexical IDENT matching. Refactoring required
true declaration identity (shadowing, imports) plus previewable edit plans.

### Pre-behavior

- `find_usages`: same-folder lexer IDENT scan.
- No RenameProvider; no extract/inline/safe-delete/introduce-parameter.
- AST spans mostly point-only; no `name_span` on decls.

### Why it hurt

- Rename-by-text would corrupt shadowed names and unrelated symbols.
- No educational IntelliJ-style preview / conflict UX.

### Post-behavior

- `refactor/refs.py` builds a binding-aware index (scopes, import graph, enum
  members) and powers Find Usages + refactors.
- `RefactorPlan` JSON with catalog teaching fields; ops: rename, extract-*,
  inline-*, safe-delete, introduce-parameter.
- Extension 0.0.57: F2 RenameProvider, Refactor menu, CodeActions, preview
  QuickPick then `WorkspaceEdit`.
- Extension 0.0.63: context menu shows common techniques flat (Rename, Extract
  Variable/Function); rarer ones under click-to-open “More Refactorings”
  (VS Code hover-open submenus are unreliable). Titles are names only.
- CLI: `--refactor-plan <op> …`; `--usages` accepts `--line` / `--column`.

### Evidence

`tests/test_refactor.py`, `tests/test_ide_usages.py`; teaching J-refactor / S8.

## Trade-offs

- Extract/inline heuristics are intentionally narrow for DoD (e.g. inline
  function = single `return expr`).
- Standalone `{ }` statement blocks are not in the grammar; shadowing demos use
  `if` bodies.
- Deferred Fowler ops listed as F-005.
