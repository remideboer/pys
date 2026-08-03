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

- `find_usages(path, symbol)` lex-scans `.pys` files in the same package folder
  for IDENT tokens matching the last dotted segment (skips keywords/primitives;
  ignores strings/comments).
- CLI: `python -m transpiler.ide <file.pys> --usages <symbol>`.
- Extension registers `ReferenceProvider` and **Find Usages** on
  `editor/context` (`pys.findUsages` → `editor.action.referenceSearch.trigger`).
- Extension **0.0.56**.

### Evidence

`tests/test_ide_usages.py`.
