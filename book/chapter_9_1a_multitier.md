# 10.1a. Multitier architecture — layers, tiers, and three-tier

When you ask an AI for “a three-tier shop,” you are naming **Multitier**
(also **n-tier**) architecture: separate **presentation**, **application /
business logic**, and **data access** so each can change without rewriting the
others.

[Wikipedia: Multitier architecture](https://en.wikipedia.org/wiki/Multitier_architecture)

## What Multitier / n-tier is

**Multitier** means client–server work is split into **tiers of responsibility**.
The most common form in teaching and industry talk is **three-tier**:

1. Presentation (UI / HTTP edge)
2. Application / business logic
3. Data (persistence)

Your living shop examples under [`examples/rest-api/shop/`](../examples/rest-api/shop/)
(and the Express JS track under
[`examples/by-target/javascript/rest-api/express/`](../examples/by-target/javascript/rest-api/express/))
often use this stack — sometimes combined with ports (hexagonal).

## Layer ≠ tier (the key distinction)

| Term | Means |
|------|--------|
| **Layer** | Logical grouping of code (UI code, app services, data access) |
| **Tier** | Physical deploy node (browser, app server, database host) |

One process can host **three layers on one tier**. Teaching demos do that on
purpose: you learn the *stack of responsibilities* without running three
machines.

<figure class="concept-diagram" role="img" aria-label="Three logical layers stacked inside one physical process tier">
  <div class="diagram-layers">
    <div class="diagram-layer diagram-outside">
      <strong>Presentation layer</strong>
      <span>console UI / HTTP handlers — no SQL</span>
    </div>
    <div class="diagram-layer">
      <strong>Application / business</strong>
      <span>use-cases and domain types</span>
    </div>
    <div class="diagram-layer diagram-layer-core">
      <strong>Data access layer</strong>
      <span>store port + in-memory / DB adapter</span>
    </div>
  </div>
  <figcaption>
    Three <em>layers</em> in one process = still one <em>tier</em>. Production may
    put each layer on its own machine later.
  </figcaption>
</figure>

## Common logical layers

A fuller stack often names four logical bands (top depends downward):

<figure class="concept-diagram" role="img" aria-label="Presentation over application over domain over data access">
  <div class="diagram-layers">
    <div class="diagram-layer diagram-outside">
      <strong>Presentation</strong>
      <span>UI, routes, printers</span>
    </div>
    <div class="diagram-layer">
      <strong>Application / service</strong>
      <span>use-case orchestration</span>
    </div>
    <div class="diagram-layer diagram-layer-core">
      <strong>Business / domain</strong>
      <span>entities and rules you protect</span>
    </div>
    <div class="diagram-layer diagram-layer-edge">
      <strong>Data access</strong>
      <span>repositories, SQL, files</span>
    </div>
  </div>
  <figcaption>
    Outer code may call inward; domain types stay free of UI and SQL details.
  </figcaption>
</figure>

## Classic three-tier (and the web mapping)

On the web you often hear the same three names mapped to deploy nodes:

| Logical (layer) | Typical web tier |
|-----------------|------------------|
| Presentation | Browser / static assets |
| Application | App server (API + use-cases) |
| Data | Database host |

This book does **not** implement browsers or multi-server deploy. The runnable
demo keeps three **logical** layers in one process so the vocabulary stays
honest and runnable.

<figure class="concept-diagram" role="img" aria-label="Three-tier boxes presentation application and data">
  <div class="diagram-stack">
    <div class="diagram-box diagram-outside"><strong>Presentation</strong><span>UI edge</span></div>
    <div class="diagram-arrow" aria-hidden="true">↓</div>
    <div class="diagram-box"><strong>Application</strong><span>logic / use-cases</span></div>
    <div class="diagram-arrow" aria-hidden="true">↓</div>
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>Data</strong>
      <span>persistence</span>
    </div>
  </div>
  <figcaption>
    Classic three-tier stack: presentation calls application; application talks
    to data — not the reverse.
  </figcaption>
</figure>

## Strict vs relaxed layering

**Strict** layering: a layer may call **only the next layer down**
(presentation → application → data). **Relaxed** layering allows skipping
(e.g. presentation reading a read-model store) — useful, but easier to tangle.

<figure class="concept-diagram" role="img" aria-label="Strict dependencies only call the next layer down">
  <div class="diagram-stack">
    <div class="diagram-box diagram-outside"><strong>Presentation</strong><span>may call ↓</span></div>
    <div class="diagram-arrow" aria-hidden="true">↓ only</div>
    <div class="diagram-box"><strong>Application</strong><span>may call ↓</span></div>
    <div class="diagram-arrow" aria-hidden="true">↓ only</div>
    <div class="diagram-box diagram-layer-edge" style="border-style:dashed;border-width:2px;background:#f5ecd8;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>Data access</strong>
      <span>no upward calls</span>
    </div>
  </div>
  <figcaption>
    Strict: only the next layer down. Skip links are relaxed layering — document
    them when you allow them.
  </figcaption>
</figure>

## Multitier vs hexagonal

| | Multitier | Hexagonal |
|--|-----------|-----------|
| Picture | Stacked layers | Ports around a protected core |
| Dependency story | Outer depends on inner down the stack | Inside depends on ports; adapters plug in |
| Good for | Naming UI / app / data bands | Protecting domain from frameworks |

Shops often **combine** both: multitier bands *and* a Repository port at the
data edge ([`hexagonal.pys`](../examples/patterns/architectural/hexagonal.pys)).

<figure class="concept-diagram" role="img" aria-label="Stack of layers versus core with ports and outside adapters">
  <div class="diagram-grid-2">
    <div class="diagram-box">
      <strong>Multitier</strong>
      <span>Presentation → App → Data (stack)</span>
    </div>
    <div class="diagram-box diagram-layer-core" style="border:2px solid var(--accent);background:#e5edff;padding:0.7rem;border-radius:6px;text-align:center">
      <strong>Hexagonal</strong>
      <span>Core · ports · adapters outside</span>
    </div>
  </div>
  <figcaption>
    Different pictures, same goal of honest boundaries. Do not treat the names
    as synonyms when prompting an AI.
  </figcaption>
</figure>

### Prompting an AI

**Say this:** “Use a **three-tier / multitier** layout: presentation calls an
application service; the service uses a data-access port. Keep UI free of SQL.
Remember **layer ≠ tier** — one process is fine for the teaching demo.”

**Not this:** “Put SQL and `print` in the same handler.” · “Three-tier means
three Docker containers” (that is deploy tiers, not the logical lesson).

**Confusion to avoid:** Multitier ≠ Hexagonal · Layer ≠ tier · Layered demo
([`layered.pys`](../examples/patterns/architectural/layered.pys)) is the short
sibling of Multitier.

## Runnable demo

[`examples/patterns/architectural/multitier.pys`](../examples/patterns/architectural/multitier.pys)

```text
python -m transpiler run examples/patterns/architectural/multitier.pys
```

**Output:**

```text
placed:O-1
status:new
```

`OrderConsoleUi` (presentation) → `OrderApplication` (application) →
`OrderStore` / `InMemoryOrderStore` (data access). Domain `Order` stays free of
UI and SQL.

Living shops (same idea at scale): [`examples/rest-api/shop/`](../examples/rest-api/shop/).

### Exercise

> A classmate says “three-tier means we must run three servers.” What do you
> correct? (Answer: they mixed **tier** with **layer**; three logical layers
> can live in one process.)

---

[Previous: App shape](chapter_9_1_app_shape.md) · [Next: Authorization](chapter_9_2_authorization.md)
