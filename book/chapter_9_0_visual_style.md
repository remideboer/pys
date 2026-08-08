# 10.0. How these diagrams work

Session 10 uses the same **concept diagrams** as earlier chapters: plain boxes,
arrows, and shared borders — not UML class soup. The goal is to match how people
already think about software (*inside* vs *outside*, *ports*, *paths*, *machines*).
Sessions 3–7 reuse this chrome for control flow, functions, concurrency, and
tests.

### Metaphors we reuse

| Metaphor | You already saw it | Here it means |
|----------|--------------------|---------------|
| Drawer / label | Basics memory grid | A place that holds a value |
| Socket + cable | Interfaces | A port / contract the caller depends on |
| Machine + gears | Classes | An implementer with real behavior |
| Flow arrow | Entrypoint / under the hood | Order of steps or dependency direction |
| Common region | — | Layers that belong together (domain vs adapters) |

### Rules (keep diagrams teachable)

1. **One idea per figure** — if you need two claims, use two figures.
2. **Labels on the boxes** — do not force the reader to decode a legend first.
3. **Caption restates the claim** — dual coding: picture + words.
4. **Cap the nodes** — roughly four to six labeled parts; drop decoration.
5. **Same chrome as the rest of the book** — warm figure panel, accent fill for
   “inside” / active, dashed border for a **boundary** (ACL, ports).

Why these rules? Short research notes and citations live in
[Bibliography: visual explanations](bibliography_visual_explanations.md).

<figure class="concept-diagram" role="img" aria-label="Inside domain core, application service, dashed ports edge, outside adapters">
  <div class="diagram-layers">
    <div class="diagram-layer diagram-layer-core">
      <strong>Domain (inside)</strong>
      <span>rules and types you protect</span>
    </div>
    <div class="diagram-layer">
      <strong>Application service</strong>
      <span>use-case orchestration</span>
    </div>
    <div class="diagram-layer diagram-layer-edge">
      <strong>Ports (boundary)</strong>
      <span>interfaces the inside depends on</span>
    </div>
    <div class="diagram-layer diagram-outside">
      <strong>Adapters / outside</strong>
      <span>HTTP, SQL, legacy shapes</span>
    </div>
  </div>
  <figcaption>
    Shared regions show what belongs together. The dashed edge is the boundary
    you defend — the same “inside vs outside” story as hexagonal architecture.
  </figcaption>
</figure>

---

[Previous: Patterns session](chapter_9_session_patterns.md) · [Next: App shape](chapter_9_1_app_shape.md)
