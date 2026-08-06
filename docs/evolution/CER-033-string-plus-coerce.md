# CER-033: String-involved `+` concatenates with coerce

| | |
| --- | --- |
| Status | Accepted |
| Date | 2026-08-06 |
| Scope | docs (`LANGUAGE`); tests; book / GUI teaching examples |
| Architecture | (emit already implements — document + lock) |

## Context

Emit’s `_plus` already left-associates `+` and, once a string appears in the
chain, wraps non-string operands with `str(...)` (same idea as the legacy
`language_spec` rewriter). Teaching materials still wrote
`str(birthYear)` inside concatenations, implying an explicit cast was
required in PYS source.

## Entry 1 — document and test as first-class rule

### Pre-behavior

LANGUAGE had a one-line note; examples and the basics book used redundant
`str(...)` in `"..." + value` chains. Tests covered mostly numeric
*literals* with strings, not typed identifiers.

### Why it hurt

Beginners learned that every non-string glue needed `str(...)`, fighting the
actual language rule and cluttering first programs.

### Post-behavior

- LANGUAGE § operators spell out: both numeric → arithmetic; either side
  `string` → concatenation with coerce of the other operand(s).
- Explicit `str(x)` remains for assignment / teaching conversion without a
  string sibling.
- Tests lock `fix int birthYear` (and left/right order) under concat.
- Book + temperature GUI samples drop unnecessary concat-side `str(...)`.

### Evidence

`tests/test_string_plus_coerce.py`; updated `book/basics.md` and related
examples.

## Trade-offs

- Coercion uses the Python emit target’s `str(...)` (e.g. `true` → `True`).
- Mass rewrite of every `str(...)` in `examples/` is out of scope; only
  concat teaching paths were cleaned.
