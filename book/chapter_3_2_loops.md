# 4.2. Loops

Three shapes:

```pys
# C-style
loop (int i = 0; i < 3; i++) {
    print(i)
}

# while-style
int n = 0
loop (n < 3) {
    print(n)
    n++
}

# foreach
list<string> xs = ["a", "b"]
loop (string x in xs) {
    print(x)
}
```

Output:

```text
0
1
2
0
1
2
a
b
```

## Why a C-style loop has one counter

PYS deliberately keeps the C-style form narrow. The initializer, condition,
and step must all name the same counter, and that counter is immutable in the
body. This gives the reader one clear answer to: “what controls this loop?”

Java and C++ allow this denser form (the following is **not PYS**):

```java
for (int x = 0, y = 10; x < 3; x++, y++) {
    System.out.println(x + ", " + y);
}
```

Output while both updates stay aligned:

```text
0, 10
1, 11
2, 12
```

Their compilers also accept an extra update to only one value. For example,
this Java body accidentally advances `y` twice during one pass:

```java
for (int x = 0, y = 10; x < 3; x++, y++) {
    if (x == 1) {
        y++;
    }
    System.out.println(x + ", " + y);
}
```

Output — notice that the last two pairs are no longer ten apart:

```text
0, 10
1, 12
2, 13
```

The condition still checks only `x`; nothing guarantees that `y` stays in
step. A different `y += 2` in the header would compile too. C++ expresses the
update with its comma operator, while Java uses a comma-separated update list.

PYS does not add comma-separated counters or a special `{x, y}` group. Use
the existing while-style form when several ordinary mutable values take part:

```pys
int x = 0
int y = 10

loop (x < 3) {
    print("#i{x}, #i{y}")
    x++
    y++
}
```

Output:

```text
0, 10
1, 11
2, 12
```

This is the same algorithm, but initialization and every mutation are visible.
The trade-off is the normal while-loop responsibility: make sure the body
eventually changes the values needed to make the condition false.


## Leaving early: `break`

`break` stops the loop **immediately**. Use it when you have found what you
were looking for and further passes would waste work.

```pys
list<string> names = ["Ada", "Tom", "Lin", "Sam"]
string target = "Lin"
bool found = false

loop (string name in names) {
    if (name == target) {
        found = true
        break
    }
}

if (found) {
    print("found " + target)
} else {
    print("not in the list")
}
```

Output:

```text
found Lin
```


Without `break`, the loop would keep walking `"Sam"` after `"Lin"` was
already found. With `break`, control jumps to the first statement **after**
the loop’s closing `}`.

## Skipping one pass: `continue`

`continue` ends **only the current iteration** and jumps to the next one
(the next value, or the next C-style step). Use it to skip work you do not
want for some items.

```pys
loop (int i = 1; i <= 6; i++) {
    if (i % 2 == 0) {
        continue
    }
    print(i)
}
```

Output:

```text
1
3
5
```


Even numbers hit `continue` and never reach `print`. Odd numbers print:
`1`, `3`, `5`.

> **Sidebar — modulo `%`**
>
> `i % 2` is the remainder after dividing `i` by 2. Remainder `0` means
> even. You will use `%` often in filters and “every Nth item” logic.

> **Sidebar — `continue` in `switch`**
>
> Inside a `switch` statement, bare `continue` means something else:
> fall through to the next `case` (see [Enums and switch](chapter_3_5_enums_and_switch.md)).
> In a `loop`, `continue` always means “next iteration.”

## Block scope

Names declared inside a loop’s `{ … }` exist only until that closing
brace. After the loop, they are gone — that is **block scope**.

```pys
loop (int i = 0; i < 1; i++) {
    int scratch = 10
    print(scratch)
}
# print(scratch)  # does not compile — scratch lived only inside the loop
```

*Compile error if the commented line is uncommented.*



### Exercise

> Sum the numbers 1..10 into `int total` with a C-style loop and print the
> total. Then change the loop so that when `total` reaches or exceeds `20`,
> you `break` early — confirm the printed total is less than `55`.

---

[Previous: Control flow](chapter_3_1_control_flow.md) · [Next: Arrays and lists](chapter_3_3_arrays_and_lists.md)
