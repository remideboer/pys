# Drill — Typed interpolation

For each line, write the **marker** that should wrap the expression (`#i`, `#f`, `#s`, `#b`, or `#o`).

Assume:

```pys
int n = 3
float x = 1.5
string name = "Ada"
bool ok = true
Car c = Car("x", "y", 2020)
tuple<int, string> row  # row[0] int, row[1] string
```

1. `print("n=|{n}|")`  
2. `print("x=|{x}|")`  
3. `print("hi |{name}|")`  
4. `print("flag=|{ok}|")`  
5. `print("car=|{c}|")`  
6. `print("id=|{row[0]}| name=|{row[1]}|")`

## Check

Reveal only after you finish: `#i #f #s #b #o` then `#i` and `#s`.

Wrong often? Re-read [JIT print](../jit/J-print-interpolate.md), then redo once.
