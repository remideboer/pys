# Chain of Responsibility

**Category:** Behavioral  
**Demo:** [chain_of_responsibility.pys](chain_of_responsibility.pys)  
**Wikipedia:** [Chain of Responsibility pattern](https://en.wikipedia.org/wiki/Chain-of-responsibility_pattern) · [Design Patterns (book)](https://en.wikipedia.org/wiki/Design_Patterns)

## Intent

Avoid coupling the sender of a request to its receiver by giving more than one object a chance to handle the request. Chain the receiving objects and pass the request along the chain until an object handles it.

## Explanation

Each `Handler` may handle the request or forward to `next`. `AuthHandler` then `LogHandler` form a pipeline. Order matters; unhandled requests fall off the end.

## Classic structure (UML)

```mermaid
classDiagram
    class Handler {
        +setNext()
        +handle()
    }
    class ConcreteHandlerA
    class ConcreteHandlerB
    class Client
    Handler <|-- ConcreteHandlerA
    Handler <|-- ConcreteHandlerB
    Handler --> Handler : next
    Client --> Handler
```

## This demo

`Handler` is the base; `AuthHandler` and `LogHandler` are links; the client starts at the head of the chain.

```mermaid
classDiagram
    class Handler
    class AuthHandler
    class LogHandler
    Handler <|-- AuthHandler
    Handler <|-- LogHandler
    Handler --> Handler : next
```

## Real-world use cases

- HTTP middleware / servlet filter chains.
- GUI event bubbling (widget → parent → window).
- Support ticket escalation (L1 → L2 → L3) until resolved.

## Run

```text
python -m transpiler run examples/design_patterns/behavioral/chain_of_responsibility.pys
```
