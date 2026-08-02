# CER-008: Traits composition

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-03 |
| Commits | (traits increment) |
| Scope | `lex.py`, `parse.py`, `ast_nodes.py`, `sem.py`, `emit/python.py`, `imports.py`; `pys-language/*`; `docs/*`; `examples/traits.pys`; `tests/test_traits.py` |
| ADRs | [ADR-009](../adr/ADR-009-traits-composition.md) |

## Context

Requirements specify Java/Scala-style traits with explicit `requires` for
didactic host contracts.

### Pre-behavior

No `trait` / `uses` / `requires`; only `interface` + single `inherits`.

### Post-behavior

- Lex/parse: `trait` bodies (`requires` + methods); class header `uses`.
- Sem: requires satisfaction, collision, `this.x` dependency, not-a-type;
  trait methods count toward `implements`.
- Emit: flatten into host; mangled `_Trait_method` when host overrides for
  `Trait.method(this)`.
- IDE: TextMate, hover, snippets, go-to; extension ≥ 0.0.41.
- Docs: LANGUAGE, EBNF, railroad, JIT `J-trait`, ADR-009.

### Evidence

`tests/test_traits.py`; `examples/traits.pys` with workspace-isolated
`run_source` (CER-001 §4).

## Trade-offs

- Flatten emit duplicates method text into each host (clear for teaching;
  no shared runtime trait object).
