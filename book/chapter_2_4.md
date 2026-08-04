# 3.4. Running and checking your work

## Run

```shell
python -m transpiler run path/to/file.pys
```

## Transpile only

See the generated Python without executing:

```shell
python -m transpiler transpile path/to/file.pys
```

## Editor feedback

With the PYS extension, save the file and read diagnostics in the Problems
panel. Prefer fixing **errors** first; warnings (for example enum naming
style) still teach good habits.

## A tiny checklist

1. Does the program compile?
2. Does it print what you expected for one happy input?
3. Did you try one bad input on purpose?

That third step is the seed of testing — Session 6 grows it into a habit.

### Exercise

> Take any earlier example, introduce a deliberate type error, run or save,
> and write one sentence describing what the diagnostic asked you to fix.

---

[Previous: Static types](chapter_2_3.md) · [Next: Session 2](chapter_3.md)
