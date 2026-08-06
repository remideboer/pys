# CER-030: parseFloat / parseInt recoverable builtins

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-06 |
| Scope | `sem` (seeded returns/params; switch subject locals); `emit/python` (`_pys_parse_*`); book; examples; highlighter |
| Architecture | [ADR-021](../adr/ADR-021-result-propagate-panic.md) (amended) |

## Context

GUI/form parsing needed `result<float, string>` without inventing `try`/`catch`
or fake helpers (`isNumeric` / `toFloat`). Hand scanners and bare `float(...)`
were either verbose or crash-on-bad-input.

## Entry 1 — builtins

### Pre-behavior

Only crashing `int(...)` / `float(...)` conversions existed for text.

### Why it hurt

Recoverable input could not share one parse path with typed success/failure.

### Post-behavior

- `parseFloat(text)` → `result<float, string>`
- `parseInt(text)` → `result<int, string>`
- Emit lowers to helpers that catch only `ValueError` and wrap `_pys_ok` /
  `_pys_err`. Acceptance matches the Python emit target (documented trade-off).

### Evidence

`tests/test_parse_float_int.py`.

## Entry 2 — switch subject locals

### Pre-behavior

`_check_switch` did not record function-local `declare_type` bindings, so
`switch (parsed)` inside a function failed subject typing even for
`result<…> parsed = ok(1)`.

### Post-behavior

Assign/`shared` declarations update the switch walk's type map; Call subjects
recognize `parseFloat` / `parseInt`.

### Evidence

Same tests; temperature converter uses `parseCelsius` → `parseFloat`.

## Trade-offs

- No general exception surface; only these builtins bridge `ValueError`.
- Emit-target acceptance is intentional and taught (scanner vs parseFloat).
