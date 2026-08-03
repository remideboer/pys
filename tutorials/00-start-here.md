# Start here

## What you are learning to *do*

Not “list PYS keywords”. You are learning to **deliver small working programs** that
use types as contracts, keep modules honest about what they share, and stay runnable
through the PYS → Python path.

## The learning rule (read once)

1. Open the next **task class** under [`tasks/`](tasks/).
2. Do the **worked example** first: run it, then explain it without looking.
3. Open **JIT cards** only when a concrete step blocks you (link from the task).
4. Read **supportive** pages when you keep making the *same kind of design mistake*
   (wrong boundary, wrong type story) — not for every syntax doubt.
5. Use **practice** drills if a mechanical skill (e.g. `#i` vs `#s`) keeps slipping.

That split is deliberate:

- **JIT** = recurrent *how* (steps, forms, error fixes).
- **Supportive** = non-recurrent *why* (models for new situations).
- **Tasks** = where both meet, on a whole product.

Structs (value types): [J-struct](jit/J-struct.md), design contrast [S6](supportive/S6-struct-vs-dict.md).

Member / import **kind order** (parse errors with educational messages):
[J-member-order](jit/J-member-order.md), habit model [S7](supportive/S7-order-as-habit.md),
drill [P-member-order](practice/P-member-order.md).

Refactoring (preview + binding-aware rename): [J-refactor](jit/J-refactor.md),
[S8](supportive/S8-refactor-as-habit.md).

## Setup checklist

- [ ] `python -m pip install -e .` from the repo root  
- [ ] PYS extension installed (see repo README)  
- [ ] You can run: `python -m transpiler run tutorials/tasks/T1-sensor-log/1-worked.pys`

## First move

Go to **[T1 — Sensor log](tasks/T1-sensor-log/)** and open `1-worked.pys`.
