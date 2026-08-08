# Model–View–ViewModel (MVVM)

**Category:** Architectural  
**Demo:** [mvvm.pys](mvvm.pys)  
**Wikipedia:** [Model–view–viewmodel](https://en.wikipedia.org/wiki/Model%E2%80%93view%E2%80%93viewmodel)

## Intent

The **View** binds to a **ViewModel** that exposes display state and commands;
the ViewModel talks to the **Model**.

## Explanation

`CounterView` only calls ViewModel commands and reads `displayValue` — it never
touches `CounterModel`. Teaching form without a framework binder.

## Classic structure (UML)

```mermaid
classDiagram
    class View
    class ViewModel
    class Model
    View --> ViewModel
    ViewModel --> Model
```

## This demo

```mermaid
classDiagram
    class CounterView
    class CounterViewModel
    class CounterModel
    CounterView --> CounterViewModel
    CounterViewModel --> CounterModel
```

## Real-world use cases

- WPF / SwiftUI / Android data-binding UIs.
- SPAs where a view-model holds screen state separate from domain entities.

## Run

```text
python -m transpiler run examples/patterns/architectural/mvvm.pys
```
