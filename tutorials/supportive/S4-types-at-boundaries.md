# S4 — Types at library boundaries

## The idea

Python libraries often return **weak** shapes (`list`, bare `tuple`). PYS lets you
**restate** the shape you believe is true:

```pys
list<tuple<int, string, string>> rows = mycursor.fetchall()
```

That restatement is a contract between you and your own code — not a proof that
MySQL agreed. If the database changes, your types become lies; the program may
still “run” until a use site breaks.

## How to think

1. Infer what one element *means* (id, name, …).  
2. Write the strongest honest generic you can.  
3. Use typed loops / `#i` / `#s` so mismatches fail early.

Untyped `loop (tuple x in rows)` is a temporary scaffold — finish by naming element types.

## Tie-in

JIT: [library boundary](../jit/J-library.md). Showcase patterns live in `examples/main.pys`.
