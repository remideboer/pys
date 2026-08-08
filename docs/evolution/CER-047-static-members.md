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

## Trade-offs

- Keep `static` spelling for C#/Java/JS transfer; teach via memory model rather
  than rename.
