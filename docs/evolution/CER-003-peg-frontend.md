# CER-003: Lexer/deps wins + PEG-capable parse front-end

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-01 |
| Commits | performance branch (phases 0–4 of PEG plan) |
| Scope | `transpiler/lex.py`, `parse.py`, `peg.py`, `deps.py`, `pytypes.py`; `tools/bench_*.py`; `tests/test_peg_dual_run.py` |
| ADRs | [ADR-003](../adr/ADR-003-measure-before-optimize.md), [ADR-004](../adr/ADR-004-peg-frontend.md) |

## Context

After CER-002, profile still showed `tokenize` / `peek` / `bump`, parse/sem
walks, and deps `is_file`/`stat` probes. This record covers the measurement-gated
follow-up: mechanical lexer cleanup, deps FS caches, and a PEP 617-inspired
packrat path — without flipping the default parser while packrat is slower.

### Baseline gate corpus

`examples/main.pys`, `vehicles.pys`, `gui/pokemontcg/{main,ui}.pys`,
`gui/PyQt/main.pys`.

| Mode | After CER-002 | After this CER (RD default) |
| --- | --- | --- |
| Hot median of 8 | ~302 ms | ~256–274 ms |
| Cold best-of-3 | ~846 ms | ~923 ms (noise; cold varies with machine load) |
| FS calls / 20 analyze | ~1311 | **~511** |

---

## 1. Honest phase benches (`parse_program_from_tokens`)

**Symbols:** `parse.parse_program_from_tokens`, `lex.tokenize_with_flags`;
`tools/bench_transpile.py`.

### Pre-behavior

Phase bench called `tokenize` then `parse_program` (which lexes again), so
totals over-counted lexing vs `compile_pys`.

### Why it hurt

Could not tell real parse cost from double-lex artifact; blocked ADR-003 gates.

### Post-behavior

`tokenize_with_flags` → `parse_program_from_tokens(lexed)` — one lex, parse-only
column. `parse_program` uses the same path.

---

## 2. Mechanical lexer wins + mode flags

**Symbols:** `lex._SINGLES`, `_OPS_BY_FIRST`, `TokenizeResult`,
`tokenize_with_flags`.

### Pre-behavior

- `singles` dict rebuilt every main-loop iteration
- `_OPS` scanned linearly for every punct character
- Frequent `bump(peek())` double index
- `parse_program` scanned all tokens twice for brace / legacy cues

### Why it hurt

Top cProfile time was `tokenize` / `peek` / `bump` / `add` — pure per-character
overhead, not semantic work.

### Post-behavior

Hoisted singles map; ops indexed by first character (longest-first preserved);
direct `source[i]` in hot loops; brace / legacy-indent flags set during lex.

**Evidence:** `tests/test_lex.py`; hot compile improved vs CER-002 (~302 → ~256 ms
in one after-phase1 run).

---

## 3. Deps filesystem caches

**Symbols:** `deps._find_deps_file_cached`, `_module_present_on_paths_cached`,
`deps.clear_filesystem_caches`; cleared from `pytypes.clear_filesystem_caches`.

### Pre-behavior

Every external-import check re-walked site trees (`is_file`/`stat`/`iterdir`);
`find_deps_file` re-walked parents.

### Why it hurt

`bench_fs_calls.py` showed hundreds of deps probes per analyze corpus; dominant
after `_same_package` was fixed in CER-002.

### Post-behavior

LRU caches keyed by module ref + site path tuple / resolved start + bound.
Tests reset via existing conftest autouse clear.

**Evidence:** FS calls **1311 → 511** on the same 20-file analyze corpus.

---

## 4. Packrat PEG path (not default)

**Symbols:** `parse._packrat`, `_Tok(packrat=…)`, `peg.parse_brace_module`,
`parse.set_brace_engine`, `engine=` on `parse_program_from_tokens`.

### Pre-behavior

Single classic RD path; no memo; no dual-run hook.

### Why change

PEP 617 / CPython Parser layout: keep lexer separate, enable packrat for
productions that backtrack, migrate with AST equality before switching default.

### Post-behavior

Same productions; optional per-parse memo on toplevel/statement/expression
ladder/block. Dual-run tests require RD dump == PEG dump on brace corpus +
goldens. **Default engine remains `rd`**: measured hot total RD ~274 ms vs PEG
~289 ms (~5% regress) because this grammar rarely re-enters the same
`(rule, pos)` — memo cost dominates reuse.

**Evidence:** `tests/test_peg_dual_run.py`; `tools/bench_engines.py`.

### Flip condition

Set `_BRACE_ENGINE = "peg"` only with a new CER showing packrat ≤ RD on the
gate corpus (or after grammar changes that increase backtracking).

---

## Trade-offs / rejected

- Full CPython `pegen` C generator — rejected (teaching maintainability)
- Third-party parser library — rejected
- Forcing PEG default despite regress — rejected (ADR-003 gate)
- Reintroducing double tokenize in `compile_pys` — still forbidden (CER-002)
