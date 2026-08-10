# CER-055: Live buffer diagnostics + Error paint

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-10 |
| Commits | (this change set) |
| Scope | `transpiler/ide.py` (`analyze_file` `source=` / `--stdin`); `pys-language/ide-process.js` (`stdin`); `pys-language/extension.js` (validate + error decorations); parse `pys.trait-require-typo` |
| ADRs | [ADR-001](../adr/ADR-001-security-boundaries.md) (path containment unchanged); [ADR-009](../adr/ADR-009-traits-composition.md) / [CER-008](CER-008-traits.md) (`requires` spelling) |

## Context

IDE diagnostics already debounced on every keystroke, but the helper read the
**on-disk** file. Unsaved fixes left squiggles until save. Beginners also miss
thin squiggles on 1–2 character tokens (e.g. `require` vs `requires`).

### Pre-behavior

- `validateDocument` → `python -m transpiler.ide <path>` → `read_text` disk only.
- Errors: standard DiagnosticCollection squiggles only.
- Singular `require` briefly accepted as a synonym (reverted — teaching cost).

### Why it hurt

- Live edit / disk mismatch made diagnostics feel broken.
- Tiny squiggles are easy to overlook in a busy IDE.
- Keyword-highlighting `require` as a synonym taught the wrong spelling.

### Post-behavior

- Diagnostics pass `--stdin` + `document.getText()`; path still fail-closed for
  workspace containment (ADR-001). `analyze_file(..., source=...)` optional.
- All Error diagnostics also get a red text background decoration
  (`TextEditorDecorationType`) + overview ruler mark.
- `require Type name` → `pys.trait-require-typo` + quick fix to `requires`;
  `require` is **not** a keyword / not highlighted.

### Evidence

- `tests/test_ide_stdin_analyze.py`
- `tests/test_traits.py::test_require_singular_is_trait_require_typo`
- `pys-language/test/ide-process.test.js` (stdin write)

## Trade-offs

- Buffer analysis trusts the editor buffer for that contained path only — never
  bypasses path containment.
- Red paint applies to every Error severity (beginner visibility), not only the
  trait typo.
