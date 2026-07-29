# JIT — Print and interpolation

## Forms

```pys
print("hello")
print("n={n}")
print("n=#i{n}, name=#s{name}")
```

## Typed slots

| Marker | Requires |
|--------|----------|
| `#i{…}` | `int` |
| `#f{…}` | `float` |
| `#s{…}` | `string` |
| `#c{…}` | `char` |
| `#b{…}` | `bool` |
| `#o{…}` | object (not a primitive) |

Indexed tuple fields work when the tuple carries type args: `x` as `tuple<int, string>` → `#i{x[0]}`, `#s{x[1]}`.

## Plain `{name}`

Unmarked `{name}` interpolates without that check — useful while drafting; prefer typed markers when the value’s kind matters.
