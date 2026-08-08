# Layered architecture

**Category:** Architectural  
**Demo:** [layered.pys](layered.pys)  
**Wikipedia:** [Multitier architecture](https://en.wikipedia.org/wiki/Multitier_architecture)  
**Fuller teaching:** [multitier.pys](multitier.pys) · book §10.1a

## Intent

Organize code so outer layers (UI) depend on inner ones (application / domain),
not the reverse. This file is the **short** sibling; Multitier names the classic
three-tier / n-tier vocabulary (and **layer ≠ tier**).

## Explanation

`CheckoutUi` → `CheckoutApp` → `PricingService` / `Money`. Full shops under
[`examples/database/`](../../database/) and [`examples/rest-api/shop/`](../../rest-api/shop/).

## Prompting an AI

**Say this:** “Keep presentation above application above domain — no upward
dependencies.” Prefer naming **three-tier / Multitier** when you want the
industry term ([multitier.md](multitier.md)).

**Not this:** “UI class opens the database.”

**Confusion to avoid:** Layered/Multitier ≠ Hexagonal (see [hexagonal.md](hexagonal.md)).

## Run

```text
python -m transpiler run examples/patterns/architectural/layered.pys
```
