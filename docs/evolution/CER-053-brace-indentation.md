# CER-053 — Brace-mode indentation formatting (`pys.indent`)

| Field | Value |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-10 |
| Commits | (this change set) |
| Scope | `transpiler/sem.py` (`_check_brace_indentation`); `pys-language/extension.js`; `tests/test_indent.py` |

## Context

Brace mode ignores indentation for **structure**, so inconsistent spaces
(e.g. class field at 5 spaces, method body line at 9) compiled silently.
Students expected formatting errors (see `tests/fixtures/rekenmachine.pys`).

## 1. Fail-closed 4-space grid in brace mode

### Pre-behavior

Only tabs were illegal. Misaligned siblings / nest levels transpiled.

### Why it hurt

Teaching samples and IDE feedback could not enforce the documented 4-space
habit; “indentation transpile error” appeared to have vanished.

### Post-behavior

- `_check_brace_indentation` (brace_mode only) requires line-leading nodes to
  sit at `parent_indent + 4` (top-level at 0).
- Skips mid-line tokens (one-liner `{ … }` bodies; `global function` span on
  `function`; `else if` span on `if`).
- Synthetic `else → Block → IfStmt` for `else if` does not add an extra nest.
- `tasks` / `switch` cases nest from the task/case line.
- Error code `pys.indent` + `suggested_fix` (re-indented line); IDE quick fix
  “Fix indentation”.

### Evidence

- `tests/test_indent.py` (rekenmachine lines 9/12 shapes, else-if, global fn)
- Fixture `tests/fixtures/rekenmachine.pys` (aligned positive path)
- Rejection corpora updated to 4-space so SA errors remain the first failure

## Trade-offs

- Indent mode (legacy) unchanged — braces still optional there.
- Closing `}` lines are not separately validated (no AST node); sibling /
  nest checks cover the student mistakes that mattered.
- Does not run a full formatter — only fail-closed nest/sibling alignment.
