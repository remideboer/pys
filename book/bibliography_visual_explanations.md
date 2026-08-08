# Bibliography — visual explanations (Session 10 diagrams)

Short teaching bibliography for the diagram rules in
[How these diagrams work](chapter_9_0_visual_style.md). These are **design
inputs**, not a literature review.

## Cognitive / learning science

**Paivio, A. (1986).** *Mental representations: A dual coding approach.*
Oxford University Press.

- **Used for:** Pair every figure with prose and a caption that restates the
  claim (verbal + nonverbal channels).

**Mayer, R. E. (2009).** *Multimedia learning* (2nd ed.). Cambridge University
Press.

- **Used for:** Coherence (strip decoration), signaling (bold labels / accent
  “inside”), and spatial contiguity (diagram next to the section it explains).

**Sweller, J. (2011).** Cognitive load theory. In *Psychology of learning and
motivation* (Vol. 55). Academic Press.

- **Used for:** Cap nodes per figure; one idea per diagram so working memory is
  not flooded with UML detail.

**Lakoff, G., & Johnson, M. (1980).** *Metaphors we live by.* University of
Chicago Press.

- **Used for:** Stable metaphors — *container* (inside/outside), *path* (flow /
  pipeline), already established in earlier book chapters (socket, machine).

## Visual design

**Tufte, E. R. (2001).** *The visual display of quantitative information*
(2nd ed.). Graphics Press.

- **Used for:** High data-ink: sparse boxes and arrows; no gradients, glow, or
  decorative icon clusters.

## Software metaphor (architecture image)

**Cockburn, A. (2005).** Hexagonal architecture.
https://alistair.cockburn.us/hexagonal-architecture/

- **Used for:** The *ports and adapters* “inside protected by a boundary”
  picture that Session 10 layers diagrams echo (not psychology — complementary
  domain metaphor).

## How to read this list

If a new Session 10 figure breaks a rule above, fix the figure — do not invent a
second visual language. Companion Mermaid in `examples/patterns/**/*.md` may
stay UML-shaped; the beginner book stays on `concept-diagram` HTML.

---

[Previous: Resources](resources.md) · [Back to Summary](SUMMARY.md)
