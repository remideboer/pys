# CER-056: IDE IntelliSense completions + Create Class

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-10 |
| Commits | (this change set) |
| Scope | `transpiler/completions.py`; `transpiler/ide.py` `--completions`; `transpiler/refactor/create_class.py`; `pys-language/extension.js` / `refactor.js` / `package.json` |
| ADRs | [ADR-016](../adr/ADR-016-ide-refactoring.md) (generation note); [ADR-001](../adr/ADR-001-security-boundaries.md) (stdin path containment) |

## Context

Completion previously listed only static keywords/types. Students typing `rm.`
saw no members. Unresolved `Student(naam="…")` had no scaffold action.

### Pre-behavior

- `CompletionItemProvider`: keywords + primitives only
- No status-bar IntelliSense toggle
- No create-class generation from call sites

### Why it hurt

- Dot completion is the primary discoverability tool for OO teaching samples
- Beginners need optional disable when noise overwhelms
- Call-first scaffolding matches JetBrains “create class from usage” pedagogy

### Post-behavior

- `python -m transpiler.ide <file> --completions --line N --column N [--stdin]`
  returns ranked items (locals → params → fields → types → keywords; members
  after `.` with visibility filtering)
- Setting `pys.intellisense.enabled` + status bar toggle
- `--refactor-plan create-class` + CodeAction on `pys.unknown-type` / command
  `pys.generate.createClass` inserts a class with fields + constructor from
  **named** arguments (literal types inferred)

### Evidence

- `tests/test_completions.py`
- `tests/test_create_class.py`
- `pys-language/test/project-main.test.js` (manifest + extension surface)

## Trade-offs

- Signature Help deferred
- Positional-only ctor calls are out of Create Class MVP
- Full Fowler generation catalog remains [F-005](../TODO-FUTURE.md#f-005-full-fowler-refactor-catalog)
