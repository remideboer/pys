# ADR-003: Measure before optimize; record lasting perf fixes as CERs

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-01 |
| Commits | `639ed2e` |
| Code detail | [CER-002](../evolution/CER-002-compile-performance.md) |

## Context

The compile pipeline (lex → parse → sem → emit + imports/deps) invites
premature micro-optimization. Blind “cleanup” also tends to remove caches and
guards that exist only because measurement proved a bottleneck — i.e. devolution.

## Decision

1. **No performance change without measurement** (cold/hot `compile_pys`, phase
   bench, cProfile, or FS-call attribution as appropriate).
2. Prefer **removing redundant work** and **small caches** over rewriting the
   lexer/parser for elegance.
3. Lasting, measured fixes get a **CER** so later refactors do not reintroduce
   the pre-behavior (double tokenize, uncached module parses, etc.).
4. Do not drop security fail-closed behavior for speed (ADR-001 wins).

## Consequences

- Bench tools under `tools/bench_*.py` are part of the workflow, not throwaways.
- “Simplify by inlining / removing the cache” requires new numbers + a CER
  update, not taste alone.

## Rejected alternatives

- Optimize from intuition or from phase benches that double-count lexing
- Large lexer rewrite before exhausting redundant-work wins
