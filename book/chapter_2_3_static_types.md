# 3.3. Static types and casts

Common primitives:

| Type | Example |
|------|---------|
| `int` | `10`, `0xFF` |
| `float` | `3.14` |
| `string` | `"hello"` |
| `bool` | `true` / `false` |
| `char` | `'A'` |

Prefer an explicit type on the left when teaching or when the initializer
is unclear. Use `var` when the right-hand side already makes the type
obvious.

## Casts

```pys
float speed = 12.9
int whole = (int) speed
print(whole)
```

Output:

```text
12
```


Casts are explicit on purpose — silent narrowing is a common bug in less
strict languages.

## Width aliases

Aliases like `byte`, `nibble`, and `int16` teach bit-sized ranges. They
still emit as Python `int`, but **out-of-range literals are rejected**.

```pys
byte flags = 0b1011_1101
nibble n = 0xA
int16 port = 8080
print(flags)
print(n)
print(port)
# byte tooBig = 300   # does not compile — outside 0..255
```

*Compile error if the commented line is uncommented.*



### Exercise

> Store `9.81` as a `float`, cast to `int`, and print both with typed
> interpolation (`#f{…}` and `#i{…}`).

---

[Previous: Variables](chapter_2_2_variables.md) · [Next: Running and checking your work](chapter_2_4_running_and_checking.md)
