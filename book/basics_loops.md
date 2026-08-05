# 2.5. Loops

A **loop** repeats a block until a condition says stop — or until every
item in a collection has been visited.

## Count with a C-style loop

```pys
loop (int i = 0; i < 3; i++) {
    print(i)
}
```

Output:

```text
0
1
2
```


Reads as: start `i` at 0; while `i < 3`; after each body, do `i++`
(add one). Prints `0`, then `1`, then `2`.

> Inside this loop shape, the loop variable is treated as fixed for that
> iteration — you advance it in the step clause (`i++`), not by random
> assignments in the middle of the body.

> **Sidebar — why `;` in the header?**
>
> The three parts of a C-style loop are separated by `;`, just like in
> C#/Java `for (…; …; …)`. That matches PYS’s optional statement `;`
> (required only when two statements share one line).

## While-style loop

```pys
int counter = 0
loop (counter < 3) {
    print(counter)
    counter++
}
```

Output:

```text
0
1
2
```


Same three prints; the condition is checked before each pass.

## When two values must change

The C-style form is intentionally for **one** counter. Its start, condition,
and step all name that counter, and you cannot change it in the body. For two
or more changing values, use the while-style form you already know:

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

The two starting values and both updates are visible on their own lines. PYS
does not hide them in a denser multi-variable loop header.

## Foreach — walk a collection

```pys
list<string> names = ["Ada", "Tom", "Lin"]
loop (string name in names) {
    print("Hello, " + name)
}
```

Output:

```text
Hello, Ada
Hello, Tom
Hello, Lin
```


Each pass binds `name` to the next element.

### Exercise

> Print the numbers 1 through 5 using a C-style `loop`. Then print each
> character of the string `"PYS"` by looping over a `list` you build, or by
> printing indices into the string if you prefer.

---

[Previous: Data structures](basics_data.md) · [Next: Conversion](basics_conversion.md)
