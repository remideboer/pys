# CER-051: Create Project target + host runtime ensure

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-09 |
| Commits | (runtime-ensure / create-project target) |
| Scope | `pys-language/runtime-ensure.js`; `create-project.js`; `extension.js` Create Project / Run; ADR-001 |
| ADRs | [ADR-001](../adr/ADR-001-trust-boundaries.md); complements [ADR-030](../adr/ADR-030-javascript-emit-target.md) |

## Context

Create Project always scaffolded a Python-oriented `pys.toml` with no emit
`target`. Students could pick JavaScript only via the status bar after the fact.
Missing Python/Node on PATH produced opaque terminal failures.

### Pre-behavior

- Scaffold wrote `main` / source roots / deps comments only.
- No PATH probe; Run assumed `python` / `node` existed.

### Why it hurt

- JavaScript projects were not first-class at create time.
- Classroom machines without Python/Node failed late and without an install path
  consistent with ADR-001 (trusted + explicit).

### Post-behavior

- On extension activate (trusted workspace): probe Python on PATH; if missing,
  prompt Install → curated version QuickPick → visible `winget` / `brew` / docs.
  If workspace `pys.toml` or `pys.emitTarget` is JavaScript, also probe Node.
- Create Project QuickPick: `python` | `javascript`; writes `[project].target`.
- Python is always required (transpiler host); JavaScript also requires Node.
- Run / Run Project / Debug / Select Emit Target reuse the same ensure helper
  (session dismiss for “Not now”).

### Evidence

`pys-language/test/runtime-ensure.test.js`; `create-project.test.js`;
extension asserts in `project-main.test.js`.

## Trade-offs

- Install does not block until PATH updates; user reloads / re-runs Create.
- Linux stays docs/`apt` hint (no unattended root).
