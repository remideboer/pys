# Gang of Four design patterns — PYS teaching demos

Classic patterns from *Design Patterns: Elements of Reusable Object-Oriented
Software* (Gamma, Helm, Johnson, Vlissides, 1994), plus related **general** and
**concurrency** demos, as **pure OO** runnable `.pys` files.

Background: [Wikipedia — Design Patterns](https://en.wikipedia.org/wiki/Design_Patterns).
Concurrency catalog: [Wikipedia — Concurrency pattern](https://en.wikipedia.org/wiki/Concurrency_pattern).

Each pattern also has a companion `[name].md` with intent, explanation, classic
and demo Mermaid UML, and real-world use cases.

## Run

From the repo root (this folder has its own `pys.toml` so runs do not inherit
the monorepo MySQL lock):

```text
python -m transpiler run examples/design_patterns/creational/singleton.pys
python -m transpiler run examples/design_patterns/behavioral/observer.pys
```

Each file is its own demo entrypoint (no single `main` in `pys.toml`). Expected
print lines are marked with `# …` comments.

## Creational

| Pattern | Code | Notes |
|---------|------|-------|
| Abstract Factory | [abstract_factory.pys](creational/abstract_factory.pys) | [abstract_factory.md](creational/abstract_factory.md) |
| Builder | [builder.pys](creational/builder.pys) | [builder.md](creational/builder.md) |
| Factory Method | [factory_method.pys](creational/factory_method.pys) | [factory_method.md](creational/factory_method.md) |
| Prototype | [prototype.pys](creational/prototype.pys) | [prototype.md](creational/prototype.md) |
| Singleton | [singleton.pys](creational/singleton.pys) | [singleton.md](creational/singleton.md) — prefer [DI](general/dependency_injection.md) in apps |

## General

Not from the GoF catalog; common companion patterns used with OO PYS apps.

| Pattern | Code | Notes |
|---------|------|-------|
| Dependency Injection | [dependency_injection.pys](general/dependency_injection.pys) | [dependency_injection.md](general/dependency_injection.md) (constructor injection) |

## Structural

| Pattern | Code | Notes |
|---------|------|-------|
| Adapter | [adapter.pys](structural/adapter.pys) | [adapter.md](structural/adapter.md) |
| Bridge | [bridge.pys](structural/bridge.pys) | [bridge.md](structural/bridge.md) |
| Composite | [composite.pys](structural/composite.pys) | [composite.md](structural/composite.md) |
| Decorator | [decorator.pys](structural/decorator.pys) | [decorator.md](structural/decorator.md) |
| Facade | [facade.pys](structural/facade.pys) | [facade.md](structural/facade.md) |
| Flyweight | [flyweight.pys](structural/flyweight.pys) | [flyweight.md](structural/flyweight.md) |
| Proxy | [proxy.pys](structural/proxy.pys) | [proxy.md](structural/proxy.md) |

## Behavioral

| Pattern | Code | Notes |
|---------|------|-------|
| Chain of Responsibility | [chain_of_responsibility.pys](behavioral/chain_of_responsibility.pys) | [chain_of_responsibility.md](behavioral/chain_of_responsibility.md) |
| Command | [command.pys](behavioral/command.pys) | [command.md](behavioral/command.md) |
| Interpreter | [interpreter.pys](behavioral/interpreter.pys) | [interpreter.md](behavioral/interpreter.md) |
| Iterator | [iterator.pys](behavioral/iterator.pys) | [iterator.md](behavioral/iterator.md) |
| Mediator | [mediator.pys](behavioral/mediator.pys) | [mediator.md](behavioral/mediator.md) |
| Memento | [memento.pys](behavioral/memento.pys) | [memento.md](behavioral/memento.md) |
| Observer | [observer.pys](behavioral/observer.pys) | [observer.md](behavioral/observer.md) |
| State | [state.pys](behavioral/state.pys) | [state.md](behavioral/state.md) |
| Strategy | [strategy.pys](behavioral/strategy.pys) | [strategy.md](behavioral/strategy.md) |
| Template Method | [template_method.pys](behavioral/template_method.pys) | [template_method.md](behavioral/template_method.md) |
| Visitor | [visitor.pys](behavioral/visitor.pys) | [visitor.md](behavioral/visitor.md) |

## Concurrency

Runnable demos use only `tasks` / `task` / `await` / `shared` / `atomic`
([CONCURRENCY.md](../../docs/CONCURRENCY.md)). No `import threading`.

| Pattern | Code | Notes |
|---------|------|-------|
| Active object | [active_object.pys](concurrency/active_object.pys) | [active_object.md](concurrency/active_object.md) |
| Balking | [balking.pys](concurrency/balking.pys) | [balking.md](concurrency/balking.md) |
| Double-checked locking | [double_checked_locking.pys](concurrency/double_checked_locking.pys) | [double_checked_locking.md](concurrency/double_checked_locking.md) (CAS, no mutex) |
| Scheduler | [scheduler.pys](concurrency/scheduler.pys) | [scheduler.md](concurrency/scheduler.md) |

### Out of language today

Wikipedia’s Examples list also names patterns that need locks, wait/notify, TLS,
a reusable barrier, or a demux API. They are **documented here only** — no fake
demos (including no “await N tasks” stand-in for Barrier):

| Pattern | Why skipped |
|---------|-------------|
| Barrier | Needs a reusable multi-party barrier / arrive-and-wait; `await` fan-in is structured join, not this pattern |
| Guarded suspension | Needs wait/notify or a condition variable |
| Monitor object | Needs mutual exclusion on methods |
| Readers–writer lock | Needs an RW lock |
| Thread-local storage | No TLS in PYS |
| Thread pool | Emitter uses a pool; PYS cannot define/size one |
| Reactor | No selector / demux API |
| Nuclear reaction | Niche; needs the same missing primitives |

## Modern notes

- Prefer **program to an interface** and **composition over inheritance** (GoF ch. 1).
- **Singleton** is shown in classic form for literacy; prefer
  [Dependency Injection](general/dependency_injection.md) (constructor injection /
  a composition root) instead of a global instance.
- **Interpreter** is for tiny DSLs; do not invent a language when a function
  or library parser would do.
- Language `loop (x in xs)` already iterates collections; the Iterator demo
  shows the OO roles behind that idea.
