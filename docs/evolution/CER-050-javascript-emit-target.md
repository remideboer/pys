# CER-050: JavaScript emit target and Node run

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-09 |
| Commits | (javascript emit) |
| Scope | `transpiler/emit/javascript.py`, `npm_deps.py`, `pipeline.py`, `transpiler.py`, `__main__.py`, `pys-language/extension.js`, `examples/js_smoke.pys`, `examples/by-target/` |

## Context

Only Python emit/run existed despite `target=` stub in `compile_pys`. Need a
second backend and selectable Run path (ADR-030).

## Entries

### 1. JavaScript MVP emitter

**Pre-behavior:** `Target = Literal["python"]`; non-python raised.

**Post-behavior:** `emit/javascript.py` + `compile_pys(..., target="javascript")`.
Core teaching surface (see §5); traits/tasks/atomics and Python packages fail
closed (`JsEmitError`).

**Evidence:** `tests/test_emit_javascript.py`.

### 2. Node run + CLI `--target`

**Pre-behavior:** `run_source` always wrote `.py` and invoked CPython.

**Post-behavior:** `run_source(..., target=)` and CLI `--target`; JS writes
`.mjs` and runs `node`. Smoke: `examples/js_smoke.pys`.

**Evidence:** `tests/test_run_javascript.py` (skips if `node` missing).

### 3. Extension emit-target selector

**Pre-behavior:** Run always `python -m transpiler run <file>`.

**Post-behavior:** `pys.emitTarget` + status bar / `pys.selectEmitTarget`;
Run passes `--target`; Debug blocked when target ≠ python.

**Evidence:** `pys-language/package.json`, `extension.js`; `local_ci.py`.

### 4. Cast AST field name

**Pre-behavior:** `_cast` read `Cast.value` → `AttributeError` on `(int) f`.

**Post-behavior:** Uses `Cast.expr` (same as Python emit).

**Evidence:** `tests/test_emit_javascript.py::test_js_emit_explicit_cast`.

### 5. Core language expand (slice / switch / enum / entity / result)

**Pre-behavior:** Slice, Switch, Enum, Entity, Result, Set/Tuple/Brace,
Repeat fail closed as MVP gaps.

**Post-behavior:** Those lower to JS (tuples→arrays, sets→`Set`, enums→frozen
members with `.value`, switch→if/ternary, result helpers in preamble). Still
fail-closed: tasks/shared/atomic/await, traits, Python package imports.

**Evidence:** `tests/test_emit_javascript.py` (slice/switch/entity/import);
`examples/switch.pys` / `enums.pys` compile under `--target javascript`.

### 6. Library-independent main + by-target silos

**Pre-behavior:** `examples/main.pys` pulled MySQL/tkinter; root `pys.deps`
pinned mysql-connector; JS could not run the showcase.

**Post-behavior:** `main.pys` is sibling-`.pys` only (runs Python + JS). Target
demos live under `examples/by-target/{python,javascript}/` with local
`pys.toml` / `pys.deps` / `package.json` as declarations. JS maps
`nodegui`→`@nodegui/nodegui`, `mysql2`. Constructor / method overloads and ESM
`export` + import binding for sibling modules.

**Evidence:** `tests/test_acceptance_examples.py` (main runs both targets;
by-target compile gates).

### 7. NodeGUI runs under qode

**Pre-behavior:** JS `run_source` always invoked plain `node`, so
`@nodegui/nodegui` failed with `ERR_DLOPEN_FAILED` on `nodegui_core.node`.

**Post-behavior:** When `@nodegui/nodegui` + `.bin/qode` exist in the resolved
npm env (central cache preferred), run uses **qode**. PascalCase namespace
calls emit `new` (`ng.QMainWindow()`).

**Evidence:** `tests/test_acceptance_examples.py::test_resolve_js_runtime_prefers_qode_for_nodegui`;
manual desktop run of `examples/by-target/javascript/gui_nodegui`.

### 8. Central npm cache (parity with pys.deps)

