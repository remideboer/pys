# CER-052 — Enforce member access inside string interpolations

| Field | Value |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-10 |
| Commits | (this change set) |
| Scope | `transpiler/sem.py` (`_check_oop` / `walk_expr`, `_interpolation_inner_exprs`) |

## Context

Member visibility (`private` / `protected` / …) is enforced in `_check_oop` by
walking `Member` AST nodes. `InterpolatedString` stores only the literal `raw`
text — interpolation `{expr}` pieces are **not** child Expr nodes — so private
field reads inside `print("…{obj.field}…")` skipped the access check and
compiled (observed on VSIX 0.0.90). Spec: `private` = defining class only;
`protected` = subclasses.

## 1. Walk re-parsed interpolation pieces

### Pre-behavior

- Bare assigns / reads (`car.make = …`, `int x = car.make`) denied correctly.
- Same private read inside `"…{car.make}…"` or `#s{car.make}` transpiled and ran.

### Why it hurt

Students (and production code) could observe private state via string
interpolation, contradicting LANGUAGE member-access rules and teaching examples.

### Post-behavior

- `_interpolation_inner_exprs` strips quotes / typed `#…{}` markers and parses
  each `{…}` piece via `_expr_from_text`.
- `walk_expr` walks those pieces so `check_member` applies the same private /
  protected rules as for ordinary expressions.
- Public method calls in interpolations (`{rm.som()}`) remain allowed.

### Evidence

- `tests/test_sem.py` (interpolation-focused cases)
- `tests/test_member_access.py` — negative matrix across use sites +
  `requirements/rekenmachine.pys` fixture (uncomment-each-line denials)

## 2. Negative corpus across use sites (DoD)

### Pre-behavior

Access tests mostly covered one assign shape (`car.make = …`). Interpolation
and other reads could still compile — the VSIX 0.0.90 student sample slipped
through.

### Why it hurt

Fail-closed rules with happy-path-only (or single-shape) tests regress silently.

### Post-behavior

DoD §2 and engineering ruleset §3 require **negative** regressions for
fail-closed rules; member access must deny assign / print / decl RHS / call
arg / interpolations / subclass `this.` while public API remains allowed.
`requirements/rekenmachine.pys` documents uncomment-to-fail lines.

### Evidence

`tests/test_member_access.py`; `.cursor/rules/feature-maturity-dod.mdc` §2;
`docs/ci-failure-patterns.md` pattern on access use-site coverage.

## Trade-offs

- Still does not materialize interpolation Exprs in the parse AST (emit keeps
  regex lowering). Re-parse is shared shape with emit, not a second semantics.
- Malformed `{…}` pieces that fail to parse are skipped here (other phases /
  emit remain responsible).
- Brace mode does not revive Python IndentationError for mixed spaces inside
  `{ }` — visibility is semantic, not indent-based.
