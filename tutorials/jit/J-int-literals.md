# JIT — Binary / hex literals and bitwise ops

## Forms

```pys
int i = 0b1010
byte flags = 0b1011_1101
nibble n = 0xA
int16 mask = 0xFFFF

print(i & 0b0101)
print(i | 0b0101)
print(i xor 0b0101)
print(~i)
print(i << 1)
print(i shift right 1)
print(2 ** 3)
print(10 // 3)
```

## Rules

1. Literals: `0b`/`0B`, `0x`/`0X`, decimal; optional `_` between digits  
2. Width aliases (`byte`, `nibble`, `int16`, `int32`, `int64`, `dword`) are
   **unsigned** ranges on `int` — out-of-range literals error  
3. Bitwise: `& | ^ ~ << >>` and `xor` / `shift left` / `shift right`  
4. `and` / `or` / `not` stay **logical** (not bitwise)  
5. Rotate (`<<<` / `>>>`) is not implemented yet  

See [LANGUAGE](../../docs/LANGUAGE.md) § Primitive types.
