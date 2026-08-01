# ADR-002: Hashed, fail-closed dependency locks

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-01 |
| Commits | `4446848` |
| Code detail | [CER-001](../evolution/CER-001-security-boundaries.md) §6–7 |

## Context

Third-party packages for `.pys` programs are shared via `~/.pys/repository`, not
per-project venvs. Without exact pins and artifact hashes, classroom runs and CI
can silently pick different bits than the author reviewed.

## Decision

1. Every runnable project with deps keeps a committed **`pys.lock`** (URL +
   SHA-256 per artifact, deps fingerprint, Python minor, platform).
2. Install uses **`pip --require-hashes --no-deps`** into a lock-digest cache.
3. Missing, stale, wrong-runtime, or bad-hash locks **fail closed** on run /
   transpile; unpinned run dependencies are rejected.
4. Authors refresh locks explicitly: `python -m transpiler deps lock`.

## Consequences

- Changing `pys.deps` without regenerating the lock is a hard error — intentional.
- Platform-specific locks may be needed when artifacts differ (document in
  project README / CI); do not weaken hashing to paper over that.
- Analysis may recognize locked modules without installing them
  (`lock_declares_module`).

## Rejected alternatives

- Flyweight install of “latest” on first use (non-reproducible, supply-chain drift)
- Hash-optional locks for convenience (fail-open under pressure)
