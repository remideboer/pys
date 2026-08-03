# CER-019: Multi-dimensional arrays

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-03 |
| Commits | (multi-dim arrays increment) |
| Scope | `ast_nodes.ArrayDecl` / `ArrayAlloc`; `parse.py` dims + brace init; `sem._check_arrays`; `emit.python` nested `array.array` |
| ADRs | — (language surface; no trust-boundary change) |

## Context

Arrays were 1D only (`int[]` / `int[n]`). Students comparing with Java expected
`int[][]` and brace initializers; nesting via `list<list<int>>` is the wrong
teaching form (not the performant array path).

### Pre-behavior

- Parser accepted a single `[]` / `[n]` after the element type.
- Emit always produced one `array.array` (or a string list).
- `int[][]` failed at parse (`Expected IDENT, got LBRACK`).

### Why it hurt

- No innate multi-dim array construct; forced `list<list<…>>` for grids.
- Java-style examples from teaching materials did not transpile.

### Post-behavior

- Rank ≥ 1 **unsized** decls: `T[]`, `T[][]`, `T[][][]` (length from initializer).
  Sized decl types (`int[3] xs = …`) are a parse error; sizes belong only on
  RHS allocation expressions.
- Initializers: nested `[…]` or `{…}` brace literals in expression position.
- Allocation expr (no `new`): `int[3][][]`, `int[2][3]` → outer containers +
  innermost `array.array` (zero-filled when sized) or `[None] * n` when trailing
  dims are unsized.
- Sem checks nested literals; types register as `elem` + `[]` * rank.
- Outer ranks are Python lists of nested arrays (stdlib `array.array` cannot
  hold object rows); leaf numeric/bool storage remains `array.array`.
- Foreach binders may use array types: `loop (int[] row in grid)`.

### Evidence

`tests/test_multidim_arrays.py`; existing 1D array tests still green.
Showcase: [`examples/arrays.pys`](../../examples/arrays.pys) (nested
`loop (int[] row in …)` / indexed loops; also a short section in
`examples/main.pys`).

## Trade-offs

- Not a single flat buffer / numpy ndarray — keeps emit readable for teaching.
- Outer ranks are Python lists of nested arrays; leaf numeric/bool storage is
  `array.array`. Slot assigns of nested `{…}` / `[…]` re-emit through the same
  path (not plain Python lists).
- Semicolons after decls remain non-tokens (PYS statement style unchanged).
