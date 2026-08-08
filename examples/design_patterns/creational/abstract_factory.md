# Abstract Factory

**Category:** Creational  
**Demo:** [abstract_factory.pys](abstract_factory.pys)  
**Wikipedia:** [Abstract Factory pattern](https://en.wikipedia.org/wiki/Abstract_factory_pattern) · [Design Patterns (book)](https://en.wikipedia.org/wiki/Design_Patterns)

## Intent

Provide an interface for creating families of related or dependent objects without specifying their concrete classes.

## Explanation

A client asks a **factory** for products (`Button`, `Checkbox`) and never names `WinButton` or `MacButton`. Switching the factory swaps the whole family so widgets stay consistent (all Win or all Mac). Use when you need multiple product *families* that must vary together.

## Classic structure (UML)

```mermaid
classDiagram
    class AbstractFactory {
        <<interface>>
        +createProductA()
        +createProductB()
    }
    class ConcreteFactory1
    class ConcreteFactory2
    class AbstractProductA {
        <<interface>>
    }
    class AbstractProductB {
        <<interface>>
    }
    class ProductA1
    class ProductB1
    class ProductA2
    class ProductB2
    class Client
    AbstractFactory <|.. ConcreteFactory1
    AbstractFactory <|.. ConcreteFactory2
    AbstractProductA <|.. ProductA1
    AbstractProductA <|.. ProductA2
    AbstractProductB <|.. ProductB1
    AbstractProductB <|.. ProductB2
    ConcreteFactory1 --> ProductA1
    ConcreteFactory1 --> ProductB1
    ConcreteFactory2 --> ProductA2
    ConcreteFactory2 --> ProductB2
    Client --> AbstractFactory
    Client --> AbstractProductA
    Client --> AbstractProductB
```

## This demo

`GUIFactory` is the abstract factory; `WinFactory` / `MacFactory` are concrete factories. `Button` / `Checkbox` are abstract products; `WinButton`, `MacButton`, … are concrete products. `Application` is the client that only talks to the interfaces.

```mermaid
classDiagram
    class GUIFactory {
        <<interface>>
        +createButton()
        +createCheckbox()
    }
    class WinFactory
    class MacFactory
    class Button {
        <<interface>>
    }
    class Checkbox {
        <<interface>>
    }
    class WinButton
    class MacButton
    class WinCheckbox
    class MacCheckbox
    class Application
    GUIFactory <|.. WinFactory
    GUIFactory <|.. MacFactory
    Button <|.. WinButton
    Button <|.. MacButton
    Checkbox <|.. WinCheckbox
    Checkbox <|.. MacCheckbox
    WinFactory --> WinButton
    WinFactory --> WinCheckbox
    MacFactory --> MacButton
    MacFactory --> MacCheckbox
    Application --> GUIFactory
    Application --> Button
    Application --> Checkbox
```

## Real-world use cases

- Cross-platform UI kits that must create matching controls (window, button, scrollbar) for Win / Mac / Linux.
- Database driver families (connection + statement + result-set) selected by vendor.
- Theme packs that produce consistent icons, colors, and dialogs as one family.

## Run

```text
python -m transpiler run examples/design_patterns/creational/abstract_factory.pys
```
