# JIT — Libraries and generics

## Import package

```pys
import mysql.connector
import tkinter as tk
```

Declare packages in project `pys.deps` when they are not stdlib.

## Restate weak returns

```pys
list<tuple<int, string>> rows = cursor.fetchall()
loop (tuple<int, string> row in rows) {
    print("#i{row[0]} #s{row[1]}")
}
```

## Collections (type position)

`list`, `dict`, `tuple`, `set` with `<…>` type arguments in declarations and loop variables.

Model: [S4](../supportive/S4-types-at-boundaries.md)
