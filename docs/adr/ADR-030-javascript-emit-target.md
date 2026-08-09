# ADR-030: Dual emit backends (Python reference + JavaScript)

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-09 |
| Commits | (javascript emit / Node run / teaching-core parity) |

## Context

The PYS front end (lex → parse → sem → `ast_nodes`) is target-neutral.
Students and tooling need a second backend under Node.js, selectable from
the extension Run button, without silently teaching wrong semantics.

## Decision

1. **`pipeline.Target`** is `"python" | "javascript"`. Python remains the
   **reference** backend for FastAPI decorators and exact wide ints; Debug/DAP
   works for both backends (ADR-014).
2. **`emit/javascript.py`** covers teaching-core parity with Python for
   control flow, OO, collections, switch/enum/entity/data/struct (value
   `==` + copy), result/`propagate`, lambdas, traits (`uses` flatten),
   shared/atomic/tasks/await (cooperative task group), and mapped npm
   imports. Fail-closed: library decorators, unmapped Python packages.
3. **`run_source(..., target=)`** for JS resolves `[dependencies.npm]` from
   `pys.toml` into `~/.pys/repository/npm/<fingerprint>/` on explicit Run
   (ADR-001), emits under `runs/<id>/`, prefers **qode** when NodeGUI is present.
4. **CLI / extension:** `--target` and `pys.emitTarget` for Run File; optional
   `[project].target` in `pys.toml` (default `python`) for bare `transpiler run`
   and **Run Project** on the manifest. Debug uses the same emit target
   (prepare_debug + thin launch adapters — F-010 item 1 Done).
5. **Examples:** `examples/main.pys` is target-independent; MySQL/NodeGUI/
   Express REST under `examples/by-target/` (single `pys.toml` per silo with
   `target = "javascript"` when applicable). Mapped npm includes
   `express` (default import), `mysql2`, `nodegui`; builtins `crypto`→
   `node:crypto`; teaching shims for `json` and `time`.

## Consequences

- Two emitters must stay aligned on AST contracts.
- JS tasks are cooperative (no OS-thread race simulation).
- First Run of a silo with `[dependencies.npm]` needs network + npm; later Runs
  reuse the hashed cache.
- Per-silo student-facing `package.json` is rejected as the product model
  (synthetic file only inside the central cache).

## Rejected alternatives

- Browser / Deno / Bun as first engines
- Per-silo manual `npm install` as the product model
- Auto `npm install` during IDE analyze
- Growing `if javascript` forks inside DAP remap (use launch adapters +
  target-neutral map keys instead)
