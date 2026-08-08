# Data Mapper vs Active Record

**Category:** Persistence  
**Demo:** [data_mapper_vs_active_record.pys](data_mapper_vs_active_record.pys)  
**Wikipedia / ref:** [Data Mapper vs Active Record](https://martinfowler.com/eaaCatalog/dataMapper.html)

## Intent

Active Record saves itself; Data Mapper keeps persistence outside the domain object.

## Prompting an AI

**Say this:** “Side-by-side ArProduct.save vs ProductMapper.insert.”

**Not this:** “Call everything a repository.”

**Confusion to avoid:** Active Record ≠ Data Mapper.

## Run

```text
python -m transpiler run examples/patterns/persistence/data_mapper_vs_active_record.pys
```
