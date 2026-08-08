# Active object

**Category:** Concurrency  
**Demo:** [active_object.pys](active_object.pys)  
**Wikipedia:** [Active object](https://en.wikipedia.org/wiki/Active_object) · [Concurrency pattern](https://en.wikipedia.org/wiki/Concurrency_pattern)

## Intent

Decouple method execution from method invocation so that the object runs in its own thread of control.

## Explanation

Clients call `say`, which **enqueues** a `MethodRequest`. A servant (`pump`) executes requests later in its own `task`. There is no condition-wait for an empty queue — this demo drains a known queue after enqueue. Full Active Object often adds a scheduler and futures; PYS stops short of wait/notify.

## Classic structure (UML)

```mermaid
classDiagram
    class Proxy
    class Scheduler
    class Servant
    class MethodRequest {
        <<interface>>
        +execute()
    }
    Proxy --> Scheduler
    Scheduler o-- MethodRequest
    Scheduler --> Servant
    MethodRequest --> Servant
```

## This demo

`ActiveEngine` is proxy + queue; `PrintRequest` is a method request; `pump` is the servant run inside `tasks`.

```mermaid
classDiagram
    class ActiveEngine
    class MethodRequest {
        <<interface>>
        +execute()
    }
    class PrintRequest
    ActiveEngine o-- MethodRequest
    MethodRequest <|.. PrintRequest
```

## Real-world use cases

- GUI toolkits posting work onto a single UI thread.
- Actor-style services that process a mailbox of messages.
- Hardware drivers that serialize device commands through one worker.

## Run

```text
python -m transpiler run examples/design_patterns/concurrency/active_object.pys
```
