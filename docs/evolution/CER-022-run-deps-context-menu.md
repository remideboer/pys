# CER-022: Run Deps from pys.deps context menu

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-04 |
| Commits | (extension 0.0.66) |
| Scope | `pys-language/package.json` menus; `extension.js` `pys.lockDeps` / `lockDepsFile` |
| ADRs | [ADR-002](../adr/ADR-002-hashed-dependency-locks.md) (lock refresh remains explicit) |

## Context

After editing `pys.deps`, authors must run `python -m transpiler deps lock`
(ADR-002). Students and teachers often only know the IDE; there was no
discoverable surface on the deps file itself.

### Pre-behavior

- Explorer / editor context menus for `pys.deps` had no PYS action.
- Locking required a terminal / CLI knowledge of `deps lock`.

### Why it hurt

- Fail-closed locks (CER-001 / ADR-002) look like “broken Run” when `pys.lock`
  is stale; the refresh step was hard to find.

### Post-behavior

- Command **PYS: Run Deps** (`pys.lockDeps`) on `resourceFilename == 'pys.deps'`:
  explorer context, editor context, editor title, command palette.
- Opens a terminal and runs `python -m transpiler deps lock <pys.deps>` with the
  same bundled `PYTHONPATH` / workspace env as Run (ADR-001 containment).

### Evidence

- Manual: right-click `pys.deps` → Run Deps; terminal prints lock path.
- Extension **0.0.66**.

## Trade-offs

- Does not auto-lock on save (still explicit per ADR-002).
- Filename must be exactly `pys.deps` (case-sensitive on Linux).
