# JIT — Debug (.pys breakpoints)

## Setup

1. Install the **Microsoft Python** extension (debugpy).
2. Open a `.pys` file in a **trusted** workspace.
3. Click in the gutter to set a breakpoint on a statement line.
4. **PYS: Debug File** (`Ctrl+Shift+D`) or the Debug CodeLens.

Debug runs until it **hits a breakpoint** (it does not stop at the first
top-level line). While paused, **inline values** appear at the end of lines
(IntelliJ-style) for variables in scope — turn off with `pys.debug.inlineValues`
if needed (and keep Cursor/VS Code `debug.inlineValues` on `auto` or `on`).

**Logpoints** log to the Debug Console without pausing: gutter / context
**PYS: Add Logpoint**, or VS Code **Add Logpoint**. Use `{name}` for values
(e.g. `total={total}`). See [IntelliJ logpoints](https://www.jetbrains.com/help/idea/logpoints.html).

Inline values only include names present in the current frame’s Locals (not
globals / builtins / other functions’ identifiers).

Use **PYS: Clear All Breakpoints** from the editor context menu, line-number/gutter
menu, or the editor tab menu/icon.

## What happens

1. Extension runs `prepare_debug` → temp `.py` + `.pysmap.json` line maps (+ name table).
2. debugpy launches the **generated program** (not `transpiler run`).
3. Breakpoints (including verified glyphs), stack frames, and Step Over/Into/Out
   are remapped back to `.pys` paths/lines.
4. Variables rename lambda captures (`_c_hits` → `hits`); runtime `_pys_*` helpers are hidden.

```pys
int total = 0          # set BP here to pause
function int bump(int n) {
    return n + 1       # Step Into lands here
}
total = bump(total)
print(total)
```

## Run vs Debug

| | Run | Debug |
|--|-----|-------|
| Command | `PYS: Run File` | `PYS: Debug File` |
| Stops on `.pys` | no | yes, at breakpoints |
| Needs Python ext. | no | yes |

## Limits

- Shared/atomic cells still appear as wrapper objects in Variables (not fake scalars).
- Concurrency helpers / thread pools may show unmapped frames.
- Untrusted workspaces cannot Debug (same gate as Run).

Full sample: [`examples/debug_step.pys`](../../examples/debug_step.pys).
