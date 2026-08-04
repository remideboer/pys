# 2.4. Data structures

One variable holds one value. Real programs juggle **collections** of values.

## Lists

A `list` is an ordered row of items of one element type:

```pys
list<string> names = ["Ada", "Tom", "Lin"]
print(names[0])
print(len(names))
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

## Arrays

For teaching fixed-element sequences of primitives, PYS also has arrays:

```pys
int[] scores = [10, 20, 30]
print(scores[1])
```

Prefer `list<T>` when working with growing collections; prefer `T[]` when
you want array-shaped teaching examples. Session 2 goes deeper.

## Tuples

A `tuple` groups a fixed number of values that may have different types:

```pys
tuple<string, int> person = ("Ada", 36)
print(person[0])
print(person[1])
```

## Dicts

A `dict` maps keys to values:

```pys
dict<string, int> ages = {}
ages["Ada"] = 36
ages["Tom"] = 41
print(ages["Ada"])
```

### Exercise

> Create a `list<string>` of three foods you like. Print the second item
> (index `1`) and the length of the list.

---

[Previous: Making choices](basics_choices.md) · [Next: Loops](basics_loops.md)
