# 4.4. Dicts, tuples, and sets

Construct with Python builtins (see also [Data structures](basics_data.md));
typed `dict` / `tuple` / `set` names still matter on library APIs.

```pys
from builtins import dict
from builtins import tuple
from builtins import set

var ages = dict()
ages["Ada"] = 36
print(ages["Ada"])

var row = tuple([1, "Ada"])
print(row[1])

var tags = set(["work", "home"])
print(len(tags))
```

Output:

```text
36
Ada
2
```


- **dict** — key → value lookup.
- **tuple** — fixed-length sequence (often mixed types from libraries).
- **set** — unique elements; order is not the point.

### Exercise

> Make a dict from country code to country name with two entries. Print one
> value by key.

---

[Previous: Arrays and lists](chapter_3_3.md) · [Next: Enums and switch](chapter_3_5.md)
