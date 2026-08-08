# Gang of Four design patterns — PYS teaching demos

Classic patterns from *Design Patterns: Elements of Reusable Object-Oriented
Software* (Gamma, Helm, Johnson, Vlissides, 1994), implemented as **pure OO**
runnable `.pys` files. Folder layout follows the three GoF categories.

Background: [Wikipedia — Design Patterns](https://en.wikipedia.org/wiki/Design_Patterns).

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

| Pattern | File |
|---------|------|
| Abstract Factory | [creational/abstract_factory.pys](creational/abstract_factory.pys) |
| Builder | [creational/builder.pys](creational/builder.pys) |
| Factory Method | [creational/factory_method.pys](creational/factory_method.pys) |
| Prototype | [creational/prototype.pys](creational/prototype.pys) |
| Singleton | [creational/singleton.pys](creational/singleton.pys) |

## Structural

| Pattern | File |
|---------|------|
| Adapter | [structural/adapter.pys](structural/adapter.pys) |
| Bridge | [structural/bridge.pys](structural/bridge.pys) |
| Composite | [structural/composite.pys](structural/composite.pys) |
| Decorator | [structural/decorator.pys](structural/decorator.pys) |
| Facade | [structural/facade.pys](structural/facade.pys) |
| Flyweight | [structural/flyweight.pys](structural/flyweight.pys) |
| Proxy | [structural/proxy.pys](structural/proxy.pys) |

## Behavioral

| Pattern | File |
|---------|------|
| Chain of Responsibility | [behavioral/chain_of_responsibility.pys](behavioral/chain_of_responsibility.pys) |
| Command | [behavioral/command.pys](behavioral/command.pys) |
| Interpreter | [behavioral/interpreter.pys](behavioral/interpreter.pys) |
| Iterator | [behavioral/iterator.pys](behavioral/iterator.pys) |
| Mediator | [behavioral/mediator.pys](behavioral/mediator.pys) |
| Memento | [behavioral/memento.pys](behavioral/memento.pys) |
| Observer | [behavioral/observer.pys](behavioral/observer.pys) |
| State | [behavioral/state.pys](behavioral/state.pys) |
| Strategy | [behavioral/strategy.pys](behavioral/strategy.pys) |
| Template Method | [behavioral/template_method.pys](behavioral/template_method.pys) |
| Visitor | [behavioral/visitor.pys](behavioral/visitor.pys) |

## Modern notes

- Prefer **program to an interface** and **composition over inheritance** (GoF ch. 1).
- **Singleton** is shown in classic form for literacy; prefer constructor injection /
  a composition root in application code instead of a global instance.
- **Interpreter** is for tiny DSLs; do not invent a language when a function
  or library parser would do.
- Language `loop (x in xs)` already iterates collections; the Iterator demo
  shows the OO roles behind that idea.
