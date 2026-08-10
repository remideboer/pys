# CER-054 — Foreach binder type required + element match

| Field | Value |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-10 |
| Commits | (this change set) |
| Scope | `transpiler/parse.py` (foreach); `transpiler/sem.py` (`_check_foreach_binder`); EBNF / railroad; examples; book |

## Context

`loop (x in xs)` and mismatched binders such as `loop (string x in int[])`
compiled. Students expected an explicit element type that matches the
collection (see `requirements/rekenmachine.pys`).

## 1. Required binder type

### Pre-behavior

EBNF allowed optional `[ type_name ]`; parse left `var_type` empty; IDE only
emitted a soft `pys.untyped-loop-var` tip.

### Why it hurt

Untyped binders hid element types and blocked teaching “name the type you
iterate.”

### Post-behavior

- Grammar: `foreach_loop` requires `type_name`.
- Parse raises `FatalParseError` / `pys.foreach-type-required` when omitted.
- Examples and book use typed binders (including `object` for opaque library
  iterators).

## 2. Element type must match

### Pre-behavior

`loop (string x in arr)` with `int[] arr` typed the binder as `string` and
emitted a Python `for` without checking the array element type.

### Why it hurt

False sense of type safety; wrong teaching samples looked “valid.”

### Post-behavior

- `_check_foreach_binder` compares binder type to `_iterable_element_type` of
  the iterable’s declared type (`T[]`, `list<T>`, `set<T>`, `dict<K,V>` keys,
  uniform `tuple<…>`).
- Mismatch → `TranspileError` / `pys.foreach-type` with
  `suggested_fix=loop (Elem name in coll)`.
- When the collection type has no known element type (bare `dict` / `list`,
  library `object` iterators), only the required-type rule applies.

## Evidence

- `tests/test_foreach_types.py` (required, mismatch, match, rekenmachine
  negative)
- Fixture `requirements/rekenmachine.pys` (positive `int` binder; commented
  negatives)

## Trade-offs

- Corpus examples that used untyped foreach were updated in the same change
  set.
- Soft IDE hint `pys.untyped-loop-var` is largely superseded by the hard parse
  error (still harmless if a typed binder is present).
