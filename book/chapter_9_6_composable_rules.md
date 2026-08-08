# 10.6. Composable rules — pipeline, specification, null object, plugin

## Pipeline / middleware

Wrap a handler in ordered layers (auth, logging). Cousin of Chain of
Responsibility.

Demo: [`pipeline_middleware.pys`](../examples/patterns/application/pipeline_middleware.pys)

**Output:**

```text
log:GET /x
ok:GET /x
log:GET /x
deny
```

## Specification

Composable predicates (`and` / `or` / `not`) over a candidate.

Demo: [`specification.pys`](../examples/patterns/application/specification.pys)

**Output:**

```text
True
False
False
```

## Null Object

A do-nothing `Notifier` so callers never branch on null.

Demo: [`null_object.pys`](../examples/patterns/application/null_object.pys)

**Output:**

```text
notify:done:O-1
checkout:O-1
checkout:O-2
```

## Plugin

Host registers implementations of an interface and runs them.

Demo: [`plugin.pys`](../examples/patterns/application/plugin.pys)

**Output:**

```text
sales=sales:42
inventory=inventory:7
```

## Anti-pattern: Service Locator

Hidden global lookup. Prefer [Dependency Injection](../examples/patterns/general/dependency_injection.pys).

Demo: [`service_locator_antipattern.pys`](../examples/patterns/general/service_locator_antipattern.pys)

### Prompt dialogue

> **You:** Add logging and auth middleware around the HTTP handler. Prefer
> constructor DI; do not add a service locator.
>
> **Not:** “Get dependencies from a global Services.get().”

---

[Previous: Test doubles](chapter_9_5_test_doubles.md) · [Next: Data paths](chapter_9_7_data_paths.md)
