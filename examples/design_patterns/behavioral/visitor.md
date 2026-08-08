# Visitor

**Category:** Behavioral  
**Demo:** [visitor.pys](visitor.pys)  
**Wikipedia:** [Visitor pattern](https://en.wikipedia.org/wiki/Visitor_pattern) · [Design Patterns (book)](https://en.wikipedia.org/wiki/Design_Patterns)

## Intent

Represent an operation to be performed on the elements of an object structure. Visitor lets you define a new operation without changing the classes of the elements on which it operates.

## Explanation

Shapes implement `accept(visitor)`; `DescribeVisitor` implements `visitDot` / `visitCircle`. New operations become new visitors; element classes stay stable. Adding a new element type requires updating all visitors (the classic trade-off).

## Classic structure (UML)

```mermaid
classDiagram
    class Visitor {
        <<interface>>
        +visitConcreteA()
        +visitConcreteB()
    }
    class ConcreteVisitor
    class Element {
        <<interface>>
        +accept(v)
    }
    class ConcreteElementA
    class ConcreteElementB
    Visitor <|.. ConcreteVisitor
    Element <|.. ConcreteElementA
    Element <|.. ConcreteElementB
    ConcreteElementA --> Visitor : accept
    ConcreteElementB --> Visitor : accept
```

## This demo

`ShapeVisitor` / `DescribeVisitor` are visitors; `Shape`, `Dot`, `Circle` are elements.

```mermaid
classDiagram
    class ShapeVisitor {
        <<interface>>
    }
    class DescribeVisitor
    class Shape {
        <<interface>>
    }
    class Dot
    class Circle
    ShapeVisitor <|.. DescribeVisitor
    Shape <|.. Dot
    Shape <|.. Circle
    Dot ..> ShapeVisitor : accept
    Circle ..> ShapeVisitor : accept
```

## Real-world use cases

- Compilers: AST nodes accept type-check / emit / pretty-print visitors.
- Document object models exporting to PDF vs HTML without changing nodes.
- Insurance product graphs where new reports are new visitors.

## Run

```text
python -m transpiler run examples/design_patterns/behavioral/visitor.pys
```
