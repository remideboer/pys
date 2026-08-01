# CER-001: Harden security boundaries

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-01 |
| Commits | `4446848` (`fix: harden transpiler security boundaries`) |
| Scope | `pys-language/ide-process.js`, `extension.js`, `transpiler/workspace.py`, `deps.py`, `imports.py`, `pytypes.py`, `pipeline.py`, `ide.py`, `sem.py`, publish workflows |
| ADRs | [ADR-001](../adr/ADR-001-trust-boundaries.md), [ADR-002](../adr/ADR-002-hashed-dependency-locks.md) |

## Context

Opening or running a `.pys` file used to pull the workspace onto `PYTHONPATH`,
walk parent directories for `pys.deps`, import third-party modules during static
analysis, and install packages as a side effect of transpile/IDE validation.
Publish jobs also fetched floating CLIs while holding marketplace secrets.

That is convenient for a trusted author machine. It is unsafe for classroom /
untrusted folders and for CI supply-chain integrity. The changes below keep the
teaching workflow, but fail closed at each boundary.

---

## 1. Isolated IDE helper process

**Symbols:** `pys-language/ide-process.js` (`buildIdeProcessSpec`, `IDE_BOOTSTRAP`);
call sites in `extension.js` for diagnostics, go-to-def, semantic tokens.

### Pre-behavior

```text
spawn(python, ["-m", "transpiler.ide", path], {
  cwd: workspace,
  env: { PYTHONPATH: workspace + user PYTHONPATH, ... }
})
```

