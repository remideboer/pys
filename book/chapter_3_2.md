# 4.2. Loops

Three shapes:

```pys
# C-style
loop (int i = 0, i < 3, i++) {
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

Without `break`, the loop would keep walking `"Sam"` after `"Lin"` was
already found. With `break`, control jumps to the first statement **after**
the loop’s closing `}`.

## Skipping one pass: `continue`

`continue` ends **only the current iteration** and jumps to the next one
(the next value, or the next C-style step). Use it to skip work you do not
want for some items.

```pys
loop (int i = 1, i <= 6, i++) {
    if (i % 2 == 0) {
        continue
    }
    print(i)
}
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
> fall through to the next `case` (see [Enums and switch](chapter_3_5.md)).
> In a `loop`, `continue` always means “next iteration.”

## Block scope

Names declared inside a loop’s `{ … }` exist only until that closing
brace. After the loop, they are gone — that is **block scope**.

```pys
loop (int i = 0, i < 1, i++) {
    int scratch = 10
    print(scratch)
}
# print(scratch)  # does not compile — scratch lived only inside the loop
```

### Exercise

> Sum the numbers 1..10 into `int total` with a C-style loop and print the
> total. Then change the loop so that when `total` reaches or exceeds `20`,
> you `break` early — confirm the printed total is less than `55`.

---

[Previous: Control flow](chapter_3_1.md) · [Next: Arrays and lists](chapter_3_3.md)
