# CER-043: Library decorator application

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-08 |
| Scope | `transpiler/lex.py`, `parse.py`, `ast_nodes.py`, `emit/python.py`, docs |
| Extends | [ADR-026](../adr/ADR-026-library-decorators.md) |

## Context

Absolute “no `@` in PYS” blocked FastAPI-style library field research.

## Entries

### 1. `@expr` before function / class / method

- **Pre-behavior:** `@` was a lex error / unused; docs forbade all source `@`.
- **Post-behavior:** `@expr` stacks attach to `FunctionDef` / `ClassDef` /
  `MethodDef`; emit `@…` before Python `def`/`class`. Illegal targets raise
  `pys.decorator-target`.
- **Evidence:** `tests/test_decorators.py`.

## Trade-offs

- Sem does not interpret decorator meaning (library-defined at runtime).
- Analyze/transpile still does not import third-party packages for typing
  (ADR-001).
