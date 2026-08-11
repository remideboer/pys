# CER-062: Whole-file document formatter

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-11 |
| Scope | `transpiler/format.py`; `transpiler/ide.py` `--format`; `pys-language` DocumentFormattingEditProvider + context menu |
| Spec | [requirements/document_formatter.md](../../requirements/document_formatter.md) |
| ADRs | [ADR-015](../adr/ADR-015-enforced-member-ordering.md) (kind order); [ADR-001](../adr/ADR-001-security-boundaries.md) (IDE path containment) |

## Context

Students need a familiar **Reformat Code in File** action (context menu, Edit
menu, `Shift+Alt+F` / format-on-save). Indent quick fixes (CER-053) only repair
one line; there was no AST pretty-printer.

### Pre-behavior

- No `DocumentFormattingEditProvider`; no `pys.formatDocument`
- Only CER-053 `pys.indent` line quick fixes

### Why it hurt

- No muscle-memory format path; messy buffers stayed messy after fixes

### Post-behavior

- `format_source` / `format_module` pretty-print **brace-mode** ASTs that already
  parse: 4-space indent, K&R `{`, ADR-015 kind order (stable within kind), blank
  line before each method/ctor, enum 1-line vs multi (≤4 + soft 100 cols), param
  wrap, blank-line collapse, trailing WS strip, final newline
- Blank lines follow a sparse Java-like rule: none between fields of the same
  kind; one blank before each method/ctor (and between kind sections); one blank
  between top-level types/functions. Source `BlankStmt`s are not echoed.
- Parse failure / non-brace → no-op (`None` / empty edits); existing diagnostics
  surface the error
- **Not** repaired by format: illegal tabs, wrong kind order (parse-first),
  casing renames, visibility/`static` injection, import alphabetization,
  `tasks { }` reorder
- IDE: `--format` + `--stdin`; extension registers formatting provider +
  context menu `1_modification` (“Reformat Code in File”)

### Evidence

- `tests/test_format.py` (idempotency + goldens)
- `pys-language` menu order test includes format command

## Trade-offs

- House style (100-col soft wrap, blank collapse, same-line `{`) is formatter
  convention, not LANGUAGE FatalParseError
- Interface round-trip prefers original source slice (AST drops signatures)
- Range formatting deferred (spec §7 follow-up)
- Legacy indent-mode files are not formatted in v1
