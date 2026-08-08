# Multitier architecture (n-tier / three-tier)

**Category:** Architectural  
**Demo:** [multitier.pys](multitier.pys)  
**Wikipedia:** [Multitier architecture](https://en.wikipedia.org/wiki/Multitier_architecture)  
**Related:** [layered.pys](layered.pys) (shorter stack) · [hexagonal.pys](hexagonal.pys) · book §10.1a

## Intent

Separate **presentation**, **application/business logic**, and **data access**
so each can change without rewriting the others. Often called **n-tier** or
**three-tier**.

## Layer vs tier

| Term | Means |
|------|--------|
| **Layer** | Logical grouping of code (UI, app, data access) |
| **Tier** | Physical deploy node (browser, app server, DB host) |

This demo runs **three layers in one process** (one tier). Production may put
each layer on its own tier.

## This demo

`OrderConsoleUi` (presentation) → `OrderApplication` (application) →
`OrderStore` / `InMemoryOrderStore` (data access). Domain `Order` stays free of
UI and SQL.

## Prompting an AI

**Say this:** “Use a three-tier / multitier layout: presentation calls an
application service; the service uses a data-access port. Keep UI free of SQL.”

**Not this:** “Put SQL and print statements in the same handler class.”

**Confusion to avoid:** Multitier ≠ Hexagonal (stack of layers vs ports around
a core — shops often combine both). Layer ≠ tier.

## Run

```text
python -m transpiler run examples/patterns/architectural/multitier.pys
```
