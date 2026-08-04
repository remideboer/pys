# CER-021: Collection literals (dict / set / tuple)

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-04 |
| Commits | (collection literals increment) |
| Scope | `ast_nodes` Dict/Set/Tuple/BraceLiteral; `parse._parse_brace_literal` / `_parse_paren_primary`; `sem` brace assign checks; `emit.python` expected-type emit; tests; LANGUAGE/EBNF/railroad; book; `examples/collection_literals.pys` |
| ADRs | [ADR-018](../adr/ADR-018-collection-literals.md) |

## Context

Documented collection literals did not round-trip through the toolchain. The
beginner book imported builtins; empty `dict… = {}` emitted as a list.

### Pre-behavior

- `{…}` → `ArrayLiteral` → Python `[…]` in expression emit.
- `{k: v}` failed at parse (`Expected RBRACE, got COLON`).
- `(a, b)` failed (parens grouped one expression only).
- `int[]` / `int[][]` brace inits worked only via `ArrayDecl` + `ArrayLiteral`.

### Why it hurt

- Spec/book lied relative to emit; students could not write LANGUAGE.md samples.
- Empty dict silently became a list (`[]`), breaking keyed assignment at runtime.

### Post-behavior

- Tuple / dict / brace AST nodes; type-directed brace resolution (ADR-018).
- `dict<string, int> ages = {}` emits `{}`; sets and tuples emit Python forms.
- Unkeyed braces under `dict` and untyped `var x = {}` raise educational errors.
- Nested `int[][]` / slot assigns still use `array.array` (regression tests).

### Evidence

- `tests/test_collection_literals.py`
- `tests/test_multidim_arrays.py` (brace array regression)

## Trade-offs

- Call-argument / return expected types for braces are not fully threaded yet;
  declaring assigns and array contexts cover the LANGUAGE.md surface.
- Bare `dict()` / `set()` / `tuple()` calls remain valid but are not required.
