# 12.3. Emit targets: Python and JavaScript

> **Optional background.** Most of the book assumes the default **Python**
> emit target. This chapter explains how to run the same `.pys` under
> **JavaScript (Node)** and what still differs.

## One front end, two backends

Lex, parse, and semantic analysis are shared. Only the last step — emit —
chooses a backend:

| Target | Runtime | Typical use |
| --- | --- | --- |
| `python` (default) | CPython | Full language surface, deps, Debug |
| `javascript` | Node.js (or **qode** for NodeGUI) | Second backend; teaching-core parity + Debug |

In the VS Code / Cursor extension, pick the target from the status bar
(`pys.emitTarget`) for **Run File**, or set it on the project:

```toml
[project]
main = "main.pys"
target = "javascript"
```

**Run Project** (right-click `pys.toml`) uses `[project].target` (default
`python`) and does not follow the status-bar selector. **Create PYS Project**
also asks for this target and can prompt to install Python / Node when missing
from PATH. CLI:

```text
python -m transpiler run examples/main.pys --target javascript
```

Without `--target`, `transpiler run` also reads `[project].target` from the
nearest `pys.toml`.

Expected: the same prints as under Python for that showcase.

## Dependencies

- **Python:** declare packages under `[dependencies]` in `pys.toml`; Run installs
  into `~/.pys/repository` (central repo) using sibling `pys.lock`.
- **JavaScript:** declare npm packages under `[dependencies.npm]` in the same
  `pys.toml`; Run installs into `~/.pys/repository/npm/<fingerprint>/`. No
  silo-local `npm install` is required.

Target-specific demos (MySQL, NodeGUI) live under
`examples/by-target/` — see that folder’s README.

## What matches today

Teaching-core programs under `examples/*.pys` — including data/struct
equality, lambdas with `shared`, traits, results/`propagate`, atomics, and
`tasks`/`await` — run under both targets.

```pys
data Point {
    int x
    int y
}
print(Point(0, 0) == Point(0, 0))  # True under Python and JavaScript
```

Expected output:

```text
True
```

## Limits to remember

1. **Debug** works for both emit targets (Python/debugpy or Node/js-debug).
   Set `pys.emitTarget` then use **PYS: Debug File**; Advanced opens the
   generated `.py` or `.mjs`.
2. **Library decorators** (e.g. FastAPI `@app.get`) fail closed on JS emit —
   use `--target python`.
3. **Python stdlib / Tk / FastAPI** are not JS libraries; use sibling `.pys`,
   npm-mapped names (`mysql2`, `nodegui`), or the Python target.
4. JS `tasks` run **cooperatively** on one thread (await trampoline). Shared
   counter “race” demos may always show the sequential total; atomics still
   give the deterministic RMW result. (True OS-thread JS tasks remain
   deferred — F-010 item 2.)
5. Integers wider than JS `Number` precision (e.g. some `int64` dumps) may
   round — prefer Python when exact big integers matter.

## Try it

1. Run `examples/js_smoke.pys` with `--target javascript`.
2. Run `examples/data.pys` under both targets; confirm `True` / `False` lines
   match.
3. Open `examples/by-target/javascript/mysql/` and Run with the JS target
   (needs a MySQL server for a live query).
4. Switch emit target to JavaScript, set a breakpoint in
   `examples/debug_step.pys`, and **Debug File** — the gutter should stop on
   the `.pys` line (same idea as Python debug).
