# Layered architecture

**Category:** Architectural  
**Status: stub — implement later** (as a standalone pattern demo)

**Wikipedia:** [Multitier architecture](https://en.wikipedia.org/wiki/Multitier_architecture)

## Intent

Organize code in layers (presentation → application → domain → infrastructure)
with dependencies pointing inward/downward.

## Living references

- [`examples/database/`](../../database/) — menus / GUI → repositories → mappers → DB  
- [`examples/rest-api/shop/`](../../rest-api/shop/) — HTTP → APIs → repositories  

A short single-file pattern sketch may be added later; prefer those folders today.
