# 9.3. Packages and source roots

By default, “same package” means **same folder**. Projects often mirror
production and tests:

```toml
# pys.toml
[source_roots]
main = "src"
test = "tests"
```

Then `src/billing/Invoice.pys` and `tests/billing/InvoiceTest.pys` share
package `billing`. Tests can use `package` exports without widening them
to `global`.

If a test file sits in the wrong folder (for example `tests/test_utils/`)
and imports a `package` symbol from `billing`, PYS reports
`pys.package-mismatch` and suggests moving the file — the IDE offers a
quick fix.

Teaching example: [`examples/source_roots/`](../examples/source_roots/).

### Exercise

> Open `examples/source_roots/`, run the billing test, then read
> `WrongPlaceTest.pys` and explain why the import is commented out.

---

[Previous: Better PYS with TDD](chapter_7_2.md) · [Next: Types and declarations](chapter_8_1.md)
