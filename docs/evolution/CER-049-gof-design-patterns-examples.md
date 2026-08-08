# CER-049: GoF design-pattern teaching examples

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-08 |
| Commits | _(landing)_ |
| Scope | `examples/design_patterns/**`; `tests/test_design_patterns.py` |

## Context

Students need runnable, **pure OO** references for the classic Gang of Four
catalog (creational / structural / behavioral), aligned with PYS features
(`abstract`, `interface`, `static`, `open`/`override`) and the default OO
layered Cursor rule — not procedural `dict`/`object` sketches.

## Entries

### 1. Twenty-three demos under category folders

**Pre-behavior:** No `examples/design_patterns/` corpus.

**Why it hurt:** Patterns were only named in prose; no greppable PYS that
shows roles, composition, and expected output.

**Post-behavior:** One self-contained `.pys` per GoF pattern under
`creational/`, `structural/`, `behavioral/`; root README with index and modern
caveats (Singleton vs DI, Interpreter scope); isolated `pys.toml`; transpile
gate `tests/test_design_patterns.py`. Interface method signatures accept nominal
return types (`Button createButton()`) — see CER-010 §2.

**Evidence:** `python -m pytest -q tests/test_design_patterns.py`.

## Trade-offs

- One file per pattern (not multi-module packages) for runnable teaching
  density.
- Book chapters for patterns deferred — examples-only increment.
