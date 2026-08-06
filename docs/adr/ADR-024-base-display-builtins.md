# ADR-024: Base display builtins (`toBin` / `toHex` / `toOct`)

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-06 |
| Code detail | [CER-032](../evolution/CER-032-to-bin-hex-oct.md) |
| Related | [ADR-007](ADR-007-int-literals-and-widths.md) (literals / bitwise / widths) |

## Context

Hardware teaching (ESP32 / Arduino / MicroPython) already has binary and hex
**literals** and bitwise ops (ADR-007), but `print` / `str` / `#i{…}` always
show **decimal**. Students who need register dumps imported Python `bin` /
`hex` from `builtins`, which is ceremony, prefixes (`0b` / `0x`) that clutter
UART logs, and no zero-padding to `byte` / `nibble` width.

Typed interpolation `#b{…}` already means **bool** (EBNF / LANGUAGE) — binary
display must not reuse that tag.

## Decision

1. **Seeded builtins** (no import), returning `string`:
   - `toBin(value)` / `toBin(value, widthBits)`
   - `toHex(value)` / `toHex(value, widthDigits)`
   - `toOct(value)` / `toOct(value, widthDigits)`
2. **`value`** is any int-like type (`int`, `byte`, `nibble`, …). It must be
   **≥ 0** (unsigned teaching model aligned with ADR-007 width aliases).
3. **No radix prefix** in the returned string (`1010`, `bd`, `12` — not
   `0b…` / `0x…` / `0o…`). Literals in source keep `0b` / `0x`; display is for
   dumps.
4. **Hex is lowercase** (`ff` not `FF`).
5. **Optional width** (Phase B):
   - `toBin`: `widthBits` ≥ 1 → left-pad with `'0'` to that many bits.
   - `toHex` / `toOct`: `widthDigits` ≥ 1 → left-pad with `'0'` to that many
     digits.
   - If the natural representation is **longer** than `width`, keep the longer
     form (**no truncation** — silent cut would hide overflow in hardware labs).
6. **Arity** is 1 or 2. Wrong arity / non-int-like args / negative value /
   width &lt; 1 are compile-time or well-defined runtime errors with tips
   (implementation: sem for arity/types; emit helper for negative/width).
7. **No** `#bin` / `#hex` interpolation tags in this decision (functions first;
   tags deferred).
8. **No** seeded Python-named `bin` / `hex` / `oct` builtins (names reserved for
   possible later alias only if teaching requires them — not part of this ADR).
9. **`parseBin` / `parseHex`** (text → `result<int,string>`) are **out of scope**
   here; follow CER-030 style in a later record if needed.
10. Rotate remains [F-001](../TODO-FUTURE.md#f-001-bitwise-rotate).

## Consequences

- Hardware labs can write `print(toHex(status, 2))` / `print(toBin(flags, 8))`
  without imports.
- Emit lowers to private helpers (gated on use, like parse helpers).
- ADR-007 unchanged for literals and bitwise; this ADR only covers **display**.
- `#b{…}` stays bool.

## Rejected alternatives

| Alternative | Why rejected |
| --- | --- |
| Seed Python `bin` / `hex` / `oct` only | Prefixes + no padding; weaker transfer than `to*` |
| Reuse `#b{…}` for binary | Collides with bool typed interpolation |
| `#bin{…}` / `#hex{…}` tags first | Padding needs an argument; functions are clearer |
| `format(value, spec)` | Second mini-language; weak teaching signal |
| Methods on ints (`x.toHex()`) | Scalars stay non-OO |
| Truncate when value exceeds width | Hides overflow in register teaching |
| Allow negatives (Python-style `-0b…`) | Conflicts with unsigned width pedagogy |

## References

- [ADR-007](ADR-007-int-literals-and-widths.md)
- [CER-006](../evolution/CER-006-int-literals-bitwise-widths.md)
- Requirements provenance: `requirements/binairy_hexadecimal_literals.pys`
