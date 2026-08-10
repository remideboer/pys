# CER-057: Fail-closed unknown types at all use sites

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-10 |
| Commits | (this change set) |
| Scope | `transpiler/sem.py` (`_check_library_types`, `_collect_type_atoms`, …); `tests/test_unknown_type_sites.py`; `pys-language/extension.js` (diagnostic range for `pys.unknown-type`) |
| ADRs | [ADR-001](../adr/ADR-001-security-boundaries.md) / [CER-001](CER-001-security-boundaries.md) §7 (soft-open library types when introspection is off); [CER-056](CER-056-intellisense-completions.md) (`pys.unknown-type` → Create Class) |

## Context

Students writing `private Heritage heritage` before defining `Heritage` got no
compile/IDE error. Transpile succeeded and Python raised `NameError` only when a
`Heritage(...)` call ran.

### Pre-behavior

- `_check_library_types` only inspected **top-level** `AssignStmt.declare_type`
- Class/entity/struct/data **fields**, **params**, **returns**, nested decls,
  generic args (`list<Heritage>`), and PascalCase `TypeName(...)` calls were not
  existence-checked
- Emit still produced `Heritage(...)` → runtime `NameError`

### Why it hurt

- Fail-open on the most common teaching sites (fields + ctor args)
- IDE Create Class / red paint never fired for field annotations
- Runtime failure looked like a Python bug, not a missing type

### Post-behavior

- Same `pys.unknown-type` diagnostic walks **all** annotation sites and PascalCase
  bare callees (type-name convention); camelCase/lowercase callees stay
  library-open
- Generic args are collected (`nullable<Heritage>` flags `Heritage`)
- Class type parameters (`class Box<T>`) remain known inside the body
- CER-001 soft-true when imports exist and introspection is off is unchanged;
  unresolved names in a file that already imports libraries also stay soft
  (opaque driver types such as `MySQLCursor`) so library samples keep compiling
- IDE maps `pys.unknown-type` ranges onto the type token in the source line

### Evidence

- `tests/test_unknown_type_sites.py` (deny matrix + local allow + soft-open)
- `tests/test_deps.py::test_unknown_library_type_is_rejected` (regression)

## Trade-offs

- Does not invent hard errors for lowercase unknown callees (`print` / library
  helpers) — only PascalCase type-name calls
- Soft-open with any import still suppresses unverifiable third-party type names
  (CER-001); no-import student files fail closed
- `lambda<P… -> R>` atoms are the parameter/return types, not the raw `int -> bool` string
