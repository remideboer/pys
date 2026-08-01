# ADR-004: PEG-capable front-end (lexer separate, packrat optional)

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-01 |
| Commits | (performance branch — CER-003) |
| Code detail | [CER-003](../evolution/CER-003-peg-frontend.md) |

## Context

Remaining compile cost after CER-002 sat in lexer internals and parse walks.
[PEP 617](https://peps.python.org/pep-0617/) and
[CPython’s Parser](https://github.com/python/cpython/tree/main/Parser) show a
maintainable shape: tokenizer separate from a PEG / packrat parser, grammar
actions building AST directly, dual-run migration before flipping defaults.

A full C/`pegen` port is out of scope for a pure-Python teaching toolchain.

## Decision

1. **Lexer stays** in `transpiler/lex.py` (CPython tokenizer-vs-parser split).
2. **Productions stay** in `transpiler/parse.py`, aligned with `docs/language.ebnf`.
3. **Packrat / PEG mode** is `parse_program_from_tokens(..., engine="peg")` via
   `transpiler/peg.py` — same rules, per-parse memo on `(rule, position)`.
4. **Default engine remains classic RD** until measurement shows packrat ≤ RD
   wall time on the standard corpus (this grammar rarely backtracks).
5. **Dual-run tests** (`tests/test_peg_dual_run.py`) keep PEG AST-equal to RD.
6. No third-party parser dependency; no C extension; AST → sem → emit unchanged.

## Consequences

- Future grammar growth can lean on packrat without a rewrite.
- Flipping `_BRACE_ENGINE` to `"peg"` requires a new CER measurement, not taste.
- Indent/legacy mode stays on the non-PEG indent path.

## Rejected alternatives

- Porting CPython `pegen` / generating C
- Adopting Lark / another parser library as the runtime front-end
- Fusing lex+parse (no token list) before exhausting simpler wins
