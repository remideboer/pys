# PYS patterns — teaching demos and stubs

Runnable **pure OO** `.pys` demos plus markdown notes. Layout:

| Folder | Contents |
|--------|----------|
| [`design/`](design/) | Gang of Four (creational / structural / behavioral) |
| [`concurrency/`](concurrency/) | Concurrency patterns expressible in PYS today |
| [`general/`](general/) | Cross-cutting OO (e.g. Dependency Injection) |
| [`authentication/`](authentication/) | Common authentication patterns |
| [`architectural/`](architectural/) | App structure — mostly **stubs** |
| [`messaging/`](messaging/) | Event-driven / pub-sub at scale — **stubs** |
| [`reactive/`](reactive/) | Reactive streams — **stub** |

Background: [Wikipedia — Design Patterns](https://en.wikipedia.org/wiki/Design_Patterns) ·
[Concurrency pattern](https://en.wikipedia.org/wiki/Concurrency_pattern) ·
[Dependency injection](https://en.wikipedia.org/wiki/Dependency_injection).

Companion `[name].md` files include intent, UML, use cases, and a run line.
Stubs are markdown only (**Status: stub — implement later**) — no fake `.pys`.

## Run

From the repo root (this folder has its own `pys.toml`):

```text
python -m transpiler run examples/patterns/design/creational/singleton.pys
python -m transpiler run examples/patterns/general/dependency_injection.pys
python -m transpiler run examples/patterns/authentication/session_based.pys
```

## Design (GoF)

### Creational

| Pattern | Code | Notes |
|---------|------|-------|
| Abstract Factory | [abstract_factory.pys](design/creational/abstract_factory.pys) | [md](design/creational/abstract_factory.md) |
| Builder | [builder.pys](design/creational/builder.pys) | [md](design/creational/builder.md) |
| Factory Method | [factory_method.pys](design/creational/factory_method.pys) | [md](design/creational/factory_method.md) |
| Prototype | [prototype.pys](design/creational/prototype.pys) | [md](design/creational/prototype.md) |
| Singleton | [singleton.pys](design/creational/singleton.pys) | [md](design/creational/singleton.md) — prefer [DI](general/dependency_injection.md) |

### Structural

| Pattern | Code | Notes |
|---------|------|-------|
| Adapter | [adapter.pys](design/structural/adapter.pys) | [md](design/structural/adapter.md) |
| Bridge | [bridge.pys](design/structural/bridge.pys) | [md](design/structural/bridge.md) |
| Composite | [composite.pys](design/structural/composite.pys) | [md](design/structural/composite.md) |
| Decorator | [decorator.pys](design/structural/decorator.pys) | [md](design/structural/decorator.md) |
| Facade | [facade.pys](design/structural/facade.pys) | [md](design/structural/facade.md) |
| Flyweight | [flyweight.pys](design/structural/flyweight.pys) | [md](design/structural/flyweight.md) |
| Proxy | [proxy.pys](design/structural/proxy.pys) | [md](design/structural/proxy.md) |

### Behavioral

| Pattern | Code | Notes |
|---------|------|-------|
| Chain of Responsibility | [chain_of_responsibility.pys](design/behavioral/chain_of_responsibility.pys) | [md](design/behavioral/chain_of_responsibility.md) |
| Command | [command.pys](design/behavioral/command.pys) | [md](design/behavioral/command.md) |
| Interpreter | [interpreter.pys](design/behavioral/interpreter.pys) | [md](design/behavioral/interpreter.md) |
| Iterator | [iterator.pys](design/behavioral/iterator.pys) | [md](design/behavioral/iterator.md) |
| Mediator | [mediator.pys](design/behavioral/mediator.pys) | [md](design/behavioral/mediator.md) |
| Memento | [memento.pys](design/behavioral/memento.pys) | [md](design/behavioral/memento.md) |
| Observer | [observer.pys](design/behavioral/observer.pys) | [md](design/behavioral/observer.md) |
| State | [state.pys](design/behavioral/state.pys) | [md](design/behavioral/state.md) |
| Strategy | [strategy.pys](design/behavioral/strategy.pys) | [md](design/behavioral/strategy.md) |
| Template Method | [template_method.pys](design/behavioral/template_method.pys) | [md](design/behavioral/template_method.md) |
| Visitor | [visitor.pys](design/behavioral/visitor.pys) | [md](design/behavioral/visitor.md) |

## Concurrency

Runnable demos use only `tasks` / `task` / `await` / `shared` / `atomic`
([CONCURRENCY.md](../../docs/CONCURRENCY.md)). No `import threading`.

| Pattern | Code | Notes |
|---------|------|-------|
| Active object | [active_object.pys](concurrency/active_object.pys) | [md](concurrency/active_object.md) |
| Balking | [balking.pys](concurrency/balking.pys) | [md](concurrency/balking.md) |
| Double-checked locking | [double_checked_locking.pys](concurrency/double_checked_locking.pys) | [md](concurrency/double_checked_locking.md) |
| Scheduler | [scheduler.pys](concurrency/scheduler.pys) | [md](concurrency/scheduler.md) |

### Out of language today

| Pattern | Why skipped |
|---------|-------------|
| Barrier | Needs reusable arrive-and-wait; `await` fan-in is not this pattern |
| Guarded suspension | Needs wait/notify |
| Monitor object | Needs mutual exclusion on methods |
| Readers–writer lock | Needs RW lock |
| Thread-local storage | No TLS |
| Thread pool | Emitter pools threads; PYS cannot define/size one |
| Reactor | No selector / demux API |
| Nuclear reaction | Niche; same missing primitives |

## General

| Pattern | Code | Notes |
|---------|------|-------|
| Dependency Injection | [dependency_injection.pys](general/dependency_injection.pys) | [md](general/dependency_injection.md) (constructor injection) |

## Authentication

Pure OO teaching demos (no network). Full HTTP JWT shop:
[`examples/rest-api/shop/jwt/`](../rest-api/shop/jwt/).

| Pattern | Code | Notes |
|---------|------|-------|
| Session-based | [session_based.pys](authentication/session_based.pys) | [md](authentication/session_based.md) |
| Token-based | [token_based.pys](authentication/token_based.pys) | [md](authentication/token_based.md) |
| API key | [api_key.pys](authentication/api_key.pys) | [md](authentication/api_key.md) |
| HTTP Basic | [basic_auth.pys](authentication/basic_auth.pys) | [md](authentication/basic_auth.md) |

### Stubs

| Pattern | Notes |
|---------|-------|
| [OAuth 2.0](authentication/oauth2.md) | Needs external IdP / redirects |
| [mTLS](authentication/mtls.md) | Needs TLS client certificates |

## Architectural (stubs)

| Pattern | Notes |
|---------|-------|
| [MVC](architectural/mvc.md) | Model–View–Controller |
| [MVVM](architectural/mvvm.md) | Model–View–ViewModel |
| [MVP](architectural/mvp.md) | Model–View–Presenter |
| [Hexagonal](architectural/hexagonal.md) | Ports and adapters |
| [Layered](architectural/layered.md) | Living refs: shop / database examples |

## Messaging (stubs)

| Pattern | Notes |
|---------|-------|
| [Event-driven](messaging/event_driven.md) | Architecture-scale events |
| [Publish–subscribe](messaging/publish_subscribe.md) | Brokers; see also design Observer |
| [CQRS](messaging/cqrs.md) | Command Query Responsibility Segregation |

## Reactive (stubs)

| Pattern | Notes |
|---------|-------|
| [Reactive](reactive/reactive.md) | Observable streams; not the same as `tasks`/`await` |

## Modern notes

- Prefer **program to an interface** and **composition over inheritance**.
- Prefer [Dependency Injection](general/dependency_injection.md) over Singleton globals.
- **Interpreter** is for tiny DSLs only.
