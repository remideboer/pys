# Service Locator (anti-pattern)

**Category:** General  
**Demo:** [service_locator_antipattern.pys](service_locator_antipattern.pys)  
**Wikipedia / ref:** [Service Locator (anti-pattern)](https://en.wikipedia.org/wiki/Service_locator_pattern)

## Intent

Hidden global lookup — contrast with constructor DI. Prefer DI.

## Prompting an AI

**Say this:** “Show ServiceRegistry ambient lookup vs InjectedOrderService(logger).”

**Not this:** “Add a service locator for all new dependencies.”

**Confusion to avoid:** Service Locator ≠ Dependency Injection.

## Run

```text
python -m transpiler run examples/patterns/general/service_locator_antipattern.pys
```
