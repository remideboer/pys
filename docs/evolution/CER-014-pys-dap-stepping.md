# CER-014: PYS source-level DAP stepping

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-03 |
| Amended | 2026-08-03 (UX maturity / deps); 2026-08-04 (PYS-only default + Python depth mode) |
| Commits | (F-004 increment; debug UX maturity; deps on Debug) |
| Scope | `emit/python.py`; `pipeline.py`; `transpiler.py`; `ide.py`; `pys-language/extension.js`; `debug-map.js`; docs |
| ADRs | [ADR-014](../adr/ADR-014-pys-dap-stepping.md) |

## Context

F-004 / pipeline C2: students need breakpoints and step-over on `.pys` lines.
Follow-up maturity: verified gutter glyphs, stop-on-entry, Variables/Watch names.

### Pre-behavior

- Emit ignored AST spans; no line map.
- `debugPysFile` launched `type: python` on `module: transpiler` /
  `args: ['run', file]` — debugger on the runner; student code in a child
  subprocess under `run_source`.

### Post-behavior (F-004)

- `emit_with_map` / `compile_pys_with_map` / `transpile_with_modules_and_maps`
  produce statement maps `{py, pys}`; preamble unmapped.
- `ide.prepare_debug` writes temp modules + `*.pysmap.json`; CLI
  `--prepare-debug <outdir> <file.pys>`.
- Extension prepares artifacts, launches `program` under debugpy, remaps
  inbound `setBreakpoints` / `stackTrace` via `debug-map.js`.

### Post-behavior (UX maturity)

- Outbound `setBreakpoints` response + `breakpoint` events remap to `.pys`.
- Launch **`stopOnEntry: false`** — run until a user breakpoint (not top-level halt).
- `pys.clearAllBreakpoints` on editor context, gutter line-number context, tab
  title, and tab context menu.
- pysmap includes `names` (`_c_*` → PYS) and `hidePrefixes`; tracker remaps
  `variables` and bare `evaluate` expressions.
- Lambda free-name walk treats outer aug-assign targets as captures.
- Extension **0.0.49**.

### Post-behavior (deps PYTHONPATH)

- `prepare_debug` resolves `pys.deps` site paths like `run_source` and joins
  them into `pythonpath_prepend` after the temp module dir; also returns
  `python` for the launch config.
- Debug no longer fails with `ModuleNotFoundError` for locked packages
  (e.g. `mysql.connector`) that Run already finds.
- Extension **0.0.50**.

### Post-behavior (inline values)

- `InlineValuesProvider` for `.pys` shows Locals as end-of-line ghost text
  while paused (`InlineValueText`); only names present in the current frame’s
  Locals/Args scopes (not Globals/Builtins); `pys.debug.inlineValues`.
- Extension **0.0.54** (Map scope filter fix; was 0.0.53 empty inline values).
- Extension **0.0.55**: `remapVariables` applies pysmap `names` **before**
  `hidePrefixes`, so brace-scoped `_pys_bN_*` locals (CER-015) display as
  their PYS names in Variables and inline values (e.g. loop counter `i` on
  the `loop` header line).

### Post-behavior (logpoints)

- DAP `logMessage` remapped with PYS→emitted identifier rewrite inside `{…}`.
- `pys.addLogpoint` on gutter / editor context; messages go to Debug Console
  without suspending (IntelliJ-style logpoints).
- Extension **0.0.52**.

### Post-behavior (PYS-first stepping)

- `PYS: Debug File` now uses `justMyCode: true`: normal Step Into stays in
  mapped PYS/user code instead of entering Python dependencies.
- `PYS Advanced: Debug Transpiled Python` is the explicit escape hatch:
  opens the generated `.py`, stops on entry, uses `justMyCode: false`, and
  leaves stack/Variables/evaluate in Python names.
- Both session modes still translate pre-existing `.pys` breakpoints to the
  generated program. Only the normal mode remaps source views back to PYS.
- `debug-mode.js` keeps the launch contract pure and unit-tested.
- Extension **0.0.68**.

### Evidence

`tests/test_line_map.py`; `tests/test_prepare_debug.py`;
`pys-language/test/debug-map.test.js`;
`pys-language/test/debug-mode.test.js`.

## Trade-offs / deferred

- No scalar unwrap of `_PysShared` / `_PysAtomic` in Variables.
- `tasks` / ThreadPool thread debugging not specialized.
- Column / `end_line` spans still unused.
- Custom standalone DAP server not built.
