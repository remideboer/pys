# ADR-018: Collection literals (dict / set / tuple) and type-directed braces

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-04 |
| Source | [`LANGUAGE.md`](../LANGUAGE.md) collection forms; beginner book workarounds |
| Related | [CER-021](../evolution/CER-021-collection-literals.md); [CER-019](../evolution/CER-019-multidim-arrays.md) |

## Context

LANGUAGE.md documented `dict… = {}`, `set… = {"a","b"}`, and
`tuple… = (1, "a", "b")`, but the toolchain treated every `{…}` as an array/list
initializer and parentheses as grouping only. The beginner book had to import
Python `dict` / `tuple` / `set` constructors. Meanwhile Java-style
`int[][] = { {…}, {…} }` (CER-019) must keep working.

## Decision

1. **Tuple literals** are parse-time: `()`, `(a,)`, `(a, b, …)`. A single
   parenthesized expression without a comma remains grouping.
2. **Keyed braces** `{k: v, …}` are always **dict** literals.
3. **Unkeyed / empty braces** `{…}` / `{}` are an unresolved brace form resolved
   by **expected type**:
   - `dict` → empty `{}` (unkeyed non-empty is an error — need `k: v`)
   - `set` → `set()` or `{e, …}`
   - `list` → `[…]`
   - `T[]` / array slot assign → existing array.array path (CER-019)
   - `var` / unknown → educational error (type the binding)
4. Struct / data **field** brace literals remain rejected (constructors only).

## Consequences

- Docs, EBNF, railroad, book, and `examples/collection_literals.pys` teach the real forms.
- Emit and sem share the resolution matrix; array regressions stay covered by
  multidim tests.

## Rejected alternatives

- Deprecating Java brace array init in favor of Python-only `{}` = dict/set.
- Always emitting `{}` as dict (breaks `int[][]` teaching).
- Requiring `dict()` / `set()` / `tuple()` calls as the only constructors.
