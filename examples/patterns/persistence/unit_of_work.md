# Unit of Work

**Category:** Persistence  
**Demo:** [unit_of_work.pys](unit_of_work.pys)  
**Wikipedia:** [Unit of work](https://en.wikipedia.org/wiki/Unit_of_work)  
**Related:** [repository](repository.md)

## Intent

Track all changes made during a **business transaction** and persist them
together on `commit`, or discard them on `rollback`.

## Explanation

`UnitOfWork` holds pending `Product` rows. `commit()` writes them through the
store; `rollback()` drops the pending list. This teaching form is in-memory —
production UoW often wraps a DB transaction.

## Prompting an AI

**Say this:** “Introduce a Unit of Work that registers new products and only
writes them on `commit`. Show a rollback path that leaves the store empty.”

**Not this:** “Save to the database on every field assignment.”

**Confusion to avoid:** Unit of Work ≠ Repository (UoW batches; repository
persists one aggregate API).

## Run

```text
python -m transpiler run examples/patterns/persistence/unit_of_work.pys
```
