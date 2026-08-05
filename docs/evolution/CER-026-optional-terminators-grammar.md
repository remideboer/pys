# CER-026: Optional `;`, C-for `;`, comma enums, multi-label switch

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-05 |
| Scope | `parse.py`, `ast_nodes.py` (`SwitchCase.brace_scoped`), `sem.py`, `emit/python.py`, `refactor/refs.py`, `language_spec.py`; EBNF/railroad/LANGUAGE; `pys-language` snippets; examples/book/tutorials/golden; `tests/test_statement_terminator.py` |
| ADRs | [ADR-022](../adr/ADR-022-optional-terminators-grammar.md) |

## Context

Four related grammar changes from
`requirements/enum_optional_statement_terminator.md` needed parse-first delivery
with corpus migration and teaching/spec updates.

---

## 1. Optional statement terminator + same-line rule

**Symbols:** `_finish_stmt_terminator`, `_check_same_line_boundary`;
`TokenKind.SEMI` (already lexed).

### Pre-behavior

No `;` consumption after statements. Two declarations on one line could not be
written; the second token was a parse error without an actionable same-line tip.

### Why it hurt

Related short bindings had to occupy separate lines; no way to mark an intentional
same-line boundary.

### Post-behavior

After each real statement (module body, blocks, bare switch arms), optionally
consume one `SEMI`. If the next non-noise statement token shares the previous
statement’s end line and no `;` was consumed → `FatalParseError`
`pys.same-line-statements` with tip to insert `;` or split lines. Trailing `;`
always allowed.

### Evidence

`tests/test_statement_terminator.py` (same-line with/without `;`, trailing `;`).

---

## 2. C-for header separators `,` → `;`

**Symbols:** `_parse_loop`; `language_spec` `loop_general` regex.

### Pre-behavior

`loop (int i = 0, i < n, i++)`.

### Why it hurt

Diverged from C#/Java and from PYS’s new statement `;`.

### Post-behavior

Headers use `;`. Two top-level commas without two semis → migrate error
`pys.c-for-semi`. ADR-019 single-counter rule unchanged.

### Evidence

Focused terminator tests; migrated examples/book/JIT/golden; `test_language_spec`.

---

## 3. Comma-delimited enum members

**Symbols:** `_parse_enum`.

### Pre-behavior

Members juxtaposed (newline or whitespace); no commas.

### Post-behavior

`enum_member_list = member { "," member } [ "," ]`. Missing comma between
members → `pys.enum-member-comma`.

### Evidence

`tests/test_enums.py`; `examples/enums.pys`; JIT `J-enum`.

---

## 4. Switch statement multi-label + block bodies

**Symbols:** `_parse_switch_stmt_body`; `SwitchCase.brace_scoped`; sem/refs/emit.

### Pre-behavior

Statement arms: one label only; bare statement sequence only. Expression arms
already allowed multi-label.

### Post-behavior

Statement arms accept `{ "," case_label }` and optional `{ }` body.
`brace_scoped=True` → nested binding check + emit `brace_scope=True` (CER-015).
Bare sequence shares enclosing scope for decls. Fall-through still trailing
`continue`.

### Evidence

`tests/test_statement_terminator.py` (multi-label + block; brace mangling vs bare).

## Trade-offs

- Breaking change for C-for commas and juxtaposition enums (intentional).
- Do not restore multi-var C-for headers or universal mandatory `;`.