**Pre-behavior:** JS silos required a local `npm install` / `node_modules`;
`run_source` wrote `.pys_js_out` beside `package.json` and fail-closed if
packages were missing locally.

**Post-behavior:** `transpiler/npm_deps.py` fingerprints `[dependencies.npm]`
from `pys.toml` (legacy `package.json` with deprecation warning) and installs
into `~/.pys/repository/npm/<digest>/` (`PYS_REPO` override) with a
**synthetic** cache `package.json`. Explicit Run may `npm install` into that
cache (ADR-001); emit under `runs/<id>/` so ESM resolves central
`node_modules`. IDE/analyze paths use `install=False` and do not network. No
silo-local install required.

**Evidence:** `tests/test_npm_deps.py`; by-target READMEs; ADR-030 amend.

### 9. Teaching-core JS parity (value types, concurrency, traits)

**Pre-behavior:** data/struct `==` was reference equality; `toBin`/`panic`
undefined at runtime; tasks/shared/atomic/await/traits fail-closed.

**Post-behavior:** JS emit matches teaching-core Python for
`examples/*.pys` and `examples/concurrency/main.pys`: field-wise
`equals` / `_pys_value_eq`, struct copy, base-display helpers, cooperative
`_PysTaskGroup`, shared/atomic wrappers, trait flatten + `Trait.method(this)`,
result propagate catch, string method map, `time.sleep` shim. Decorators and
Python packages still fail closed. OS-thread races deferred (F-010 item 2).

**Evidence:** `tests/test_emit_javascript.py`; book
`under_the_hood_emit_targets.md`; ADR-030 amend.

### 10. Node DAP (prepare_debug + pwa-node)

**Pre-behavior:** Extension Debug refused non-Python emit targets.

**Post-behavior:** `prepare_debug(target=javascript)` writes `.mjs` +
`js`-keyed pysmaps and `runtimeExecutable`; extension launches `pwa-node`
via `debug-launch.js` and reuses the shared DebugAdapterTracker /
`debug-map.js` (py|js keys). Advanced mode reveals `.mjs`.

**Evidence:** `tests/test_prepare_debug.py`; `pys-language/test/debug-*.test.js`;
CER-014 / ADR-014 amend; F-010 item 1 Done.

### 11. Unified `pys.toml` deps (retire student `pys.deps` / `package.json`)

**Pre-behavior:** Python pins in indented `pys.deps`; npm pins in silo
`package.json`; `pys.toml` held only project/main/source_roots.

**Post-behavior:** One student-facing file — `pys.toml` — with
`[interpreter]`, `[dependencies]`, and `[dependencies.npm]`. Sibling
`pys.lock` unchanged for Python. Central npm cache writes a synthetic
`package.json` only under `~/.pys/repository/npm/`. Compat loaders warn on
legacy files.

**Evidence:** `tests/test_deps.py`, `tests/test_npm_deps.py`; ADR-002 /
ADR-030 amend; book emit-targets + ttkbootstrap.

### 12. `[project].target` + Run Project on `pys.toml`

**Pre-behavior:** Emit target came only from CLI `--target` (default python)
or workspace `pys.emitTarget`. Right-click on `pys.toml` offered Deps Lock,
not Run.

**Post-behavior:** Optional `[project].target` (`python` | `javascript`,
default `python`). Bare `transpiler run` without `--target` reads it.
Extension **Run Project** (`pys.runProject`) is first on `pys.toml` context
menus and runs `[project].main` with the manifest target (ignores status-bar
selector). JS by-target silos set `target = "javascript"`.

**Evidence:** `tests/test_entrypoint_panic.py`;
`pys-language/test/project-main.test.js`; ADR-030 / LANGUAGE / book.

## Trade-offs

- JS tracks teaching core + mapped npm packages; Python remains reference for
  FastAPI decorators and exact int64.
- Cooperative tasks do not simulate OS-thread interleaving.
- Entity / data identity uses `.equals()` via `_pys_value_eq` for `==`.
