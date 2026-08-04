# ADR-017: Declared source roots and same-package tests

| | |
| --- | --- |
| Status | Accepted (target; implementation Active as F-006) |
| Date | 2026-08-04 |
| Source | [`requirements/package_resolution_testing_philosophy.md`](../../requirements/package_resolution_testing_philosophy.md); [F-006](../TODO-FUTURE.md#f-006-source-roots-and-same-package-tests) |
| Trigger | `examples/webserver/` flat same-folder tests — production-like layout gap |

## Context

Today a file’s `package` visibility is **same filesystem folder**. That forced
`examples/webserver/test_*.pys` to sit beside production modules so they can
see `package class` members without widening modifiers to `public` / `global`.

The webserver was built partly to **discover** such PYS gaps under a
production-like project. The layout gap is language/tooling work (F-006), not
an app preference. Remaining webserver spec work is deferred ([F-007](../TODO-FUTURE.md#f-007-webserver-full-spec-remainder)) until this lands and the
example is refactored.

## Decision

Normative philosophy and diagnostics: requirements doc §1–4.

Project-manifest level (non-normative directory names; tooling enforces
resolution):

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

**Rejected with the requirements:** `private` test bypass; C# `namespace`;
`partial class`.

Without a `pys.toml` `[source_roots]` table, keep the legacy rule: same
parent directory ⇒ same package (compat for flat examples).

## Consequences

- Sem / import / IDE discovery resolve packages via declared roots, not only
  `dirname(file)`.
- Access errors for mismatched packages include the educational diagnostic
  (requirements §4): name both packages/roots and suggest the mirrored path.
- After F-006: refactor `examples/webserver/` to `src/` + `tests/`.
- Manifest filename is `pys.toml` (requirements); may coexist with `pys.deps`.

## Rejected alternatives

- Widen webserver types to `public` so tests can live elsewhere (teaches the
  wrong least-privilege story).
- Special-case “test imports ignore package” (hidden privilege, not a package
  model).
- Require `friend` / test-only modifiers (extra surface; roots already fix it).
