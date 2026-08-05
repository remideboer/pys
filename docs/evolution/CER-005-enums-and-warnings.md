# CER-005: Enums + first-class compiler warnings

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-02 |
| Commits | (enums + warnings increment) |
| Scope | `transpiler.py`, `sem.py`, `pipeline.py`, `ide.py`, `lex.py`, `ast_nodes.py`, `parse.py`, `imports.py`, `emit/python.py`; `pys-language/*`; `docs/*`; `examples/enums.pys`; `tests/test_enums.py`, `tests/test_warnings.py` |
| ADRs | [ADR-006](../adr/ADR-006-enums-as-nominal-sets.md) |

## Context

Enums require a non-fatal naming rule. The toolchain previously had only
`TranspileError` and optional IDE Information hints — no Warning severity or
structured quick-fix path for analyzer warnings.

---

## 1. Warning model / IDE plumbing

**Symbols:** `TranspileWarning`; `Module.analysis_warnings`; `analyze_file` →
`warnings`; extension `DiagnosticSeverity.Warning` + `pys.enum-naming` quick fix.

### Pre-behavior

Compile either succeeded silently or raised `TranspileError`. IDE mapped only
errors and Information hints.

### Why it hurt

Could not teach / enforce SCREAMING_SNAKE_CASE without failing the build, and
could not offer rename quick fixes for non-fatal style rules.

### Post-behavior

`sem.analyze` appends `TranspileWarning` (message, span, `code`, `tips`,
`suggested_fix`) without aborting. CLI may print warnings on stderr
(`PYS_SUPPRESS_WARNINGS=1` to silence). IDE shows Warning diagnostics with tips
and CodeAction rename when `suggested_fix` is set. Feature DoD now requires
Error / Warning / tip / quick-fix maturity when a feature emits diagnostics.

### Evidence

`tests/test_warnings.py`; `tests/test_enums.py::test_enum_naming_warning_still_compiles`
and `test_analyze_file_includes_warnings`.

---

## 2. Enum grammar / SA / emit

**Symbols:** `EnumDef`, `EnumMember`; keyword `enum`.

### Pre-behavior

No `enum` keyword.

### Post-behavior

`[top_visibility] enum Name { MEMBER [= INT|STRING] , … [,] }` (non-empty,
comma-delimited; optional trailing comma — ADR-022 / CER-026). SA:
all-or-nothing, homogeneity, uniqueness, immutability, nominal typing, same-enum
`==`, `.value`. Emit `enum.Enum` / `IntEnum` / `StrEnum`. IDE: TextMate
`meta.enum.declaration`, go-to member, snippets, hover. Match/exhaustiveness
deferred. Duplicate-value aliases: not via `@alias` — PYS avoids `@` annotations;
any future alias form must be a real construct (see ADR-006 / project-memory).

### Evidence

`tests/test_enums.py`; `examples/enums.pys` with `PYS_WORKSPACE_ROOT` bound to
`examples/` (CER-001 §4).

## Trade-offs

- Warnings print to stderr by default (tests set `PYS_SUPPRESS_WARNINGS`).
- No `match` yet — follow-up. No `@` annotations in PYS (including no `@alias`).
