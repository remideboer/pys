# ADR-014: PYS source-level debug stepping

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-03 |
| Amended | 2026-08-03 (UX maturity); 2026-08-03 (halt at BP only; clear-all UX); 2026-08-03 (deps PYTHONPATH) |
| Code detail | [CER-014](../evolution/CER-014-pys-dap-stepping.md) |
| Source | [TODO-FUTURE F-004](../TODO-FUTURE.md); [pipeline-migration C2](../pipeline-migration.md) |

## Context

Debug previously launched the Python debugger on `python -m transpiler run
<.pys>`. That path transpiles to a temp directory and runs the student program
in a **child** `subprocess`, so the debugger never attached to teaching code.
There was also no `.pys` ↔ generated-Python line map.

## Decision

1. **Launch the generated program** (`program: <temp>/<stem>.py`) under
   Microsoft Python / debugpy — not the transpiler runner.
2. **`prepare_debug`** (IDE JSON helper) writes session temp `*.py` +
   `*.pysmap.json` via `transpile_with_modules_and_maps` (Run-class:
   trusted workspace, runtime introspection allowed). Returns
   `pythonpath_prepend` = temp dir + `pys.deps` site paths (same contract as
   `run_source`) and the deps-resolved `python` executable.
3. **Remap** breakpoints and stack frames with a
   `DebugAdapterTracker` scoped to sessions named `Debug PYS`; contribute
   breakpoints for language `pys`.
4. **Verified glyphs:** remap outbound `setBreakpoints` responses and
   `breakpoint` events so the gutter stays on `.pys`.
5. **Halt only at breakpoints** — `stopOnEntry: false`; Debug runs until the
   first user breakpoint (or program end).
6. **Clear All Breakpoints** command (`pys.clearAllBreakpoints`) on editor
   context, line-number/gutter context, tab title icon, and tab context menu.
7. **Variables / Watch:** pysmap `names` maps emitted locals (`_c_hits` →
   `hits`); hide `_pys_` / `__pys_` / `_Pys` helper clutter; bare Watch
   identifiers rewrite to emitted names. Shared/atomic cells still show as
   wrapper objects (no scalar unwrap).
8. ADR-001 unchanged: Debug remains trusted-workspace / Run-class only.

## Consequences

- Extension ≥ 0.0.50; JIT `J-debug`; example `examples/debug_step.pys`.
- Requires the Microsoft Python extension at debug time.
- Concurrency preamble / `_Pys*` frames may appear unmapped; task/thread
  debugging remains deferred.

## Rejected alternatives

- Full custom DAP server wrapping debugpy (unnecessary protocol surface).
- Keeping `module: transpiler` + `run` and only adding maps (child process gap).
- Default `stopOnEntry: true` (halts at top-level before any breakpoint — not how common IDE Debug File behaves).
- Faking scalar display for `_PysShared` / `_PysAtomic` in Variables (v1).
