# ADR-017: Declared source roots and same-package tests

| | |
| --- | --- |
| Status | Proposed |
| Date | 2026-08-04 |
| Source | Webserver teaching example (same-folder `package` tests); [F-006](../TODO-FUTURE.md#f-006-source-roots-and-same-package-tests) |

## Context

Today a file’s `package` visibility is **same filesystem folder**. That forced
`examples/webserver/test_*.pys` to sit beside production modules so they can
see `package class` members without widening modifiers to `public` / `global`.

That layout is a **PYS-level gap**, not an app preference: production trees
want `src/…` and tests want `tests/…` while remaining the **same package**.

## Decision (target)

Project-manifest level (non-normative layout; tooling enforces resolution):

```text
pys.toml
src/
  billing/
    Invoice.pys        # package: billing
tests/
  billing/
    InvoiceTest.pys    # package: billing — same relative path, different root
```

```toml
[source_roots]
main = "src"
test = "tests"
```

**Resolution rule:** a file’s package is its path relative to whichever
declared source root contains it. Two files under different roots are in the
same package **if and only if** their post-root-stripping relative paths are
identical. Package-scoped members in `src/billing/Invoice.pys` are therefore
visible to `tests/billing/InvoiceTest.pys` without widening access modifiers
and without either file naming the other.

## Consequences

- Sem / import / IDE discovery must resolve packages via declared roots, not
  only `dirname(file)`.
- `examples/webserver/` (and similar flat examples) should be **refactored**
  once this lands: move app code under a main root and tests under a test root
  with mirrored relative paths.
- Until then, same-folder `test_*.pys` remain the supported pattern.
- Manifest name (`pys.toml` vs extending `pys.deps`) is implementation detail;
  the resolution rule above is the contract.

## Rejected alternatives

- Widen webserver types to `public` so tests can live elsewhere (teaches the
  wrong least-privilege story).
- Special-case “test imports ignore package” (hidden privilege, not a package
  model).
- Require `friend` / test-only modifiers (extra surface; roots already fix it).
