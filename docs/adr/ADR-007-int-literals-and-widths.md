# ADR-007: Binary/hex literals, bitwise ops, unsigned width aliases

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-02 |
| Commits | (int literals increment) |
| Code detail | [CER-006](../evolution/CER-006-int-literals-bitwise-widths.md) |

## Context

Hardware-facing teaching (ESP32 / Arduino / MicroPython) needs binary and hex
literals, bitwise operators, and small fixed-width integer names. Requirements:
`requirements/binairy_hexadecimal_literals.pys`.

## Decision

1. **Literals:** `0b`/`0B`/`0x`/`0X` and decimal with optional `_` separators;
   emit Python int literals unchanged.
2. **Bitwise symbols:** `& | ^ ~ << >>` plus `**` and `//`; word forms `xor`,
   `shift left`, `shift right` normalize to `^` / `<<` / `>>`.
3. **`and` / `or` / `not` remain logical** (short-circuit). Never redefine them
   as bitwise.
4. **Width aliases** `nibble`/`byte`/`int16`/`int32`/`dword`/`int64` are
   unsigned ranges on `int` (matching sample prints). Emit as plain `int`; SA
   rejects out-of-range literals.
5. **Rotate deferred** (`<<<` / `>>>`, rotate word forms) — explicit error;
   tracked as [F-001](../TODO-FUTURE.md#f-001-bitwise-rotate).

## Consequences

- Expression precedence gains bit/shift/power levels (EBNF + railroad synced).
- Pedagogy: JIT `J-int-literals`; example `examples/int_literals.pys`.
- Security boundaries (ADR-001) unchanged.
- **Display** of ints in other bases is separate: [ADR-024](ADR-024-base-display-builtins.md)
  (`toBin` / `toHex` / `toOct`). Literals stay `0b` / `0x` in source; print
  stays decimal unless those builtins are used.

## Rejected alternatives

- Making `and`/`or`/`not` bitwise on ints (breaks boolean teaching).
- Signed wraparound / silent truncation for width aliases.
- Shipping rotate in the same increment.
