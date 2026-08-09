# ADR-014: PYS source-level debug stepping

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-03 |
| Amended | 2026-08-03 (UX maturity; deps; inline values; logpoints); 2026-08-04 (PYS-only default + explicit Python depth; manifest entrypoint parity); 2026-08-05 (generated-line step filtering + toolbar toggle); 2026-08-09 (Node DAP / loose-coupled launch adapters) |
| Code detail | [CER-014](../evolution/CER-014-pys-dap-stepping.md) |
| Source | [TODO-FUTURE F-004](../TODO-FUTURE.md); [pipeline-migration C2](../pipeline-migration.md) |

## Context

Debug previously launched the Python debugger on `python -m transpiler run
<.pys>`. That path transpiles to a temp directory and runs the student program
in a **child** `subprocess`, so the debugger never attached to teaching code.
There was also no `.pys` ↔ generated-Python line map.

## Decision

1. **Launch the generated program** under a thin target adapter — not the
   transpiler runner:
   - Python → `program: <temp>/<stem>.py` via Microsoft Python / debugpy
   - JavaScript → `program: <…>/<stem>.mjs` via built-in js-debug (`pwa-node`),
     with `runtimeExecutable` from prepare (node or qode)
2. **`prepare_debug`** (IDE JSON helper) writes session modules +
   `*.pysmap.json` via `transpile_with_modules_and_maps` (Run-class:
   trusted workspace, runtime introspection allowed). Contract is
   target-neutral (`main`, `cwd`, `maps`, `target`); Python adds
   `pythonpath_prepend` + `python`; JavaScript adds `runtimeExecutable`.
   CLI: `--prepare-debug <outdir> <file.pys> [--target python|javascript]`.
3. **Remap** breakpoints and stack frames with a shared
   `DebugAdapterTracker` (registered for `python` and `pwa-node`) scoped to
   PYS session names; contribute breakpoints for language `pys`. Map
   registry normalizes sidecar `py`|`js` generated keys.
4. **Verified glyphs:** remap outbound `setBreakpoints` responses and
   `breakpoint` events so the gutter stays on `.pys`.
5. **Halt only at breakpoints** — `stopOnEntry: false`; Debug runs until the
   first user breakpoint (or program end).
6. **Clear All Breakpoints** command (`pys.clearAllBreakpoints`) on editor
   context, line-number/gutter context, tab title icon, and tab context menu.
7. **Variables / Watch:** pysmap `names` maps emitted locals (`_c_hits` →
   `hits`); hide `_pys_` / `__pys_` / `_Pys` helper clutter; bare Watch
   identifiers rewrite to emitted names. Exact Python `None` values display as
   PYS `null`. Shared/atomic cells still show as wrapper objects (no scalar
   unwrap).
8. **Inline values:** `InlineValuesProvider` for language `pys` shows current
   **in-scope** Locals/Args at end-of-line while paused (IntelliJ-style), by
   reading the stopped frame’s scopes and filtering editor identifiers.
   Exact `None` formats as `null`. Toggle with `pys.debug.inlineValues`
   (default on). Ensure VS Code/Cursor `debug.inlineValues` is `on` or `auto`.
9. **Logpoints:** non-suspending breakpoints with DAP `logMessage`.
   `{expr}` uses PYS names in the UI; remapper rewrites identifiers to emitted
   locals. **PYS: Add Logpoint** on gutter/context (diamond glyph); also VS Code
   **Add Logpoint**. See [IntelliJ logpoints](https://www.jetbrains.com/help/idea/logpoints.html).
10. ADR-001 unchanged: Debug remains trusted-workspace / Run-class only.
11. **Stay in PYS by default:** `PYS: Debug File` launches with
    `justMyCode: true` (Python) or `skipFiles` for Node internals/deps (JS);
    generated frames are remapped and stepping does not enter libraries.
12. **Explicit depth escape hatch:** `PYS Advanced: Debug Transpiled Output`
    opens the generated `.py` / `.mjs`, launches with remapping off, and stops
    on generated entry. Separate session names for Python vs JavaScript so
    beginner debugging never falls through by accident.
13. **Entrypoint parity:** debug preparation resolves authoritative
    `[project].main` through the same contained path contract as Run. Selecting
    another file is rejected or explicitly reconciled through Set as
    entrypoint; imported files never receive top-level panic semantics.
14. **PYS statement stepping:** normal PYS sessions filter adapter `next`,
   `stepIn`, and `stepOut` stops. A stop is visible only when the top frame has
   an **exact** line-map origin at a different `.pys` path/line, or when the
   same exact generated line executes again (for example, a loop iteration).
   Unmapped generated helpers and additional emitted lines for the same
   PYS statement are stepped again automatically.
15. **Session-local toolbar choice:** PYS-only stepping starts enabled and can
    be toggled from the native debug toolbar. The existing Step buttons remain
    authoritative. Disabling the filter restores native adapter stepping;
    the Advanced transpiled session remains separate and unfiltered.
16. **Fail safe:** only `reason: step` stops may auto-resume. Breakpoints,
   exceptions, pauses, and data breakpoints always remain stopped. Automatic
   filtering is capped at 100 repeats so an unmapped runtime loop cannot run
   forever under debugger control.
17. **Loose coupling:** `debug-launch.js` owns only launch config shape;
    `debug-map.js` owns remapping; extension wires prepare → registry →
    adapter. Do not grow `if javascript` forks inside remap logic.

## Consequences

- Extension ≥ 0.0.72; JIT `J-debug`; example `examples/debug_step.pys`.
- Python debug requires the Microsoft Python extension; JavaScript debug uses
  built-in js-debug (`pwa-node`).
- Concurrency preamble / `_Pys*` frames may appear unmapped; OS-thread task
  debugging remains deferred (F-010 item 2). PYS-only stepping skips these
  frames when they are reached by a normal step; use Advanced mode to inspect
  them deliberately.

## Rejected alternatives

- Full custom DAP server wrapping debugpy (unnecessary protocol surface).
- Keeping `module: transpiler` + `run` and only adding maps (child process gap).
- Default `stopOnEntry: true` (the normal PYS mode runs to a PYS breakpoint;
  the explicitly selected transpiled-Python mode is the deliberate exception).
- Faking scalar display for `_PysShared` / `_PysAtomic` in Variables (v1).
