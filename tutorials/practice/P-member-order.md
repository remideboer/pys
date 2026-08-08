# Practice — Member and import ordering

Time-box: 5–10 minutes.

## 1. Reorder the class

This fails to transpile. Put kinds in the legal order (`const` → `fix` →
fields → constructor → methods):

```pys
package class Counter {
    public bump() {
        this.n = this.n + 1
    }
    private int n
    public const int LIMIT = 100
    public constructor() {
        this.n = 0
    }
}
```

## 2. Imports first

Move the import so the file parses:

```pys
int x = 1
import math
print(math.sqrt(x))
```

## 3. Struct fix before mutable

```pys
struct Hit {
    int amount
    fix string type
}
```

## Check

1 → `LIMIT`, then `n`, then `Counter()`, then `bump()`.  
2 → `import math` above `int x`.  
3 → `fix string type` above `int amount`.

Habit *why*: [S7](../supportive/S7-order-as-habit.md). Forms: [J-member-order](../jit/J-member-order.md).
