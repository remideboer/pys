# 2.5. Loops

A **loop** repeats a block until a condition says stop — or until every
item in a collection has been visited.

## Count with a C-style loop

```pys
loop (int i = 0, i < 3, i++) {
    print(i)
}
```

Reads as: start `i` at 0; while `i < 3`; after each body, do `i++`
(add one). Prints `0`, then `1`, then `2`.

> Inside this loop shape, the loop variable is treated as fixed for that
> iteration — you advance it in the step clause (`i++`), not by random
> assignments in the middle of the body.

## While-style loop

```pys
int counter = 0
loop (counter < 3) {
    print(counter)
    counter++
}
```

Same three prints; the condition is checked before each pass.

## Foreach — walk a collection

```pys
list<string> names = ["Ada", "Tom", "Lin"]
loop (string name in names) {
    print("Hello, " + name)
}
```

Each pass binds `name` to the next element.

### Exercise

> Print the numbers 1 through 5 using a C-style `loop`. Then print each
> character of the string `"PYS"` by looping over a `list` you build, or by
> printing indices into the string if you prefer.

---

[Previous: Data structures](basics_data.md) · [Next: Conversion](basics_conversion.md)
