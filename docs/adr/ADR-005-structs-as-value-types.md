# ADR-005: Structs as identity-free value types

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-01 |
| Commits | `8af7db8` + hardening follow-up |
| Code detail | [CER-004](../evolution/CER-004-structs.md) |

## Context

PYS needed a schema-fixed data carrier distinct from classes (behavior +
identity) and from `dict` (open keys, reference sharing). Requirements live in
`requirements/structs.pys`.

## Decision

1. **`struct` / `fix struct`** are first-class declarations (sibling to `class`).
2. **No identity features:** no methods, no `inherits` / `super` / `sealed` /
   `implements`; no `shared <Struct>`; no `null` for struct-typed fields/bindings.
3. **Construction:** existing `Type(...)` call form only (positional + named);
   reject `new`; no brace field literals.
4. **Pass-by-value:** emit copies on assign / call / return (`_pys_struct_copy` /
   `_pys_copy`).
5. **Equality / hash:** field-wise `==`; hashable only when type-fix or every
   field is `fix` (emit frozen dataclass when hashable).
6. **Type params** allowed (`struct Pair<T, U>`), erased like class generics.

## Consequences

- Sem enforces SA mutability / ctor rules; emit uses `@dataclass`.
- Pedagogy: JIT J-struct + supportive S6 contrast dict/class.
- Security boundaries (ADR-001) unchanged.

## Rejected alternatives

- Brace field literals / `new` constructors
- Reference semantics with optional clone
- Methods or inheritance on structs
