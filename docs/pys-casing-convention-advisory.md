# PYS Design Advisory: Identifier Casing Convention

**Status:** Adopted
**Scope:** Naming convention for variables, methods, parameters, types, and constants across the PYS language surface.
**Decision:** Retain camelCase for members/variables/methods, PascalCase for type names, and SCREAMING_SNAKE_CASE for `const` fields. No adoption of snake_case as a general identifier convention.

## 1. Motivation

A recurring claim in developer discourse holds that snake_case is unambiguously easier for humans to parse than camelCase, based on cognitive science research. Since PYS is an educational language whose students are expected to move on to C# or Java, this claim was evaluated directly against PYS's specific goals before being accepted or rejected as a basis for the language's casing convention.

## 2. What the research actually shows

The empirical picture is less one-sided than the popular summary suggests, and citing it accurately matters for a language whose own design philosophy elsewhere in this specification insists on precision rather than convenient conclusions.

- Sharif and Maletic's eye-tracking study found that underscore-separated identifiers required fewer fixations and less time to recognize, suggesting a modest reduction in cognitive load during identification [1].
- Binkley et al., using a separate timed-response methodology with 135 subjects, reached the opposite conclusion: camel-cased identifiers led to higher accuracy across all subjects, and subjects trained in camelCase recognized camel-cased identifiers faster than underscored ones [2].
- A synthesis of both studies explicitly notes this contradiction: Sharif and Maletic found that underscore separation improves understandability, whereas Binkley et al. found that camelCase performs better [3].
- The original Sharif and Maletic eye-tracking paper itself is more conservative in its own abstract than later citations of it suggest: it reports no significant difference in accuracy between the two styles, with the only reliable difference being recognition speed, not correctness of understanding [4].
- A later, larger-scale study additionally found a slight camelCase advantage specifically for shorter identifier names [5].

**Conclusion drawn from the literature**: there is a small, somewhat replicated speed advantage for snake_case in raw first-glance identifier recognition, but no consistent advantage in comprehension accuracy, and at least one methodologically comparable study reaches the opposite conclusion. The frequently repeated claim that "research settles this in favor of snake_case" overstates the strength and consistency of the evidence.

## 3. A moderator present in every cited study: prior exposure

Each of the studies above reports that the effect is substantially reduced, or disappears, for programmers already trained in camelCase [1], [2], [4]. This matters directly for PYS: the advantage of snake_case is strongest for absolute beginners with no prior exposure to any convention, but this group adapts within weeks. Any short-term cognitive-load advantage is therefore largely transient, while the costs and benefits discussed in Section 4 are not.

## 4. Evaluation against PYS-specific criteria

| Criterion | snake_case | camelCase / PascalCase |
|---|---|---|
| Cognition (raw recognition speed) | Small, inconsistently replicated advantage | Small, inconsistently replicated disadvantage; possible advantage for short identifiers [5] |
| Learnability for absolute beginners | Marginally lower initial barrier | Marginally higher initial barrier, small in size |
| **Transfer to C#/Java** (explicit PYS goal) | Contrary to both target languages — both use camelCase for members/variables and PascalCase for types | Directly aligned — no relearning required; habit formed in PYS transfers immediately |
| **Internal consistency with the existing PYS specification** | Every example already written throughout the PYS design corpus (`getBalance`, `canAfford`, `isEmpty`, `compareTo`, `withdrawIfPossible`) uses camelCase; adopting snake_case would require revising the entire existing corpus and would break with the already-established `Customer`/`Product`/`OrderLine` type-naming convention | Already consistently applied; no revision required |
| **IDE tooling: subword/camel-hump matching** | Poorly supported — autocomplete typically matches only on prefix, not on each underscore-delimited segment | Broadly supported in modern IDEs (VS Code, IntelliJ, Rider): typing `gBI` resolves `getBalanceInfo` — a real productivity effect that grows with identifier length |
| Line length / horizontal space | Underscores add characters, relevant in a language whose own grammar keywords are already fairly verbose (`constructor_decl`, `interface_method`) | More compact; marginally less wrapping in long expressions |
| Keyboard ergonomics | Underscore requires Shift on most keyboard layouts, including Dutch QWERTY, at every word boundary | camelCase also requires Shift at every word boundary (capital letter) — comparable cost, not a differentiator |
| Coincidental overlap with the Python reference emitter | Would coincidentally match PEP 8 — but this is an emitter implementation detail, not a reason for the source language to conform, consistent with the specification/implementation boundary already established for `atomic` | No coincidental overlap, and none needed — the emitter can rewrite camelCase to the target convention internally without the source language following it |
| Consistency between type-casing and member-casing | Produces a mixed system: PascalCase for types (`Customer`), snake_case for members/instances (`customer_id`) — two different separation mechanisms (case-shift vs. underscore) active simultaneously | One coherent system: case-based separation throughout, differing only in the first letter (type vs. instance) — a single rule with one exception, easier to teach than two separate rules |

