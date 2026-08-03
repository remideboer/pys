# CER-002: Cut redundant parse and filesystem work

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-01 |
| Commits | `639ed2e` (`perf: cut redundant parse and filesystem work`) |
| Scope | `transpiler/imports.py`, `pipeline.py`, `pytypes.py`; benches under `tools/bench_*.py`; `tests/test_module_parse_cache.py`, `tests/conftest.py` |
| ADRs | [ADR-003](../adr/ADR-003-measure-before-optimize.md) |

## Context

After the security work, compile and IDE analysis still felt slow on multi-file
examples (PyQt / pokemontcg UIs, `examples/main.pys`). Profiling showed the cost
was not “Python is slow” in the abstract — it was **repeat work**: the same
module parsed several times per compile, an extra full tokenize before parse,
and hundreds of Windows `resolve`/`stat` hits for answers that never change
within a process.

Rules for this change set: measure first, change one bottleneck at a time, keep
behavior identical for authors, prefer simple caches over lexer rewrites.

### How we measured

| Tool | What it answers |
| --- | --- |
| `tools/bench_cold.py` | Fresh-process `compile_pys` (closest to CLI / cold IDE helper) |
| `tools/bench_hot.py` | In-process median `compile_pys` after warmup |
| `tools/bench_transpile.py` | Per-phase share + optional cProfile |
| `tools/bench_fs_calls.py` | Pathlib resolve/stat/exists/read call sites during `analyze` |

**Corpus for headlines:** `examples/main.pys`, `interfaces.pys`,
`gui/pokemontcg/{main,ui}.pys`, `gui/PyQt/main.pys`.

| Mode | Before (`639ed2e~1`) | After (`639ed2e`) |
| --- | --- | --- |
| Cold compile (best of 3) | ~4569 ms | ~846 ms (~5.4×) |
| Hot median of 8 | ~4218 ms | ~302 ms (~14×) |

Full suite stayed green (248 tests at landing).

---

## 1. Memoize module parses across resolvers

**Symbols:** `imports._parse_module`, `_ParsedModule`, `clear_parse_cache`;
used from `ImportResolver.__init__`, `_load_module`, `discover_imported_modules`.

### Pre-behavior

`sem.analyze` and `emit` each construct an `ImportResolver`. Every resolver
re-read and `parse_program`'d the entry file and each imported `.pys` module to
rebuild export / import metadata. `discover_imported_modules` parsed the entry
file again for its import lines.

For a graph of *N* modules touched by both sem and emit, the same source was
parsed on the order of **several times per compile**, not once.

### Why it hurt

Lex + parse dominate wall time on non-trivial files. Repeating them for
identical `(path, source)` text is pure overhead — no new information.

### Post-behavior

```text
@lru_cache(maxsize=256)
_parse_module(path, source) -> ModuleInfo + import lines
```

Cache key includes **source text**, so an edited file never returns a stale AST
metadata snapshot. Sem and emit still build separate resolvers (unchanged
ownership); they now share parse results.

**Evidence:** `tests/test_module_parse_cache.py`
(`test_each_file_is_parsed_once_per_compile`, edit-staleness,
path-isolation). Deterministic parse counts rather than timings.

---

## 2. Remove the duplicate tokenize in `compile_pys`

**Symbols:** `pipeline.compile_pys` (removed early `lex.tokenize` call).

### Pre-behavior

```text
compile_pys:
  tokenize(source)          # fail-fast for LexError
  parse_program(source)     # tokenizes again internally
  analyze → emit
```

### Why it hurt

`parse_program` already lexes. The early pass was a full second scan of every
character for every compile, only to discover errors that parse would raise
anyway (still mapped to `TranspileError` on the parse path).

### Post-behavior

```text
compile_pys:
  parse_program(source)     # lexes once
  analyze → emit
```

Invalid tokens still fail before emit; they no longer pay for two lexes.

**Evidence:** cold/hot benches; cProfile before change showed `lex.tokenize` as
the top cumulative cost with call counts consistent with double lexing on the
compile path.

---

## 3. Cache interpreter layout and site/stdlib probes

**Symbols:** `pytypes._interpreter_layout`, `_is_stdlib_path`,
`_site_has_module_cached`, `clear_filesystem_caches`.

### Pre-behavior

Each “is this path stdlib?” / “does this site have module M?” call
re-`resolve()`d `sysconfig` purelib/platlib/stdlib and walked the filesystem.
Import-heavy analysis (Qt, locked deps) repeated the same probes dozens or
hundreds of times per process.

### Why it hurt

On Windows, `Path.resolve()` → `nt._getfinalpathname` / `nt.stat` showed up near
the top of cProfile *after* parse memoization — not algorithmic complexity,
just repeated syscalls for immutable process layout.

### Post-behavior

- Layout of site dirs + stdlib dir cached once (`lru_cache(maxsize=1)`)
- Per-path / per-(module, sites) answers cached (`maxsize=4096`)
- `clear_filesystem_caches()` for in-process installs (tests autouse this in
  `tests/conftest.py` because acceptance tests mutate site trees)

IDE helpers remain one-shot processes, so caches naturally die with the helper.

**Evidence:** drop in `nt._getfinalpathname` / `nt.stat` share in
`bench_transpile.py --profile`; FS call bench before/after later entry.

---

## 4. Stop re-resolving in `_same_package`

**Symbols:** `ImportResolver._same_package`.

### Pre-behavior

```python
return self.source_path.parent.resolve() == other.parent.resolve()
```

`source_path` and `ModuleInfo.path` were **already** resolved when stored.
Package-visibility checks still re-resolved both parents on every export lookup.

### Why it hurt

`bench_fs_calls.py` attributed **392 resolve + 392 stat** to this one line
across 20 `analyze()` calls — the largest single pathlib hotspot. Microbench:
~0.47 ms per double-resolve vs ~0.01 ms for parent equality on the same paths.

### Post-behavior

```python
return self.source_path.parent == other.parent
```

Same semantics for resolved absolute paths; no extra filesystem round-trips.

**Evidence:** FS calls **2095 → 1311** on the analyze corpus; hot total median
improved further (~435 ms → ~302 ms) on top of entries 1–3.

---

## What we deliberately left alone

Profile after these fixes still shows real cost in:

1. **Lexer internals** (`peek` / `bump` / `add`) — algorithmic / representation
   work, not accidental double calls
2. **Parse / sem AST walks** — necessary for correctness
3. **Deps path probes** (`module_present_on_paths`, `find_deps_file`) — smaller
   than the fixed hotspots; caching needs careful invalidation after installs

Rewriting the lexer or collapsing sem/emit resolvers into one shared mutable
object would be premature optimization relative to the measured wins above and
would hurt maintainability more than it helps right now.

---

## Trade-offs

- **Process-lifetime caches** in `pytypes` require an explicit clear when tests
  (or future in-process installers) change the filesystem underfoot.
- **Parse cache** is keyed by full source string (simple, correct). Large
  edit sessions in a long-lived process could grow the LRU; helpers today are
  short-lived, and `clear_parse_cache()` exists for tests.
- Phase benches still over-count lexing if they time standalone `tokenize`
  *and* `parse_program` (documented in `bench_transpile.py`); headline numbers
  use `compile_pys` end-to-end instead.
