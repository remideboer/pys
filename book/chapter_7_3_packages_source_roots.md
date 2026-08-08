# 9.3. Packages and source roots

By default, “same package” means **same folder**. Projects often mirror
production and tests:

<figure class="concept-diagram" role="img" aria-label="src and tests source roots sharing package billing">
  <div class="diagram-layers">
    <div class="diagram-layer diagram-layer-core">
      <strong>src/billing/</strong>
      <span>Invoice.pys · package exports</span>
    </div>
    <div class="diagram-layer diagram-layer-edge">
      <strong>same package name</strong>
      <span>billing</span>
    </div>
    <div class="diagram-layer diagram-outside">
      <strong>tests/billing/</strong>
      <span>InvoiceTest.pys · can import package</span>
    </div>
  </div>
  <figcaption>
    Source roots split folders; the package name still matches so tests stay
    close without widening to <code>global</code>.
  </figcaption>
</figure>

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

[Previous: Better PYS with TDD](chapter_7_2_tdd.md) · [Next: Patterns you name to build](chapter_9_session_patterns.md)
