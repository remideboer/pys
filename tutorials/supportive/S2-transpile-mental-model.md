# S2 — Transpile mental model

## The pipeline

```
.pys source  →  lex → parse → sem → emit  →  Python text  →  run
```

Diagrams of the same flow: [`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md).

You edit **`.pys`**. The runner/transpiler produces Python. IDE diagnostics usually
come from the same front-end checks as the transpile step.

## Where to look when something fails

| Symptom | Likely layer | Move |
|---------|--------------|------|
| Red squiggle / transpile message with line | PYS checks | Fix the `.pys` line; read the message as a contract conflict |
| “Generated Python is invalid” | Edge case / bug or exotic construct | Simplify the line; report if it looks wrong |
| Runtime exception in terminal | Python running generated code | Read the traceback; map back to your `.pys` logic |
| “Cannot find module” | Import / `pys.deps` / path | [JIT: imports](../jit/J-function-import.md) |

## Teaching implication

Do not debug by pasting generated Python into the editor as your source of truth.
Keep authority in the `.pys` file; treat Python as an output.

Return to the task.