The workspace (and the user's ambient `PYTHONPATH`) could shadow the bundled
transpiler or run arbitrary import-time code when a file was merely opened.

### Why it hurt

Passive IDE features became an execution surface for untrusted repositories.

### Post-behavior

```text
python -I -c <bootstrap> <bundledRoot> <realpathSource> …
```

- `-I` isolation; `PYTHONPATH` / `PYTHONHOME` stripped
- bootstrap inserts only the extension's `bundled/` tree
- sets `PYS_WORKSPACE_ROOT` for Python-side containment

**Evidence:** `pys-language/test/ide-process.test.js`

---

## 2. Bounded, cancellable helper I/O

**Symbols:** `runJsonProcess`, `killProcessTree`, `DEFAULT_TIMEOUT_MS`,
`DEFAULT_MAX_OUTPUT_BYTES` in `ide-process.js`.

### Pre-behavior

Stdout was accumulated without a timeout or size cap; cancellation was not
structured; stderr was ignored; JSON parse failures were fragile.

### Why it hurt

A hung or chatty helper could stall the editor or grow memory without bound.
Stale processes raced with newer diagnostics.

### Post-behavior

5s timeout, 1 MiB stdout/stderr caps, VS Code cancellation / `AbortController`,
process-tree kill (including Windows `taskkill /T`), single JSON document, typed
error codes (`TIMEOUT`, `OUTPUT_LIMIT`, `CANCELLED`, `INVALID_JSON`).

**Evidence:** `ide-process.test.js` (timeout / bound cases)

---

## 3. Workspace realpath containment (JS + Python)

**Symbols:**

- JS: `resolveWorkspaceFile`, `isPathInside` (`ide-process.js`); used by
  validate / locate / run / debug / main-file paths in `extension.js`
- Python: `transpiler/workspace.py` (`resolve_workspace_path`,
  `workspace_root_from_env`); `ImportResolver` / `ide.analyze_file`

### Pre-behavior

Some paths were checked only lexically (`abspath` / string prefix). Symlinks and
junctions could point outside the opened folder while still looking “inside”.
`.pys` imports used plain `Path.resolve()` with no workspace stop.

### Why it hurt

An attacker-controlled tree could analyze or transpile files outside the trusted
workspace (and, for run/debug, execute them).

### Post-behavior

Lexical **and** `realpath` containment. Helpers refuse to spawn when the
document escapes. With `PYS_WORKSPACE_ROOT` set, Python rejects escaping source
paths and `.pys` import targets (`TranspileError` / `None`).

**Evidence:** `ide-process.test.js` (lexical + symlink escape);
`tests/test_deps.py` (`test_pys_import_cannot_escape_workspace`,
`test_pys_import_rejects_symlink_escape`,
`test_ide_rejects_symlinked_document_escape`)

---

## 4. `PYS_WORKSPACE_ROOT` stops upward deps discovery

**Symbols:** `WORKSPACE_ROOT_ENV`; `deps.find_deps_file(..., stop_at=)`;
`run_source` → `load_deps(..., stop_at=workspace_root)`; extension `buildRunEnv`.

### Pre-behavior

`find_deps_file` walked from the `.pys` file to the filesystem root. A parent
directory outside the workspace could supply `pys.deps` / lock / interpreter
constraints for an innocent nested project.

### Why it hurt

Dependency and interpreter policy could be hijacked by files the student never
opened as the project root. (Also broke CI when a root MySQL lock leaked into a
dependency-free concurrency example — fixed in `cbd7e0a` by setting the env in
tests.)

### Post-behavior

Extension sets `PYS_WORKSPACE_ROOT`. Deps discovery and run stop at that root.

**Evidence:** `test_find_deps_file_stops_at_workspace_root`,
`test_run_source_ignores_deps_above_workspace`,
`ide-process.test.js` (run env carries the variable)

---

## 5. Reject `interpreter.path` in project `pys.deps`

**Symbols:** `deps.parse_deps_text` (interpreter section); `resolve_python_executable`.

### Pre-behavior

Projects could set `[interpreter] path = ...`. Resolution executed that binary.

### Why it hurt

Repo-controlled config selected an attacker-chosen Python executable.

### Post-behavior

`interpreter.path` is a parse error. Version constraints remain. Operators pick
the interpreter by how they invoke the CLI (`python -m transpiler …`).

**Evidence:** `test_interpreter_path_is_rejected`; README dependency section

---

## 6. Hashed `pys.lock` and fail-closed install

**Symbols:** `LockedPackage`, `DepsLock`, `generate_lock`, `validate_lock`,
`ensure_locked_environment` (`pip --require-hashes --no-deps`); CLI
`python -m transpiler deps lock`.

### Pre-behavior

Packages installed into a flyweight cache from unpinned / floating versions
without per-artifact hashes. Missing or stale lock behavior was lenient.

### Why it hurt

Supply-chain drift and dependency confusion: run could pull different bits than
the author reviewed.

### Post-behavior

Committed lock records deps fingerprint, Python minor, platform, index URL, and
each package URL + SHA-256. Install only from the lock digest cache. Run /
transpile reject missing, stale, wrong-runtime, or bad-hash locks. Direct run
deps must be exact versions (no silent “latest”).

**Evidence:** lock tests in `tests/test_deps.py`;
`tests/test_cli_module.py` (`test_module_run_requires_dependency_lock`)

---

## 7. No install and no runtime imports during analysis

**Symbols:**

- `ImportResolver._deps_paths` → `ensure_site_paths_for(..., install=False)`
- `pipeline.compile_pys(..., allow_runtime_introspection=False)` (default)
- `run_source` passes `allow_runtime_introspection=True`
- `pytypes.import_module_from_sites(..., allow_runtime_imports=…)`
- `sem._known_library_type` early-out when introspection is off
- `lock_declares_module` for recognizing locked packages without importing

### Pre-behavior

Transpile / IDE validation could pip-install missing packages and
`importlib.import_module` third-party (or shadowed workspace) modules to resolve
types. Package top-level code ran as a side effect of opening a file.

### Why it hurt

“Just looking” executed untrusted code and hit the network.

### Post-behavior

| Path | Install | Import third-party for typing |
| --- | --- | --- |
| IDE / `transpile` / `compile_pys` default | No | No |
| `run_source` | Yes (from lock) | Yes |

External imports can still be *recognized* from the lock without loading the
module. Library member checks stay fail-open on types when introspection is off
(no false hard error that forces an unsafe import).

**Evidence:** `test_import_resolver_does_not_install_on_validate`,
`test_static_analysis_does_not_execute_cached_dependency`,
`test_import_module_from_sites_rejects_workspace_shadow`

---

## 8. Publish / CI supply-chain hardening

**Symbols:** `.github/workflows/publish-extension.yml`, `extension.yml`;
`pys-language/package-lock.json`; `tests/test_workflow_security.py`.

### Pre-behavior

Publish used a single job with broad permissions, mutable Action tags
(`@vN`), and `npx --yes` to fetch latest `vsce` / `ovsx` while secrets were
present.

### Why it hurt

A compromised Action tag or floating CLI on a secrets-bearing job is a direct
release compromise path.

### Post-behavior

- Split **build** (package VSIX, read-only) from **publish** (artifact + PAT)
- `npm ci` + `npx --no-install` for pinned local tools
- GitHub Actions pinned to immutable commit SHAs

**Evidence:** `test_workflow_actions_use_immutable_commit_shas`,
`test_publish_workflow_never_downloads_npx_tools`

---

## 9. VS Code workspace trust for Run / Debug

**Symbols:** `extension.js` — `runPysFile`, `debugPysFile`.

### Pre-behavior

Run/Debug did not consult `vscode.workspace.isTrusted`.

### Post-behavior

Refuse Run/Debug until the workspace is trusted. Complements helper isolation
(analysis) with an explicit gate for execution.

---

## Trade-offs

- **Typing fidelity vs safety:** IDE analysis may know less about third-party
  members until Run (introspection on). Prefer incomplete diagnostics over
  import-time execution.
- **Lock friction:** contributors must run `deps lock` after changing
  `pys.deps`; that is intentional fail-closed behavior.
- **Dev F5 path:** editable/`PYTHONPATH` contributor workflows remain documented
  separately from the packaged extension’s isolated helper.
