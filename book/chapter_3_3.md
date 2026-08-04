# 4.3. Arrays and lists

## Arrays

```pys
int[] numbers = [1, 2, 3, 4, 5]
print(numbers[0])
print(numbers[1:3])
```

> **Sidebar — inclusive slice end**
>
> In PYS source, `numbers[1:3]` includes index `3`. So for
> `[1, 2, 3, 4, 5]` that prints the three values at indexes 1, 2, and 3
> (`2`, `3`, `4`). Python’s own slices exclude the end index — the
> transpiler adjusts when emitting Python.

Multi-dimensional:

```pys
int[][] grid = [[1, 2], [3, 4]]
print(grid[1][0])
```

## Lists

```pys
list<int> scores = [10, 20, 30]
scores.append(40)
print(len(scores))
```

Prefer `list<T>` for growable sequences; prefer `T[]` when teaching
array-shaped memory.

### Exercise

> Build `int[]` with five values. Print the middle element and a slice of
> the first three (`[0:2]` inclusive end → three elements).

---

[Previous: Loops](chapter_3_2.md) · [Next: Dicts, tuples, and sets](chapter_3_4.md)
