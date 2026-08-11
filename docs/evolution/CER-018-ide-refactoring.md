# CER-018: Binding-aware refs and educational IDE refactoring

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-10 |
| Commits | (ide-refactoring; rename sites; live editor preview) |
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
- **Member / type / interpolation sites (extension ≥ 0.0.98):** field and method
  uses resolve via receiver type (`this`/`self` → enclosing type; typed locals →
  nominal type; inheritance via `type_parents`). Typed decls and ctor callees
  record type-name uses. `{…}` holes in interpolated strings are parsed and
  linked the same way. Rename / Find Usages share this index — binding-aware
  only (not lexical “every identical string”).
- `RefactorPlan` JSON with catalog teaching fields; ops: rename, extract-*,
  inline-*, safe-delete, introduce-parameter.
- Extension 0.0.57: F2 RenameProvider, Refactor menu, CodeActions, preview
  QuickPick then `WorkspaceEdit`.
- Extension 0.0.63: context menu shows common techniques flat (Rename, Extract
  Variable/Function); rarer ones under click-to-open “More Refactorings”
  (VS Code hover-open submenus are unreliable). Titles are names only.
- Extension 0.0.64: preview dialog showed a live “Code after refactor” Beside
  webview diff (superseded for apply UX below).
- Extension ≥ 0.0.98: binding-aware rename covers field/method/`this`/
  interpolation/type+ctor sites.
- Extension ≥ 0.0.99: refactor **apply** preview is **live in the editor** —
  edits are applied temporarily; orange strikethrough = old span, blue =
  proposed text in buffer; Accept keeps / Reject restores. Name prompts still
  use lightweight `showModalInput`. F2 RenameProvider uses the same live
  preview (empty WorkspaceEdit when already applied).
- Extension ≥ 0.0.100: rename resolves caret on exclusive end of a site;
  refactor CLI uses `--stdin` live buffer; menu Rename / Extract / More sit in
  the `navigation` group with Find Usages (under Go to Definition peers).
  Pre-modal editor selection is used after name prompts.
- Extension ≥ 0.0.101: Rename uses the at-cursor rename widget (`editor.action.rename` /
  F2). Live preview Accept/Reject are CodeLens on the changed line plus a sticky
  `ignoreFocusOut` input bar — no toast.
- Extension ≥ 0.0.101 (menu order): editor context is
  Run → Debug → Rename → Extract Function|Method (`pys.inClassBody`) →
  **Refactor** submenu (Extract Variable + inline/safe-delete/introduce) →
  (built-in Go to Definition / Declaration) → Find Usages → **Generate**
  submenu (Constructor/toString/override/getters/test placeholders disabled;
  Create Class enabled) → Reveal in OS (`revealFileInOS`) → remaining PYS
  extras. See `test/context-menu-order.test.js`.
- CLI: `--refactor-plan <op> …`; `--usages` accepts `--line` / `--column`.

### Evidence

`tests/test_refactor.py` (field/`this`, method call, class type+ctor,
interpolation), `tests/test_ide_usages.py`; `pys-language/test/refactor.test.js`;
teaching J-refactor / S8.

## Trade-offs

- Extract/inline heuristics are intentionally narrow for DoD (e.g. inline
  function = single `return expr`).
- Standalone `{ }` statement blocks are not in the grammar; shadowing demos use
  `if` bodies.
- Deferred Fowler ops listed as F-005.
