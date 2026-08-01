# CER-004: Identity-free struct types

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-01 |
| Commits | `8af7db8` (initial), hardening follow-up |
| Scope | `lex.py`, `ast_nodes.py`, `parse.py`, `sem.py`, `imports.py`, `emit/python.py`; `docs/language.ebnf`; `examples/structs.pys`; `tests/test_structs.py` |
| ADRs | [ADR-005](../adr/ADR-005-structs-as-value-types.md) |

## Context

The language had classes and collection types but no value-type product for
fixed-field records. Callers used classes as data bags or untyped `dict`s.

---

## 1. Grammar / AST

**Symbols:** `StructDef`, `StructField`; keyword `struct`; `docs/language.ebnf`.

### Pre-behavior

No `struct` keyword or declaration form.

### Why it hurt

Could not express identity-free records with a canonical constructor and
mutability matrix from the requirements.

### Post-behavior

`[top_visibility] [fix] struct Name [<T,…>] { [fix] type name [= expr] }`.
Fields are always public (no per-field access modifiers); `top_visibility`
controls who may import the type. Parser rejects field `public`/`private`/…,
`inherits` / `super` / `sealed` / `implements`, and `new`.

### Evidence

`tests/test_structs.py` (lex keyword, SA parse errors); EBNF structs section.

---

## 2. Semantics

**Symbols:** `sem._check_structs`, `imports.module_info_from_ast` struct maps.

### Pre-behavior

No struct registry; no SA for shared/null/fix-field/ctor arity.

### Post-behavior

Struct types registered locally and across imports. Enforces SA-1/2/6/7/9/10-style
rules and binding mutability for field writes.

### Evidence

Parametrized reject cases in `tests/test_structs.py`.

---

## 3. Emit / value copies

**Symbols:** `emit.python._struct`, `_pys_struct_copy`, `_copy_if_struct`.

### Pre-behavior

N/A.

### Post-behavior

`@dataclass` / `@dataclass(frozen=True)` when all fields immutable; `__hash__ =
None` when mutable; `_pys_copy` + wrapper copies at assign/call/return.

### Evidence

`examples/structs.pys` run; copy-on-call test (`before.amount` stays 10).

---

## 4. Hardening (access, precise copies, runtime fix fields)

### Pre-behavior (after initial land)

- Struct field access modifiers were parsed but not checked via `_check_oop`.
- Emit wrapped nearly every call arg/assign/return with `_pys_struct_copy` when
  any struct existed in the module.
- Mixed fix/mutable structs relied on static rejection only.

### Post-behavior

- Struct fields register as public in the OOP member map; unknown fields error.
  Per-field access modifiers are a parse error (type-level visibility only).
- Emit tracks binding / function return types and copies only struct-typed values.
- Partial-fix structs emit `__setattr__` guards for fix fields.
- Grammar keyword `struct` highlighted in `pys.tmLanguage.json`.

### Evidence

`tests/test_structs.py` access, precise-copy, and runtime-guard cases.

## Trade-offs

- Method return types used as `fn_return_types[name]` can collide across classes
  with the same method name (pre-existing overload naming limits).
- Fully frozen structs still rely on dataclass `frozen=True` (no custom setattr).
