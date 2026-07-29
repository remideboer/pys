# T3 — Toolbox

**Whole task:** A second file needs a greeting and a shared max-size constant from your toolbox module — without exposing private helpers.

## Scaffolding

| Level | Folder / file | Your job |
|-------|---------------|----------|
| A Worked | [`1-worked/`](1-worked/) | Run `app.pys`. Trace which names cross the import door. |
| B Completion | [`2-completion/`](2-completion/) | Fix visibility / imports so `app.pys` runs and the private helper stays private. |
| C Conventional | [`3-brief.md`](3-brief.md) | Design your own two-file toolbox. |

## JIT

- [Function & import](../../jit/J-function-import.md)

## Supportive

- [S3 — Visibility and modules](../../supportive/S3-visibility-and-modules.md)

## Success criteria

1. `app.pys` runs via the transpiler (imports resolve).  
2. At least one name is intentionally *not* importable.  
3. You can point to each export and say who the customer is (`package` vs `global` vs private).
