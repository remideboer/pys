# 4.4. Dicts, tuples, and sets

Use typed literals (see also [Data structures](basics_data.md)):

```pys
dict<string, int> ages = {}
ages["Ada"] = 36
print(ages["Ada"])

tuple<int, string> row = (1, "Ada")
print(row[1])

set<string> tags = {"work", "home"}
print(len(tags))
```

Output:

```text
36
Ada
2
```


- **dict** — key → value lookup (`{}` empty or `{"k": v}` keyed).
- **tuple** — fixed-length sequence (`(a, b)` or singleton `(a,)`).
- **set** — unique elements; order is not the point (`{}` empty when typed `set`).

> **Sidebar — braces and arrays**
>
> The same `{ … }` shape initializes `int[][]` grids in array chapters. The
> **declared type** decides whether braces mean dict, set, list, or array.

### Exercise

> Make a dict from country code to country name with two entries. Print one
> value by key.

---

[Previous: Arrays and lists](chapter_3_3_arrays_and_lists.md) · [Next: Enums and switch](chapter_3_5_enums_and_switch.md)
