# CER-032: `toBin` / `toHex` / `toOct` display builtins

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-06 |
| Scope | `sem` (builtins + arity/types); `emit/python` (`_pys_to_bin` / `_hex` / `_oct`); examples; highlighter; LANGUAGE |
| Architecture | [ADR-024](../adr/ADR-024-base-display-builtins.md) |

## Context

Students interfacing with hardware could write `0b` / `0x` literals and bitwise
ops (CER-006) but could only **print** decimal unless they imported Python
`bin` / `hex`.

## Entry 1 — Phase A: bare converters

### Pre-behavior

No PYS builtins for base display; `print(0b1010)` → `10`.

### Why it hurt

Register / bit dumps required `import bin from builtins` and noisy `0b` prefixes.

### Post-behavior

- `toBin(value)` / `toHex(value)` / `toOct(value)` → `string`, no import
- Digits only (no `0b` / `0x` / `0o`); hex lowercase
- Value must be int-like and ≥ 0 (runtime helper rejects negatives)

### Evidence

`tests/test_to_bin_hex_oct.py`; `examples/int_literals.pys`.

## Entry 2 — Phase B: optional width padding

### Pre-behavior

N/A (ships with Entry 1).

### Why it hurt

`byte` dumps need fixed width (`10111101`, `bd`), not minimal Python digits.

### Post-behavior

- Second argument: bits for `toBin`, digit count for `toHex` / `toOct`
- Left-pad with `'0'`; never truncate if the value needs more digits
- Width must be ≥ 1

### Evidence

Same tests (width cases).

## Entry 3 — gated emit helpers

### Post-behavior

`_pys_to_bin` / `_pys_to_hex` / `_pys_to_oct` emit only when used
(`needs_base_display`), so unrelated goldens stay stable.

### Evidence

Goldens without these calls unchanged; unit tests assert helpers appear when used.

## Trade-offs

- No interpolation tags (`#bin`) yet — functions carry width cleanly.
- No `parseBin` / `parseHex` in this CER.
- Negatives rejected rather than two's-complement formatting.
