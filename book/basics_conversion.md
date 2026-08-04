# 2.6. Conversion

Values have types. Sometimes you need to **convert** from one type to
another — for example text from the keyboard into an `int`.

## Built-in conversions

```pys
string raw = "42"
int n = int(raw)
float f = float("3.14")
string label = str(n)
print(label)
```

- `int(...)` — parse an integer (or convert from another numeric form).
- `float(...)` — parse a floating-point number.
- `str(...)` — turn a value into a string for printing or concatenation.

## Explicit casts

When both sides are numeric (or otherwise cast-compatible), you can write
a cast:

```pys
float temperature = 18.7
int whole = (int) temperature
print(whole)
```

`(int) temperature` truncates toward zero for this kind of cast — you get
`18`, not a rounded `19`.

### Exercise

> Convert `"100"` to an `int`, add `25`, convert the sum back to a
> `string`, and print `"total="` concatenated with that string.

---

[Previous: Loops](basics_loops.md) · [Next: Null and missing values](basics_null.md)
