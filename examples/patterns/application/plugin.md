# Plugin

**Category:** Application  
**Demo:** [plugin.pys](plugin.pys)  
**Wikipedia / ref:** [Plugin](https://en.wikipedia.org/wiki/Plugin)

## Intent

Host registers extensions by interface and runs them.

## Prompting an AI

**Say this:** “ReportHost.register(SalesPlugin); runAll.”

**Not this:** “Hard-code every report type in a switch.”

**Confusion to avoid:** Plugin ≠ Dependency Injection alone.

## Run

```text
python -m transpiler run examples/patterns/application/plugin.pys
```
