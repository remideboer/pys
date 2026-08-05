# Requirements → permanent documentation

Draft specifications under `requirements/` capture grammar, BDD scenarios,
cross-language comparisons, citations, and didactic notes that drove language
design. **Normative decisions live in ADRs / LANGUAGE / CERs / the beginner
book** — not only in these drafts. When a requirement lands, migrate lasting
rationale into those docs in the same change set (see
`.cursor/rules/project-memory.mdc` and feature DoD).

| Requirement | Permanent homes |
| --- | --- |
| [`traits.md`](traits.md) | [ADR-009](../docs/adr/ADR-009-traits-composition.md), [CER-008](../docs/evolution/CER-008-traits.md), LANGUAGE §Traits, book `chapter_4_4` |
| [`trait_requires_remapping.md`](trait_requires_remapping.md) | ADR-009 § remap, [CER-027](../docs/evolution/CER-027-trait-requires-remapping.md), LANGUAGE, book `chapter_4_4` |
| [`abstract_class.md`](abstract_class.md) | [ADR-010](../docs/adr/ADR-010-abstract-classes.md), [CER-009](../docs/evolution/CER-009-abstract-classes.md), LANGUAGE §Abstract, book `chapter_4_3` |
| [`data_entity.md`](data_entity.md) | [ADR-011](../docs/adr/ADR-011-data-and-entity.md), [DATA_ENTITY.md](../docs/DATA_ENTITY.md), [CER-011](../docs/evolution/CER-011-data-and-entity.md), book `chapter_4_5` / `4_6` |
| [`lambda.md`](lambda.md) | [ADR-012](../docs/adr/ADR-012-lambdas.md), [CER-012](../docs/evolution/CER-012-lambdas.md), LANGUAGE §Lambdas, book `chapter_6_4` |
| [`atomic.md`](atomic.md) | [ADR-013](../docs/adr/ADR-013-atomic.md), [CONCURRENCY.md](../docs/CONCURRENCY.md), [CER-013](../docs/evolution/CER-013-atomic.md), book `chapter_6_2`–`6_3` |
| [`enforced_ordering.md`](enforced_ordering.md) | [ADR-015](../docs/adr/ADR-015-enforced-ordering.md), [CER-017](../docs/evolution/CER-017-enforced-ordering.md), LANGUAGE § ordering, book / S7 |
| [`package_resolution_testing_philosophy.md`](package_resolution_testing_philosophy.md) | [ADR-017](../docs/adr/ADR-017-source-roots-same-package-tests.md) (impl Active / F-006) |
| [`propagate_panic.md`](propagate_panic.md) | [ADR-021](../docs/adr/ADR-021-result-propagate-panic.md), [CER-025](../docs/evolution/CER-025-result-propagate-panic.md), LANGUAGE `result`/`propagate`, book `basics_outcomes` |
| [`enum_optional_statement_terminator.md`](enum_optional_statement_terminator.md) | [ADR-022](../docs/adr/ADR-022-optional-terminators-grammar.md), [CER-026](../docs/evolution/CER-026-optional-terminators-grammar.md) |
| [`concept_entrypoint.md`](concept_entrypoint.md) | Book [`under_the_hood_entrypoint.md`](../book/under_the_hood_entrypoint.md) |
| [`concept_memory_model.md`](concept_memory_model.md) | Book [`under_the_hood_memory.md`](../book/under_the_hood_memory.md), CONCURRENCY |
| `*.pys` (structs, enums, switch, binary/hex) | Matching ADR-005 / ADR-006 / ADR-007 / ADR-008 + examples |

`.pys` files here are hybrid: short locked rules in comments plus runnable
samples. Prefer the ADRs for decisions; keep samples as teaching corpus.
