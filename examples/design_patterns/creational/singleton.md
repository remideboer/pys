# Singleton

**Category:** Creational  
**Demo:** [singleton.pys](singleton.pys)  
**Wikipedia:** [Singleton pattern](https://en.wikipedia.org/wiki/Singleton_pattern) · [Design Patterns (book)](https://en.wikipedia.org/wiki/Design_Patterns)

## Intent

Ensure a class has only one instance and provide a global point of access to it.

## Explanation

`getInstance()` lazily creates and returns the sole `Logger`. Both callers share the same object (write count accumulates). Classic form is shown for literacy; in applications prefer constructor injection or a composition root over a hidden global.

## Classic structure (UML)

```mermaid
classDiagram
    class Singleton {
        -instance
        -Singleton()
        +getInstance()$ Singleton
    }
    class Client
    Client --> Singleton : getInstance()
```

## This demo

`Logger` is the singleton; `getInstance()` is the global access point; the constructor is private.

```mermaid
classDiagram
    class Logger {
        -instance
        -Logger()
        +getInstance()$ Logger
        +info(message)
    }
```

## Real-world use cases

- Process-wide logging or metrics sinks (historically; often replaced by DI).
- Hardware device drivers that must own a single connection handle.
- Caches or thread pools that must not be constructed twice by accident.

## Run

```text
python -m transpiler run examples/design_patterns/creational/singleton.pys
```
