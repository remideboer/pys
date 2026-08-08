# CQRS (Command Query Responsibility Segregation)

**Category:** Messaging  
**Demo:** [cqrs.pys](cqrs.pys)  
**Wikipedia:** [Command Query Responsibility Segregation](https://en.wikipedia.org/wiki/Command_Query_Responsibility_Segregation)

## Intent

Use different models to **change** state (commands) and to **read** it (queries).

## Explanation

`OrderWriteModel` stores authoritative status; `OrderReadModel` holds a projected
summary updated by `CreateOrderCommand`. Teaching form in one process.

## Classic structure (UML)

```mermaid
classDiagram
    class Command
    class WriteModel
    class ReadModel
    Command --> WriteModel
    Command --> ReadModel
```

## This demo

```mermaid
classDiagram
    class CreateOrderCommand
    class OrderWriteModel
    class OrderReadModel
    CreateOrderCommand --> OrderWriteModel
    CreateOrderCommand --> OrderReadModel
```

## Real-world use cases

- High-read dashboards with denormalized query stores.
- Event-sourced systems projecting read models.

## Run

```text
python -m transpiler run examples/patterns/messaging/cqrs.pys
```
