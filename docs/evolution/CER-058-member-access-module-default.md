# CER-058: Omitted member access defaults to `module`

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-11 |
| Extends | [ADR-027](../adr/ADR-027-constructor-keyword.md) / [CER-045](CER-045-constructor-keyword.md) §5 |
| Scope | `parse.py` (`_member_access_or_module`); `sem.py`; EBNF / railroad / LANGUAGE; TextMate; tests |

## Context

Bare `constructor` already defaulted to `module`. Fields and methods still
required an explicit access modifier, so `string name` / `greet(){ }` failed
while `constructor(){ }` worked — inconsistent for teaching.

### Pre-behavior

- Class/entity fields, methods, and abstract methods: omitted access → parse or
  sem error (“require an access modifier”)
- Constructors only: omitted ⇒ `module`

### Why it hurt

Students write members the same way they write top-level types (no prefix =
module). Forcing `module`/`public` on every field and method added chrome
without changing the common same-file case.

### Post-behavior

- **All** class and entity members (`const` / `fix` / mutable fields, methods,
  abstract methods, constructors): omitted `member_access` ⇒ `module`
- Explicit `public` / `private` / `protected` / `module` still allowed
- Struct/data (always public) and interface signatures (no access) unchanged
- Sem empty-access reject removed (parse always fills `module`)

### Evidence

- `tests/test_constructor_keyword.py` (bare method)
- `tests/test_transpiler_brace_blocks.py` / `tests/test_sem.py` (bare field)
- `tests/test_member_access_module_default.py`

## Trade-offs

- Does not change what `module` means (same-file)
- Does not default struct/data/interface access models
- Legacy `language_spec` line translator still requires an explicit access
  modifier on **methods** (optional access without a return type would also
  match `print(...)` / `super(...)`). Bare members are handled by the AST
  pipeline (`parse.py`).
