# DTO and Anti-Corruption Layer

**Category:** Application  
**Demo:** [dto_acl.pys](dto_acl.pys)  
**Wikipedia:** [Data transfer object](https://en.wikipedia.org/wiki/Data_transfer_object) · [Anti-corruption layer](https://en.wikipedia.org/wiki/Anti-corruption_layer)

## Intent

**ACL** translates foreign / legacy shapes into your domain at the boundary.
**DTO** is a flat edge-facing shape for APIs or UI — not your domain model.

## Explanation

Legacy keys (`product_code`, `descr`) never appear inside `CatalogItem`.
`LegacyCatalogAcl.toDomain` protects the model; `toDto` builds a transport view.

## Prompting an AI

**Say this:** “Add an Anti-Corruption Layer that maps legacy field names into a
domain `CatalogItem`, and a DTO for the API response. Do not use the legacy
dict inside domain services.”

**Not this:** “Pass the JSON dict through the whole app.”

**Confusion to avoid:** DTO ≠ entity (DTO is for transport; entity has identity
and domain meaning).

## Run

```text
python -m transpiler run examples/patterns/application/dto_acl.pys
```
