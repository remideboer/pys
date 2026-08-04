# Source roots teaching example (ADR-017)

| Path | Role |
|------|------|
| `pys.toml` | `[source_roots] main=src test=tests` |
| `src/billing/Invoice.pys` | package `billing` production types |
| `tests/billing/InvoiceTest.pys` | same package — can use `package` exports |

```bash
python -m transpiler run examples/source_roots/tests/billing/InvoiceTest.pys
```

Wrong folder (e.g. `tests/test_utils/InvoiceTest.pys`) importing a `package`
symbol from `src/billing` fails with a diagnostic that names both packages and
suggests `tests/billing/InvoiceTest.pys` (quick fix: move file).
