# 4.3. Arrays and lists

## Arrays

An array is a **fixed consecutive block** of slots in memory. You reach an
element by **start address + offset** (the index). Index `0` is the first
slot; `numbers[2]` means “two steps past the start.”

<figure class="concept-diagram" role="img" aria-label="Array numbers as five consecutive memory slots addressed by start plus offset">
  <div class="diagram-stack">
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>numbers</strong>
      <span>start of a fixed block</span>
    </div>
    <div class="diagram-arrow" aria-hidden="true">↓ consecutive slots</div>
    <div class="diagram-slot-row">
      <div class="diagram-slot is-full"><span style="display:block;font-size:0.75rem;color:var(--muted)">[0]</span>1</div>
      <div class="diagram-slot is-full"><span style="display:block;font-size:0.75rem;color:var(--muted)">[1]</span>2</div>
      <div class="diagram-slot is-full"><span style="display:block;font-size:0.75rem;color:var(--muted)">[2]</span>3</div>
      <div class="diagram-slot is-full"><span style="display:block;font-size:0.75rem;color:var(--muted)">[3]</span>4</div>
      <div class="diagram-slot is-full"><span style="display:block;font-size:0.75rem;color:var(--muted)">[4]</span>5</div>
    </div>
    <div class="diagram-box" style="margin-top:0.5rem">
      <strong>address</strong>
      <span>start + offset · e.g. numbers[2] → start + 2</span>
    </div>
  </div>
  <figcaption>
    One block, no gaps: the index is the offset from the start, not a search
    key.
  </figcaption>
</figure>

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


Prefer `list<T>` for growable sequences; prefer `T[]` when you mean a
**fixed consecutive** block addressed by start + offset (array-shaped memory).

### Exercise

> Build `int[]` with five values. Print the middle element and a slice of
> the first three (`[0:2]` inclusive end → three elements).

---

[Previous: Loops](chapter_3_2_loops.md) · [Next: Dicts, tuples, and sets](chapter_3_4_dicts_tuples_sets.md)
