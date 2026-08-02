# CER-007: Switch statement and expression

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-02 |
| Commits | (switch increment) |
| Scope | `lex.py`, `parse.py`, `ast_nodes.py`, `sem.py`, `emit/python.py`; `pys-language/*`; `docs/*`; `examples/switch.pys`; `tests/test_switch.py` |
| ADRs | [ADR-008](../adr/ADR-008-switch-stmt-and-expr.md) |

## Context

Teaching samples need Java-inspired switch (stmt + expr) with explicit
fall-through via `continue`, enum bare labels, and expression exhaustiveness.

### Pre-behavior

No `switch` / `case` / `default` / `=>`; F-002 deferred a separate `match`.

### Post-behavior

- Lex: keywords `switch`/`case`/`default`; op `=>`.
- AST: `SwitchStmt` / `SwitchExpr` / `SwitchCase` (`fallthrough` from trailing continue).
- Parse: statement vs expression by first arm (`:` vs `=>`); reject mixes/empty.
- Sem: bare enum label resolve; duplicate/unknown labels; expression type unify;
  exhaustiveness error (expr) / warning (stmt); `_infer_type(SwitchExpr)`.
- Emit: fall-through groups → `if`/`elif`; expression → nested conditionals.
- IDE: TextMate + snippets + hover; extension ≥ 0.0.40.
- Docs: LANGUAGE, EBNF, railroad, JIT `J-switch`, ADR-008; F-002 superseded.

### Evidence

`tests/test_switch.py`; `examples/switch.pys` with workspace-isolated
`run_source` (CER-001 §4).

## Trade-offs

- Emit uses nested `if` / conditionals (readable; no reliance on Python
  fall-through). Expression form does not emit `match`/`case` yet — optional
  later polish, not required for teaching correctness.
