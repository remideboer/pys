# CER-015: Brace block scope (loop binders and locals)

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-03 |
| Commits | (block-scope increment) |
| Scope | `sem.py` `_check_bindings`; `emit/python.py` brace mangle + lambda capture defaults; goldens; `tests/test_block_scope.py` |
| ADRs | (language scoping; complements ADR-012 loop capture) |

## Context

`{ }` bodies looked like scopes to students, but emit used Python `for x in …`
and sem added the binder to the outer `declared` set. After the loop, `x` still
existed; a later `int x = 10` reassigned the same binding. The debugger correctly
showed that leaked local — the defect was language/emit, not DAP.

### Pre-behavior

- Foreach / C-style binders: `declared.add(stmt.var)` on the outer env; emit
  `for x in …` / `for i in range(…)`.
- `if` / `while` / `switch` / `repeat` bodies shared the parent `declared` dict.
- Lambda capture defaults used the PYS free name (`_c_i=i`) even when the outer
  binder was already mangled.

### Why it hurt

- Violated the teaching expectation that braces introduce scope.
- Debugger “`x` still in scope” after the loop was accurate Python, confusing
  relative to PYS source.

### Post-behavior

- `_check_bindings` nests copies of `declared` / `types` / … for brace bodies;
  foreach / for-range binders exist only in the nested env.
- Emit mangles brace-local names to `_pys_bN_<name>`, records `debug_names` for
  DAP display, and applies renames in expressions and interpolated strings.
- DAP: pysmap `names` must win over `hidePrefixes` (`_pys_`), otherwise
  Variables/inline values drop brace locals (CER-014 / extension 0.0.55).
- Lambda capture defaults use the current outer rename (`_c_i=_pys_b1_i`).
- `docs/LANGUAGE.md` documents block-scoped binders / brace locals.

### Evidence

`tests/test_block_scope.py`; lambda foreach capture; updated goldens
`ebnf__control_flow__loops.py`, `fixtures__integration_core.py`.
