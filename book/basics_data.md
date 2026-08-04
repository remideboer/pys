# 2.4. Data structures

One variable holds one value. Real programs juggle **collections** of values.

## Lists

A `list` is an ordered row of items of one element type:

```pys
list<string> names = ["Ada", "Tom", "Lin"]
print(names[0])
print(len(names))
```

Output:

```text
Ada
3
```


- `list<string>` — a list whose elements are strings.
- `names[0]` — the first element (indexing starts at **0**).
- `len(names)` — how many items are in the list.

Growing a list: call `append` to add one item at the end.

```pys
list<string> names = ["Ada"]
names.append("Tom")
print(len(names))
```

Output:

```text
2
```


## Arrays

For teaching fixed-element sequences of primitives, PYS also has arrays:

```pys
int[] scores = [10, 20, 30]
print(scores[1])
```

Output:

```text
20
```


Prefer `list<T>` when working with growing collections; prefer `T[]` when
you want array-shaped teaching examples. Session 2 goes deeper.

## Tuples and dicts (construction)

Typed `tuple<…>` / `dict<…>` names show up often on **library return values**.
To *build* them in beginner programs, use the Python constructors (imported
once at the top of the file):

```pys
from builtins import dict
from builtins import tuple

var person = tuple(["Ada", 36])
print(person[0])
print(person[1])

var ages = dict()
ages["Ada"] = 36
ages["Tom"] = 41
print(ages["Ada"])
```

Output:

```text
Ada
36
36
```


> **Sidebar — typed empty `{}`**
>
> Writing `dict<string, int> ages = {}` is the long-term typed form in the
> language docs, but empty `{}` is not a reliable dict constructor in the
> current toolchain (it can emit as a list). Prefer `dict()` here until you
> take dicts from libraries.

### Exercise

> Create a `list<string>` of three foods you like. Print the second item
> (index `1`) and the length of the list.

---

[Previous: Making choices](basics_choices.md) · [Next: Loops](basics_loops.md)
