# CER-047: Class `static` members

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-08 |
| Extends | [ADR-029](../adr/ADR-029-static-members.md) |
| Scope | `lex.py`, `parse.py`, `ast_nodes.py`, `sem.py`, `emit/python.py`, book, IDE |

## Context

No class-level `static` existed; only instance members and top-level `const` /
module state.

## Entries

### 1. Keyword + grammar

- **Pre-behavior:** `static` not a keyword; no class-wide members.
- **Post-behavior:** `static` after visibility on fields and methods; EBNF /
  railroad updated.
- **Evidence:** `tests/test_static_members.py`.

### 2. Semantics

- **Post-behavior:** `this` banned in static methods; `static` incompatible with
  `open`/`override`/`override closed`; `static const` allowed (redundant).
- **Evidence:** same test module.

### 3. Emit

- **Post-behavior:** `@staticmethod` without `self`; static fields as class
  attributes.
- **Evidence:** emit asserts in `test_static_members.py`.

### 4. Type-name static calls + Create Static Method QuickFix

- **Pre-behavior:** `Character.greet()` skipped OOP checks (`ClassDef` names were
  not type-level receivers); missing members had no diagnostic code / QF.
- **Post-behavior:** Type-name receivers resolve via `class_members` /
  `class_names`. Missing `TypeName.method(...)` → Error
  `pys.undefined-static-method` with `suggested_fix=create-static-method`.
  Instance members accessed as `TypeName.member` → `pys.instance-member-via-type`.
  QuickFix / `pys.generate.createStaticMethod` inserts
  `public static …` inferred from call args and assignment return type
  (`refactor/create_static_method.py`).
- **Evidence:** `tests/test_undefined_static_method.py`; IDE CodeAction gated on
  `suggested_fix=create-static-method`.

## Trade-offs

- Keep `static` spelling for C#/Java/JS transfer; teach via memory model rather
  than rename.
- Create Static Method scaffolds a stub body (`return` default / empty `void`);
  students fill real logic.
