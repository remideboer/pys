# State

**Category:** Behavioral  
**Demo:** [state.pys](state.pys)  
**Wikipedia:** [State pattern](https://en.wikipedia.org/wiki/State_pattern) · [Design Patterns (book)](https://en.wikipedia.org/wiki/Design_Patterns)

## Intent

Allow an object to alter its behavior when its internal state changes. The object will appear to change its class.

## Explanation

`Player` delegates `play` / `stop` to the current `PlayerState`. `StoppedState` and `PlayingState` encapsulate transitions. Avoids giant conditionals on a status enum inside the player.

## Classic structure (UML)

```mermaid
classDiagram
    class Context
    class State {
        <<interface>>
    }
    class ConcreteStateA
    class ConcreteStateB
    Context --> State
    State <|.. ConcreteStateA
    State <|.. ConcreteStateB
```

## This demo

`Player` is Context; `PlayerState`, `StoppedState`, `PlayingState` are the state hierarchy.

```mermaid
classDiagram
    class Player
    class PlayerState
    class StoppedState
    class PlayingState
    Player --> PlayerState
    PlayerState <|-- StoppedState
    PlayerState <|-- PlayingState
```

## Real-world use cases

- Media players, TCP connection state machines, order lifecycles.
- Vending machines (idle → selecting → dispensing).
- Workflow engines where each status has different allowed actions.

## Run

```text
python -m transpiler run examples/design_patterns/behavioral/state.pys
```
