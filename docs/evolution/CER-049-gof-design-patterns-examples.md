# CER-049: GoF design-pattern teaching examples

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-08 |
| Commits | `75f419c` (GoF demos); `2f3b505` (GoF markdown); _(concurrency patterns)_ |
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

### 2. Companion markdown per pattern

**Pre-behavior:** Only a root README index; no per-pattern intent / UML / use-case notes.

**Why it hurt:** Students could run demos but had no local map from GoF roles to
the concrete types in each `.pys`, or pointers to real-world uses.

**Post-behavior:** One `[pattern-name].md` beside each `.pys` (intent, explanation,
classic Mermaid UML, demo-specific UML, real-world use cases, run line). Root
README tables link Code + Notes. Wikipedia pattern articles linked from each file.

**Evidence:** `examples/design_patterns/**/*.md` co-located with demos.

### 3. Concurrency patterns (Wikipedia Examples, option B)

**Pre-behavior:** Only GoF creational/structural/behavioral demos.

**Why it hurt:** Students had no map from the Wikipedia concurrency catalog to
what PYS can express with `tasks` / `await` / `shared` / `atomic` only.

**Post-behavior:** Four runnable demos under `concurrency/` (active object,
balking, double-checked locking via CAS, scheduler) with companion `.md`
files. README lists eight Wikipedia Examples as **out of language** (barrier,
guarded suspension, monitor, RW lock, TLS, thread pool, reactor, nuclear
reaction) — no `import threading` workarounds and no await-fan-in stand-in for
Barrier.

**Evidence:** `tests/test_design_patterns.py` asserts four `concurrency/*.pys`
transpile; README Out-of-language table.

## Trade-offs

- One file per pattern (not multi-module packages) for runnable teaching
  density.
- Book chapters for patterns deferred — examples-only increment.
- Concurrency demos stay inside the existing language contract (ADR-013 /
  CONCURRENCY.md); lock/CV/TLS patterns are documented, not faked.
