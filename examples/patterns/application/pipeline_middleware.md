# Pipeline / middleware

**Category:** Application  
**Demo:** [pipeline_middleware.pys](pipeline_middleware.pys)  
**Wikipedia / ref:** [Pipeline / middleware](https://en.wikipedia.org/wiki/Pipeline_(software))

## Intent

Ordered wrappers around a handler (cousin of Chain of Responsibility).

## Prompting an AI

**Say this:** “Auth then logging middleware around AppHandler.”

**Not this:** “Put auth checks inside every handler body.”

**Confusion to avoid:** Middleware ≠ CoR always (same family).

## Run

```text
python -m transpiler run examples/patterns/application/pipeline_middleware.pys
```
