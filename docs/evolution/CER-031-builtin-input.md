# CER-031: Builtin `input`

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-06 |
| Scope | `sem` (builtins + returns/params + arity); book; examples; highlighter |
| Architecture | (teaching I/O — no new ADR) |

## Context

Beginners had to write `import input from builtins` while `print` needed no
import. That mismatch was pure ceremony for console programs.

## Entry 1 — seeded builtin

### Pre-behavior

`input` was only available via Python `builtins` import.

### Why it hurt

First keyboard programs looked harder than `print`-only ones; the import
taught a library pattern before it was needed.

### Post-behavior

- `input()` / `input(prompt)` → `string` without import
- At most one prompt argument
- Emit is Python `input(...)`
- `import input from builtins` remains accepted for older teaching files

### Evidence

`tests/test_input_builtin.py`; book `basics_input.md` and related examples.

## Trade-offs

- EOF / interrupt stay Python runtime errors (no `result` wrapper yet).
