# CER-016: Find Usages for PYS identifiers

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-03 |
| Commits | (find-usages increment) |
| Scope | `transpiler/ide.py` `find_usages`; `pys-language` ReferenceProvider + context menu |
| ADRs | (IDE navigation; complements go-to-definition) |

## Context

Go-to-definition existed, but the editor context menu had no Find Usages path
for the identifier under the cursor.

### Pre-behavior

- `lookup_symbol` / DefinitionProvider / DeclarationProvider only.
- No ReferenceProvider; no `pys.findUsages` menu entry.

### Post-behavior

- Binding-aware `find_usages` / `refactor.refs` (CER-018): resolves the
  declaration under the cursor (or by symbol) across the import graph and
  returns only sites of that binding. CLI supports `--line` / `--column`.
- Extension registers `ReferenceProvider` and **Find Usages** on
  `editor/context` (`pys.findUsages` → `editor.action.referenceSearch.trigger`).
- Extension **0.0.57** (refactoring track); Find Usages shipped earlier as 0.0.56.

### Evidence

`tests/test_ide_usages.py`, `tests/test_refactor.py`.
