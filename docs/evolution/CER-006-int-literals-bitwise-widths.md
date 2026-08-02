# CER-006: Binary/hex literals, bitwise ops, width aliases

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-02 |
| Commits | (int literals increment) |
| Scope | `lex.py`, `parse.py`, `sem.py`, `emit/python.py`, `ide.py`, `language_spec.py`; `pys-language/*`; `docs/*`; `examples/int_literals.pys`; `tests/test_int_literals.py` |
| ADRs | [ADR-007](../adr/ADR-007-int-literals-and-widths.md) |

## Context

Decimal-only ints blocked hardware teaching samples using `0b` / `0x` and
bitwise masks.

### Pre-behavior

Lexer accepted only `\d+` / floats; no `&|^~<<>>`, no width type names.

### Post-behavior

- Lex: binary/hex/`_` separators; ops including deferred `<<<`/`>>>` tokens.
- Parse: bit_or / bit_xor / bit_and / shift / power; `xor` / `shift left|right`;
  rotate rejected with tip. Generic closers split `>>` / `>>>` so
  `list<tuple<int, string>>` still parses alongside shift ops.
- Sem: unsigned width ranges; int-like checks for bitwise/`~`/`//`/`**`.
- Emit: passthrough literals and Python bitwise/power/floor-div.
- IDE: TextMate numbers/ops/types; hover; snippets; extension ≥ 0.0.39.
- Docs: LANGUAGE, EBNF, railroad, JIT, ADR-007.

### Evidence

`tests/test_lex.py`, `tests/test_int_literals.py`; `examples/int_literals.pys`
with workspace-isolated `run_source` (CER-001 §4).

## Trade-offs

- Width names look “signed” (`int16`) but ranges are unsigned per requirements
  sample prints — documented explicitly.
- Rotate left for a dedicated increment.
