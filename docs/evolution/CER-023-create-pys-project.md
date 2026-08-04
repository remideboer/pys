# CER-023: Create PYS Project from activity bar

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-04 |
| Amended | 2026-08-04 (manifest entrypoint starter) |
| Commits | (extension 0.0.67) |
| Scope | `pys-language/create-project.js`; `package.json` activity bar / welcome / `pys.createProject`; `extension.js` |
| ADRs | [ADR-017](../adr/ADR-017-source-roots-same-package-tests.md); [ADR-002](../adr/ADR-002-hashed-dependency-locks.md) |

## Context

New learners needed a one-click layout matching declared source roots
(`src` / `tests` + `pys.toml`) and an empty `pys.deps` template. There was no
primary-sidebar PYS surface for project setup.

### Pre-behavior

- No activity-bar container; project layout was hand-copied from docs/examples.

### Why it hurt

- Easy to miss ADR-017 roots and start with a flat folder (blocks same-package
  tests). Empty `pys.deps` format was not discoverable next to Run Deps (CER-022).

### Post-behavior

- Activity bar **PYS** view with welcome + title **Create PYS Project**.
- Scaffold: `src/main.pys`, `tests/.gitkeep`, `pys.toml`
  (`[project].main` plus `main`/`test` source roots), and template `pys.deps`
  (`[interpreter]` + empty `[dependencies]`).
- The starter source has documented output and is immediately runnable through
  the same manifest entrypoint contract as CLI, Run Main, and Debug.
- Pure scaffold helper unit-tested; extension **0.0.67**.

### Evidence

- `pys-language/test/create-project.test.js`

## Trade-offs

- Folder name is `tests` (ADR-017), not `test`.
- Uses one minimal `src/main.pys`; it does not invent domain structure.
- Does not auto-open a multi-root workspace; offers Open Folder after create.
