# PYS Language Support 0.0.79

Trunk-based extension release. Tag: `extension-v0.0.79`.

## Highlights

- **Result failures use `error(...)`** — the failure constructor and switch
  pattern are now `error(payload)` / `case error(message)` (not `err`). Legacy
  `err(...)` is rejected with an actionable rename tip.
- **Book chapter filenames include concepts** — e.g.
  `chapter_4_1a_classes`, `chapter_4_1b_inheriting_classes`, so chapters are
  easier to find by topic.
- **GitHub Release channel** — this version ships the student **ELO zip** and
  VSIX on the GitHub Releases page for offline / LMS install.

## Install

- **Marketplace** (when published): `ext install remideboer.pys-language`
- **ELO / offline:** download `pys-student-0.0.79.zip`, unzip, run `install.cmd`
  (Windows) or `./install.sh` (macOS/Linux), then reload the editor.

Requires Python 3.10+ on PATH. The pack includes the bundled transpiler.
