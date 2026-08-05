# Requirements folder (temporary drafts)

`requirements/` holds **draft** specs used while designing a feature. It is
**not** permanent project memory.

When a feature lands, **copy** lasting content into permanent homes under
`docs/` (ADRs, LANGUAGE, CONCURRENCY, DATA_ENTITY, CERs) and the beginner
`book/` — including rationale tables, cross-language comparisons, didactic
notes, and **full bibliographic references**. Linking alone from an ADR to a
requirement file does **not** count as absorbed: if `requirements/` were
deleted tomorrow, the permanent docs must still stand alone.

| Requirement draft | Permanent home (content lives here) |
| --- | --- |
| [`data_entity.md`](data_entity.md) | [`docs/DATA_ENTITY.md`](../docs/DATA_ENTITY.md) · [ADR-011](../docs/adr/ADR-011-data-and-entity.md) |
| [`traits.md`](traits.md) | [ADR-009](../docs/adr/ADR-009-traits-composition.md) · LANGUAGE §Traits · book `chapter_4_4` |
| [`trait_requires_remapping.md`](trait_requires_remapping.md) | ADR-009 · [CER-027](../docs/evolution/CER-027-trait-requires-remapping.md) · LANGUAGE · book |
| [`abstract_class.md`](abstract_class.md) | [ADR-010](../docs/adr/ADR-010-abstract-classes.md) · LANGUAGE · book `chapter_4_3` |
| [`lambda.md`](lambda.md) | [ADR-012](../docs/adr/ADR-012-lambdas.md) · LANGUAGE §Lambdas · book `chapter_6_4` |
| [`atomic.md`](atomic.md) | [ADR-013](../docs/adr/ADR-013-atomic.md) · [`docs/CONCURRENCY.md`](../docs/CONCURRENCY.md) · book `chapter_6_2`–`6_3` |
| [`enforced_ordering.md`](enforced_ordering.md) | [ADR-015](../docs/adr/ADR-015-enforced-ordering.md) · LANGUAGE § ordering |
| [`package_resolution_testing_philosophy.md`](package_resolution_testing_philosophy.md) | [ADR-017](../docs/adr/ADR-017-source-roots-same-package-tests.md) (impl Active / F-006) |
| [`propagate_panic.md`](propagate_panic.md) | [ADR-021](../docs/adr/ADR-021-result-propagate-panic.md) · LANGUAGE · book `basics_outcomes` |
| [`enum_optional_statement_terminator.md`](enum_optional_statement_terminator.md) | [ADR-022](../docs/adr/ADR-022-optional-terminators-grammar.md) · [CER-026](../docs/evolution/CER-026-optional-terminators-grammar.md) |
| [`nullable.md`](nullable.md) | [ADR-023](../docs/adr/ADR-023-explicit-nullability.md) · [CER-028](../docs/evolution/CER-028-nullable.md) · LANGUAGE § Explicit absence · book `basics_null` |
| [`concept_entrypoint.md`](concept_entrypoint.md) | Book [`under_the_hood_entrypoint.md`](../book/under_the_hood_entrypoint.md) |
| [`concept_memory_model.md`](concept_memory_model.md) | Book [`under_the_hood_memory.md`](../book/under_the_hood_memory.md) · CONCURRENCY |
| `*.pys` hybrids | Matching ADR-005 / ADR-006 / ADR-007 / ADR-008 + `examples/` |

ADR metadata may note a draft filename for history, but readers must never need
to open `requirements/` to recover decisions, citations, or teaching rationale.
