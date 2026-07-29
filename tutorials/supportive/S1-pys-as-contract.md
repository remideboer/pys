# S1 — PYS as a contract language

## The idea

A type in PYS is not decoration. It is a **promise** you make to the next reader
(and to the transpiler): “this name stands for this kind of value.”

Python will still run many mistakes. PYS is stricter **early**, so the mistake
shows up next to the line you are thinking about — not later in a stack trace
from generated code you did not write by hand.

## Mental model

```
intent  →  typed name  →  checked uses  →  Python that matches the intent
```

Example of a broken promise:

```pys
int count = 3
print("#s{count}")   # #s demands string; count is int → reject
```

The rejection is the pedagogy: the contract was visible, so the repair is local.

## What to practice in tasks

When you choose `int` vs `float` vs `string`, ask: **what question does this value answer?**
If you cannot answer in one sentence, the type is probably wrong or the design is foggy.

Return to your task. Open [JIT: declarations](../jit/J-declare.md) only for forms.