## 5. Decision

PYS retains camelCase for variables, parameters, and methods, and PascalCase for type names (`class`, `struct`, `data`, `entity`, `interface`, `trait`). This is not primarily a cognition-based decision — the cognitive evidence is mixed and the effect size is small and exposure-dependent — but a decision driven by three factors that outweigh it cumulatively:

1. Direct transfer to C# and Java, PYS's explicit pedagogical target.
2. Consistency with the entire existing PYS design corpus.
3. Materially better IDE tooling support for subword matching, which has a longer-lasting practical effect than the small, inconsistently replicated recognition-speed advantage reported for snake_case.

## 6. Retained exception: SCREAMING_SNAKE_CASE for constants

`const`-declared fields keep SCREAMING_SNAKE_CASE, unaffected by this decision. This preserves the one place where the underscore-separation research is most directly applicable — distinguishing one category of identifier (a fixed, compile-time constant) from all others at a glance — without extending the convention language-wide and incurring the transfer, consistency, and tooling costs identified in Section 4. This is also the convention already standard in both of PYS's target languages, C# and Java, as well as Python.

## References

[1] B. Sharif and J. I. Maletic, "An Eye Tracking Study on camelCase and under_score Identifier Styles," in *Proc. 18th IEEE Int. Conf. Program Comprehension (ICPC)*, Braga, Portugal, 2010, pp. 196–205, doi: 10.1109/ICPC.2010.41.

[2] D. Binkley, M. Davis, D. Lawrie, and C. Morrell, "To CamelCase or Under_score," in *Proc. 17th IEEE Int. Conf. Program Comprehension (ICPC)*, Vancouver, BC, Canada, 2009, pp. 158–167.

[3] "Understanding Code Understandability Improvements in Code Reviews," ResearchGate, doi: 10.48550/arXiv.2410.21990. [Online]. Available: https://www.researchgate.net/publication/224159770_An_Eye_Tracking_Study_on_camelCase_and_under_score_Identifier_Styles. [Accessed: Aug. 4, 2026].

[4] B. Sharif and J. I. Maletic, "An Eye Tracking Study on camelCase and under_score Identifier Styles," Semantic Scholar, [Online]. Available: https://www.semanticscholar.org/paper/An-Eye-Tracking-Study-on-camelCase-and-under_score-Sharif-Maletic/4524bf32179b61f961efa0c165221e68f567fd49. [Accessed: Aug. 4, 2026].

[5] M. J. Decker and J. I. Maletic, "To CamelCase or under_score," in *Proc. IEEE/ACM 41st Int. Conf. Software Engineering (ICSE)*, 2019, doi: 10.1109/ICPC.2019.00035. [Online]. Available: https://www.researchgate.net/publication/335498060_To_CamelCase_or_under_score. [Accessed: Aug. 4, 2026].
