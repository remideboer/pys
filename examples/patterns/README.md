# PYS patterns — teaching demos and stubs

Runnable **pure OO** `.pys` demos plus markdown notes. Layout:

| Folder | Contents |
|--------|----------|
| [`design/`](design/) | Gang of Four (creational / structural / behavioral) |
| [`concurrency/`](concurrency/) | Concurrency patterns expressible in PYS today |
| [`general/`](general/) | Cross-cutting OO (e.g. Dependency Injection) |
| [`authentication/`](authentication/) | Common authentication patterns |
| [`architectural/`](architectural/) | MVC / MVP / MVVM / hexagonal / layered |
| [`persistence/`](persistence/) | Repository, Unit of Work, cache, concurrency |
| [`application/`](application/) | Service layer, DTO/ACL, pipeline, specification |
| [`authorization/`](authorization/) | RBAC / ACL / ABAC |
| [`resilience/`](resilience/) | Retry, circuit breaker, idempotency, … |
| [`messaging/`](messaging/) | Event-driven / pub-sub / CQRS / outbox / saga |
| [`testing/`](testing/) | Test doubles, Object Mother / Builder |
| [`reactive/`](reactive/) | Teaching push streams |

Companion `[name].md` files include intent, use cases, a run line, and
**Prompting an AI** (say this / not this / confusion to avoid).
OAuth2 / mTLS remain **stubs** (need IdP / TLS — not faked in-process).
Book: Session 10 in [`book/`](../../book/SUMMARY.md).

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
| Dependency Injection | [dependency_injection.pys](general/dependency_injection.pys) | [md](general/dependency_injection.md) |
| Service Locator | [service_locator_antipattern.pys](general/service_locator_antipattern.pys) | [md](general/service_locator_antipattern.md) — **anti-pattern**; prefer DI |

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

## Architectural

| Pattern | Code | Notes |
|---------|------|-------|
| MVC | [mvc.pys](architectural/mvc.pys) | [md](architectural/mvc.md) |
| MVP | [mvp.pys](architectural/mvp.pys) | [md](architectural/mvp.md) |
| MVVM | [mvvm.pys](architectural/mvvm.pys) | [md](architectural/mvvm.md) |
| Hexagonal | [hexagonal.pys](architectural/hexagonal.pys) | [md](architectural/hexagonal.md) |
| Layered | [layered.pys](architectural/layered.pys) | [md](architectural/layered.md) — short stack |
| Multitier | [multitier.pys](architectural/multitier.pys) | [md](architectural/multitier.md) — three-tier / layer≠tier |

## Persistence

| Pattern | Code | Notes |
|---------|------|-------|
| Repository | [repository.pys](persistence/repository.pys) | [md](persistence/repository.md) |
| Unit of Work | [unit_of_work.pys](persistence/unit_of_work.pys) | [md](persistence/unit_of_work.md) |
| Cache-aside | [cache_aside.pys](persistence/cache_aside.pys) | [md](persistence/cache_aside.md) |
| Optimistic concurrency | [optimistic_concurrency.pys](persistence/optimistic_concurrency.pys) | [md](persistence/optimistic_concurrency.md) |
| Data Mapper vs Active Record | [data_mapper_vs_active_record.pys](persistence/data_mapper_vs_active_record.pys) | [md](persistence/data_mapper_vs_active_record.md) |
| Identity Map | [identity_map.pys](persistence/identity_map.pys) | [md](persistence/identity_map.md) |

## Application

| Pattern | Code | Notes |
|---------|------|-------|
| Service layer | [service_layer.pys](application/service_layer.pys) | [md](application/service_layer.md) |
| DTO / ACL | [dto_acl.pys](application/dto_acl.pys) | [md](application/dto_acl.md) |
| Pipeline / middleware | [pipeline_middleware.pys](application/pipeline_middleware.pys) | [md](application/pipeline_middleware.md) |
| Specification | [specification.pys](application/specification.pys) | [md](application/specification.md) |
| Null Object | [null_object.pys](application/null_object.pys) | [md](application/null_object.md) |
| Plugin | [plugin.pys](application/plugin.pys) | [md](application/plugin.md) |

## Authorization

| Pattern | Code | Notes |
|---------|------|-------|
| RBAC | [rbac.pys](authorization/rbac.pys) | [md](authorization/rbac.md) |
| ACL | [acl.pys](authorization/acl.pys) | [md](authorization/acl.md) |
| ABAC | [abac.pys](authorization/abac.pys) | [md](authorization/abac.md) |

## Resilience

| Pattern | Code | Notes |
|---------|------|-------|
| Retry | [retry.pys](resilience/retry.pys) | [md](resilience/retry.md) |
| Timeout | [timeout.pys](resilience/timeout.pys) | [md](resilience/timeout.md) |
| Circuit breaker | [circuit_breaker.pys](resilience/circuit_breaker.pys) | [md](resilience/circuit_breaker.md) |
| Bulkhead | [bulkhead.pys](resilience/bulkhead.pys) | [md](resilience/bulkhead.md) |
| Fallback | [fallback.pys](resilience/fallback.pys) | [md](resilience/fallback.md) |
| Rate limiting | [rate_limiting.pys](resilience/rate_limiting.pys) | [md](resilience/rate_limiting.md) |
| Idempotency | [idempotency.pys](resilience/idempotency.pys) | [md](resilience/idempotency.md) |

## Messaging

| Pattern | Code | Notes |
|---------|------|-------|
| Event-driven | [event_driven.pys](messaging/event_driven.pys) | [md](messaging/event_driven.md) |
| Publish–subscribe | [publish_subscribe.pys](messaging/publish_subscribe.pys) | [md](messaging/publish_subscribe.md) |
| CQRS | [cqrs.pys](messaging/cqrs.pys) | [md](messaging/cqrs.md) |
| Event sourcing | [event_sourcing.pys](messaging/event_sourcing.pys) | [md](messaging/event_sourcing.md) |
| Outbox | [outbox.pys](messaging/outbox.pys) | [md](messaging/outbox.md) |
| Saga | [saga.pys](messaging/saga.pys) | [md](messaging/saga.md) |
| Request–reply | [request_reply.pys](messaging/request_reply.pys) | [md](messaging/request_reply.md) |

## Testing

| Pattern | Code | Notes |
|---------|------|-------|
| Test doubles | [test_doubles.pys](testing/test_doubles.pys) | [md](testing/test_doubles.md) |
| Object Mother | [object_mother.pys](testing/object_mother.pys) | [md](testing/object_mother.md) |
| Test Data Builder | [test_data_builder.pys](testing/test_data_builder.pys) | [md](testing/test_data_builder.md) |

## Reactive

| Pattern | Code | Notes |
|---------|------|-------|
| Reactive (teaching) | [reactive.pys](reactive/reactive.pys) | [md](reactive/reactive.md) — push streams, not ReactiveX |

## Modern notes

- Prefer **program to an interface** and **composition over inheritance**.
- Prefer [Dependency Injection](general/dependency_injection.md) over Singleton globals.
- **Interpreter** is for tiny DSLs only.
