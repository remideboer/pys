# 4.4. Dicts, tuples, and sets

```pys
dict<string, int> ages = {}
ages["Ada"] = 36
print(ages["Ada"])

tuple<int, string> row = (1, "Ada")
print(row[1])

set<string> tags = {"work", "home"}
print(len(tags))
```

- **dict** — key → value lookup.
- **tuple** — fixed-length, mixed types allowed in the type arguments.
- **set** — unique elements; order is not the point.

### Exercise

> Make a `dict<string, string>` from country code to country name with two
> entries. Print one value by key.

---

[Previous: Arrays and lists](chapter_3_3.md) · [Next: Enums and switch](chapter_3_5.md)
