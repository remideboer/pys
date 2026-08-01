# Pokemon TCG demo (PyQt6 + PYS) — isolated silo

Type-safe OO PYS example using **PyQt6** from `pys.deps`: browse a
[TCGdex](https://tcgdex.dev/rest)-extracted card catalog, manage an owned
collection with per-type stats, and build decks from owned cards.

Self-contained folder (`domain` / `store` / `data` / `pys.deps`).
Tkinter twin: `examples/gui/pokemontcg/`.

Clicking a master-list row updates the detail pane immediately
(`QListWidget.currentRowChanged`). The first catalog card is selected on startup.

## Run

```bash
python -m transpiler run examples/gui/PyQt/main.pys
```

## Refresh the catalog (network)

```bash
python -m transpiler run examples/gui/PyQt/fetch_catalog.pys
```

## Tabs

| Tab | Master (left) | Detail (right) |
|-----|---------------|----------------|
| Catalog | Card list (click → detail) | Stats, types, attacks; **Add to collection** |
| Collection | Owned + qty (click → detail) | Card detail; **+1 / -1 / Remove**; type stats |
| Decks | Deck names (click → detail) | Deck contents; create/delete; add/remove cards |

## Layout

| File | Role |
|------|------|
| `main.pys` | Entry — `PokemonQtApp` |
| `ui.pys` | PyQt6 tabs master–detail |
| `domain.pys` / `store.pys` | Typed domain + JSON I/O |
| `pys.deps` | `pyqt6` |
| `data/` | `catalog.json`, `collection.json`, `decks.json` |
