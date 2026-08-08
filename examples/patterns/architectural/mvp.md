# Model–View–Presenter (MVP)

**Category:** Architectural  
**Demo:** [mvp.pys](mvp.pys)  
**Wikipedia:** [Model–view–presenter](https://en.wikipedia.org/wiki/Model%E2%80%93view%E2%80%93presenter)

## Intent

A **Presenter** drives a passive **View** through an interface; the View only
displays what it is told.

## Explanation

`CounterView` is an interface; `ConsoleCounterView` prints. The presenter owns
the flow — easier to swap or fake the view in tests.

## Classic structure (UML)

```mermaid
classDiagram
    class Presenter
    class Model
    class View {
        <<interface>>
    }
    Presenter --> Model
    Presenter --> View
```

## This demo

```mermaid
classDiagram
    class CounterPresenter
    class CounterModel
    class CounterView {
        <<interface>>
    }
    class ConsoleCounterView
    CounterPresenter --> CounterModel
    CounterPresenter --> CounterView
    CounterView <|.. ConsoleCounterView
```

## Real-world use cases

- Android / WinForms apps with passive views.
- UI tests that inject a fake view into the presenter.

## Run

```text
python -m transpiler run examples/patterns/architectural/mvp.pys
```
