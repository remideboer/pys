# CER-028: Explicit nullable values

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-05 |
| Scope | `lex`; `parse`; `sem`; Python emit; IDE/debugger; examples; docs/book |
| Architecture | [ADR-023](../adr/ADR-023-explicit-nullability.md) |

## Context

The literal `null` parsed and emitted as Python `None`, but semantic
assignability accepted it for every declared type. Null checks did not narrow a
binding, and the database teaching example converted SQL `NULL` to an empty
string.

## Entry 1 — explicit type and assignability

### Pre-behavior

`string name = null` compiled, `var value = null` inferred the pseudo-type
`null`, and signatures returning a plain entity could return `null`.

### Why it hurt

The declaration concealed absence and the compiler could not require a check.
Owned APIs and database mappers stated contracts that were not true.

### Post-behavior

`nullable<T>` is a recursive type expression. Plain `T` rejects `null`;
`nullable<T>` accepts `T` or `null`; bare-null inference is rejected. Invalid
nullable arguments and nullable entity identity receive stable diagnostics.

### Evidence

`tests/test_nullable.py` covers parser parity, assignment, inference, identity,
nested position, and result nesting.

## Entry 2 — conservative null-flow facts

### Pre-behavior

Null comparisons did not affect expression types. Member access after a check
and member access without a check were semantically indistinguishable.

### Why it hurt

There was neither safety nor useful compiler guidance.

### Post-behavior

Explicit checks narrow stable storage in the proven branch and after exiting
guards. Assignments and potentially mutating operations invalidate facts.
Shared values require a local snapshot. Nullable operations without proof fail
with `pys.nullable-use-before-check`.

### Evidence

BDD scenarios cover branches, guards, reassignment, switch handling,
short-circuit expressions, and invalidation.

## Entry 3 — SQL and PYS-facing fidelity

### Pre-behavior

The shop mapper's `cellStr` returned `""` for SQL `NULL`, and `NULLIF` converted
empty strings back to SQL `NULL`. Python `None` could appear in debugger values.

### Why it hurt

Two different domain/database states silently became one.

### Post-behavior

Nullable mapper contracts preserve `NULL` and `""` separately. A null in a
non-null field is a mapping error. Runtime storage remains Python `None`, while
PYS output, Watch, Variables, evaluate, and inline values display `null`.

### Evidence

Deterministic boundary tests cover null and empty-string round trips; Node tests
cover debugger value remapping.

## Trade-offs

- No wrapper allocation or force-unwrap syntax.
- No schema inference.
- Flow analysis rejects uncertain mutable/shared cases instead of attempting
  whole-program alias analysis.
