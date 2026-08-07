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

Output:

```text
42
```


- `int(...)` — parse an integer (or convert from another numeric form).
  Fails at runtime on bad text (there is no recoverable path).
- `float(...)` — parse a floating-point number. Same: bad text is not a
  `result`.
- `str(...)` — turn a value into a string explicitly (e.g. `string label = str(n)`).
  When you already concatenate with `+` and one side is a string, PYS coerces
  the other side for you — `print("n=" + n)` needs no `str(n)`.
- `parseInt(text)` — `result<int, string>`: `ok` on success, `error` on
  failure (preferred for form fields and other recoverable input).
- `parseFloat(text)` — `result<float, string>`: same pattern for floats.

```pys
result<float, string> parsed = parseFloat("3.14")
switch (parsed) {
    case ok(value):
        print(value)
    case error(message):
        print(message)
}
```

Output:

```text
3.14
```

`parseFloat` / `parseInt` accept whatever the Python emit target's
`float(...)` / `int(...)` accept (including forms like `"1e10"` for
floats). That is broader than a hand-written digit scanner — see the
temperature-converter chapter for when that trade-off matters.

## Explicit casts

When both sides are numeric (or otherwise cast-compatible), you can write
a cast:

```pys
float temperature = 18.7
int whole = (int) temperature
print(whole)
```

Output:

```text
18
```


`(int) temperature` truncates toward zero for this kind of cast — you get
`18`, not a rounded `19`.

### Exercise

> Convert `"100"` to an `int`, add `25`, convert the sum back to a
> `string`, and print `"total="` concatenated with that string.

---

[Previous: Loops](basics_loops.md) · [Next: Null and missing values](basics_null.md)
