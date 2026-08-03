# Teacher notes — PYS tutorial track

## Design intent

The track follows **4C/ID**:

- **Learning tasks** are authentic and whole (a log, a batch filter, a shared toolbox, a fleet board).
- **Supportive information** is separated from step-by-step syntax so students do not confuse “recipe” with “model”.
- **JIT cards** are procedural and short; point students there *during* a task, not as pre-reading.
- **Part-task practice** targets only skills that must become fluent (typed interpolation, declaration shape, visibility choice under time pressure).

Scaffolding inside each task class fades: **worked → completion → conventional**.

## How to coach

| Student behavior | Prefer |
|------------------|--------|
| “What’s the syntax for X?” | JIT card, not a lecture |
| “Why did they use `fix` / `package`?” | Supportive page + ask them to restate |
| Copies worked example blindly | Ask for a 60-second oral walkthrough before B |
| Stuck on conventional brief | Offer a *completion* variant, don’t restart at A unless lost |
| Flaky `#s` / `#i` | Part-task drill, 5 minutes, then return to task |
| Order diagnostics (`pys.order-*`, method before fields, late import) | [J-member-order](jit/J-member-order.md); habit framing [S7](supportive/S7-order-as-habit.md) — do not claim Java/C# will reject |

## Assessment (product criteria)

Each task folder has success criteria in its `README.md`. Prefer judging the **artifact**
(runs, types honest, visibility intentional) over keyword quizzes.

Suggested rubric dimensions (0–2 each):

1. Runs without transpile/runtime error  
2. Types match the data story  
3. Control structure matches the process (not accidental complexity)  
4. Module/class boundaries match the brief (T3–T4)  
5. Can explain two design choices without reading the file  

## Sequencing

Default: T1 → T2 → T3 → T4.  
Skip T1 only for students already fluent in typed declarations + interpolation.

Do not unlock T4 supportive “objects as responsibility” as mandatory pre-reading;
assign it when inheritance debates appear.

## Distribution

Ship the repo (or a classroom fork) with:

- `tutorials/` (this track)
- `pys-language` extension VSIX or install instructions
- `examples/` as a *reference zoo*, not the curriculum path
