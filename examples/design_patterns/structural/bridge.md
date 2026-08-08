# Bridge

**Category:** Structural  
**Demo:** [bridge.pys](bridge.pys)  
**Wikipedia:** [Bridge pattern](https://en.wikipedia.org/wiki/Bridge_pattern) · [Design Patterns (book)](https://en.wikipedia.org/wiki/Design_Patterns)

## Intent

Decouple an abstraction from its implementation so the two can vary independently.

## Explanation

`Shape` (abstraction) holds a `Renderer` (implementor). You can add new shapes or new renderers without an N×M class explosion. The bridge is the composition link from abstraction to implementor.

## Classic structure (UML)

```mermaid
classDiagram
    class Abstraction
    class RefinedAbstraction
    class Implementor {
        <<interface>>
    }
    class ConcreteImplementorA
    class ConcreteImplementorB
    Abstraction --> Implementor
    Abstraction <|-- RefinedAbstraction
    Implementor <|.. ConcreteImplementorA
    Implementor <|.. ConcreteImplementorB
```

## This demo

`Shape` / `Circle` are abstraction; `Renderer`, `VectorRenderer`, `RasterRenderer` are the implementor hierarchy.

```mermaid
classDiagram
    class Shape
    class Circle
    class Renderer
    class VectorRenderer
    class RasterRenderer
    Shape --> Renderer
    Shape <|-- Circle
    Renderer <|-- VectorRenderer
    Renderer <|-- RasterRenderer
```

## Real-world use cases

- GUI widgets drawn via OpenGL vs Canvas vs SVG backends.
- Remote vs local device drivers behind the same device abstraction.
- Messaging: Notification abstraction over Email / SMS / Push implementors.

## Run

```text
python -m transpiler run examples/design_patterns/structural/bridge.pys
```
