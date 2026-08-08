# Specification

**Category:** Application  
**Demo:** [specification.pys](specification.pys)  
**Wikipedia / ref:** [Specification](https://en.wikipedia.org/wiki/Specification_pattern)

## Intent

Composable business rules (and/or/not) over a candidate.

## Prompting an AI

**Say this:** “AndSpec(MinAgeSpec(18), ActiveSpec()).”

**Not this:** “Giant if-else of unrelated rules in the service.”

**Confusion to avoid:** Specification ≠ Strategy (rules vs algorithms).

## Run

```text
python -m transpiler run examples/patterns/application/specification.pys
```
