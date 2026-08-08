# Session 6 — Tests you can trust

Automated checks let you change code without fear. In PYS coursework,
tests are ordinary `.pys` programs that set up data, call your API, and
`print` (or fail loudly) when something is wrong — often living under a
`tests/` tree next to `src/` via `pys.toml` source roots.

<figure class="concept-diagram" role="img" aria-label="Session 6 map from first test through TDD to source roots">
  <div class="diagram-stack">
    <div class="diagram-box"><strong>9.1 First test</strong><span>Arrange · Act · Assert</span></div>
    <div class="diagram-box"><strong>9.2 TDD</strong><span>Red · Green · Refactor</span></div>
    <div class="diagram-box"><strong>9.3 Source roots</strong><span>src/ · tests/ · same package</span></div>
  </div>
  <figcaption>
    Learn a repeatable check, then flip the order, then place files so
    packages stay honest.
  </figcaption>
</figure>

1. [Writing a first test](chapter_7_1_first_test.md)
2. [Better PYS with TDD](chapter_7_2_tdd.md)
3. [Packages and source roots](chapter_7_3_packages_source_roots.md)

---

[Previous: Lambdas and capture](chapter_6_4_lambdas_capture.md) · [Next: Writing a first test](chapter_7_1_first_test.md)
