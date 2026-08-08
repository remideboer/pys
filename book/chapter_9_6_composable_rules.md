# 10.6. Composable rules — pipeline, specification, null object, plugin

## Pipeline / middleware

Wrap a handler in ordered layers (auth, logging). Cousin of Chain of
Responsibility.

<figure class="concept-diagram" role="img" aria-label="Request flows through logging and auth middleware to app handler">
  <div class="diagram-flow" style="min-width:34rem">
    <div class="diagram-box"><strong>request</strong><span>GET /x</span></div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box"><strong>Logging</strong><span>middleware</span></div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box diagram-layer-edge" style="border-style:dashed;border-width:2px;background:#f5ecd8;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>Auth</strong>
      <span>allow or deny</span>
    </div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>Handler</strong>
      <span>ok:…</span>
    </div>
  </div>
  <figcaption>
    Cross-cutting steps wrap the core handler instead of living inside it.
  </figcaption>
</figure>

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

<figure class="concept-diagram" role="img" aria-label="MinAge and Active specs combined with AndSpec">
  <div class="diagram-flow" style="min-width:30rem">
    <div class="diagram-box"><strong>MinAge(18)</strong><span>spec</span></div>
    <div class="diagram-arrow" aria-hidden="true">∧</div>
    <div class="diagram-box"><strong>Active</strong><span>spec</span></div>
    <div class="diagram-arrow" aria-hidden="true">→</div>
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>AndSpec</strong>
      <span>one composable rule</span>
    </div>
  </div>
  <figcaption>
    Small rules combine; avoid one giant if-else of unrelated checks.
  </figcaption>
</figure>

Demo: [`specification.pys`](../examples/patterns/application/specification.pys)

**Output:**

```text
True
False
False
```

## Null Object

A do-nothing `Notifier` so callers never branch on null.

<figure class="concept-diagram" role="img" aria-label="Checkout always has a Notifier; NullNotifier does nothing">
  <div class="diagram-grid-2">
    <div class="diagram-box"><strong>ConsoleNotifier</strong><span>prints notify:…</span></div>
    <div class="diagram-box diagram-outside"><strong>NullNotifier</strong><span>empty body · still a Notifier</span></div>
  </div>
  <figcaption>
    Same socket always plugged — sometimes with a silent machine.
  </figcaption>
</figure>

Demo: [`null_object.pys`](../examples/patterns/application/null_object.pys)

**Output:**

```text
notify:done:O-1
checkout:O-1
checkout:O-2
```

## Plugin

Host registers implementations of an interface and runs them.

<figure class="concept-diagram" role="img" aria-label="ReportHost holds registered Sales and Inventory plugins">
  <div class="diagram-stack">
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>ReportHost</strong>
      <span>register · runAll</span>
    </div>
    <div class="diagram-grid-2">
      <div class="diagram-box"><strong>SalesPlugin</strong><span>ReportPlugin</span></div>
      <div class="diagram-box"><strong>InventoryPlugin</strong><span>ReportPlugin</span></div>
    </div>
  </div>
  <figcaption>
    Extensions plug into a host list instead of a hard-coded switch.
  </figcaption>
</figure>

Demo: [`plugin.pys`](../examples/patterns/application/plugin.pys)

**Output:**

```text
sales=sales:42
inventory=inventory:7
```

## Anti-pattern: Service Locator

Hidden global lookup. Prefer [Dependency Injection](../examples/patterns/general/dependency_injection.pys).

<figure class="concept-diagram" role="img" aria-label="Hidden registry lookup versus constructor injection">
  <div class="diagram-grid-2">
    <div class="diagram-box" style="border:2px solid #8a6d3b;background:#f5ecd8;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>Service Locator</strong>
      <span>hidden SERVICES.getLogger()</span>
    </div>
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>DI</strong>
      <span>constructor(Logger)</span>
    </div>
  </div>
  <figcaption>
    Prefer the right column — collaborators arrive from outside.
  </figcaption>
</figure>

Demo: [`service_locator_antipattern.pys`](../examples/patterns/general/service_locator_antipattern.pys)

### Prompt dialogue

> **You:** Add logging and auth middleware around the HTTP handler. Prefer
> constructor DI; do not add a service locator.
>
> **Not:** “Get dependencies from a global Services.get().”

---

[Previous: Test doubles](chapter_9_5_test_doubles.md) · [Next: Data paths](chapter_9_7_data_paths.md)
