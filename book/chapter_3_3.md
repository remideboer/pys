# 4.3. Arrays and lists

## Arrays

```pys
int[] numbers = [1, 2, 3, 4, 5]
print(numbers[0])
print(numbers[1])
print(numbers[2])
print(numbers[3])
```

Output:

```text
1
2
3
4
```


> **Sidebar — inclusive slice end**
>
> PYS also allows slices like `numbers[1:3]`. The end index is **inclusive**
> in PYS source (the transpiler adjusts for Python). Prefer indexing while
> learning; revisit slices when you need a sub-range.

Multi-dimensional:

```pys
int[][] grid = [[1, 2], [3, 4]]
print(grid[1][0])
```

Output:

```text
3
```


## Lists

```pys
list<int> scores = [10, 20, 30]
scores.append(40)
print(len(scores))
```

Output:

```text
4
```


Prefer `list<T>` for growable sequences; prefer `T[]` when teaching
array-shaped memory.

### Exercise

> Build `int[]` with five values. Print the middle element and a slice of
> the first three (`[0:2]` inclusive end → three elements).

---

[Previous: Loops](chapter_3_2.md) · [Next: Dicts, tuples, and sets](chapter_3_4.md)
