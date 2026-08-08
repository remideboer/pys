# Test Data Builder

**Category:** Testing  
**Demo:** [test_data_builder.pys](test_data_builder.pys)  
**Wikipedia / ref:** [Test Data Builder](https://www.growingobjectorientedsoftware.com/)

## Intent

Fluent builder for one-off fixture variations.

## Prompting an AI

**Say this:** “OrderBuilder().withCustomer(...).withTotalCents(...).build().”

**Not this:** “Huge constructor calls with magic numbers and no defaults.”

**Confusion to avoid:** Builder (tests) ≠ GoF Builder for production APIs.

## Run

```text
python -m transpiler run examples/patterns/testing/test_data_builder.pys
```
