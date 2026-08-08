# Service layer

**Category:** Application  
**Demo:** [service_layer.pys](service_layer.pys)  
**Related:** [repository](../persistence/repository.md) · [Dependency Injection](../general/dependency_injection.md)

## Intent

Put **use-case orchestration** in an application service: load ports, enforce
workflow, return a result — without HTTP, GUI, or SQL details.

## Explanation

`CreateOrderService.execute` is the use-case. It depends on `OrderRepository`
and `Clock` ports. Controllers / CLI stay thin and call the service.

## Prompting an AI

**Say this:** “Create a `CreateOrderService` application service that takes
`OrderRepository` and `Clock` via constructor. Keep HTTP out of this class.”

**Not this:** “Put order creation, SQL, and JSON encoding in one handler function.”

**Confusion to avoid:** Service layer ≠ domain entity methods (entities hold
business data/rules; the service coordinates a use-case).

## Run

```text
python -m transpiler run examples/patterns/application/service_layer.pys
```
