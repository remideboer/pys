# ADR-001: Trust boundaries for IDE, transpile, and run

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-01 |
| Commits | `4446848` |
| Code detail | [CER-001](../evolution/CER-001-security-boundaries.md) |

## Context

PYS is used in classrooms and with arbitrary folders. Passive IDE must analyze
`.pys` on open/save; Run must execute generated Python with declared deps.
Those are different trust levels. Collapsing them (workspace on `PYTHONPATH`,
import-during-analyze, install-on-transpile) turns editing into an execution
surface.

## Decision

1. **Passive IDE / transpile / `compile_pys`:** fail closed — isolated helper
   (`python -I`, bundled code only), workspace realpath containment when
   `PYS_WORKSPACE_ROOT` is set, no pip install, no third-party import for typing
   by default.
2. **Explicit Run / Debug:** allowed only in a trusted workspace; may install
   from a hashed lock and use runtime introspection.
3. **Project files must not choose the interpreter binary** (`interpreter.path`
   rejected); the operator chooses Python by how they invoke the tool.
4. **Opt-in Go to Definition into locked `pys.deps`:** extension setting
   `pys.navigateLibrarySources` (default **false**) may pass
   `--library-sources` on **symbol lookup only**, so F12 can open Python
   sources from the hashed env. Diagnostics / save analysis stay fail-closed.
   Requires a trusted workspace. Does not enable analysis-time imports for
   squiggles.

## Consequences

- Diagnostics may be less precise about third-party members than Run-time typing.
- Contributors must not “fix” IDE features by restoring workspace `PYTHONPATH`
  or analysis-time imports without superseding this ADR and CER-001.
- Extension packaging must keep shipping a bundled transpiler for helpers.
- Library navigation is a deliberate privilege (setting + workspace trust), not
  the default edit path.

## Rejected alternatives

- Trust the workspace on open (convenient; unsafe for untrusted folders)
- Always import deps for richer squiggles (executes package top-level code)
