# Composite

**Category:** Structural  
**Demo:** [composite.pys](composite.pys)  
**Wikipedia:** [Composite pattern](https://en.wikipedia.org/wiki/Composite_pattern) · [Design Patterns (book)](https://en.wikipedia.org/wiki/Design_Patterns)

## Intent

Compose objects into tree structures to represent part-whole hierarchies. Composite lets clients treat individual objects and compositions of objects uniformly.

## Explanation

`Graphic.draw()` works on a leaf `Dot` and on a `CompoundGraphic` that holds children. Clients recurse the tree with one API. Use when UI scenes, file systems, or menus are naturally hierarchical.

## Classic structure (UML)

```mermaid
classDiagram
    class Component {
        +operation()
    }
    class Leaf
    class Composite
    Component <|-- Leaf
    Component <|-- Composite
    Composite o-- Component
```

## This demo

`Graphic` is Component; `Dot` is Leaf; `CompoundGraphic` is Composite and owns child `Graphic`s.

```mermaid
classDiagram
    class Graphic {
        <<interface>>
    }
    class Dot
    class CompoundGraphic
    Graphic <|.. Dot
    Graphic <|.. CompoundGraphic
    CompoundGraphic o-- Graphic
```

## Real-world use cases

- Scene graphs / DOM-like UI trees (panel containing buttons and nested panels).
- File-system browsers (files and folders share a node interface).
- Menu bars with nested submenus treated as menu items.

## Run

```text
python -m transpiler run examples/patterns/design/structural/composite.pys
```
