# Data formats

All paths are under `examples/gui/pokemontcg/data/`.

## `catalog.json` (read-only at runtime)

Produced by `fetch_catalog.pys` from [TCGdex REST v2](https://tcgdex.dev/rest).

```json
{
  "source": "TCGdex",
  "setId": "swsh3",
  "cards": [
    {
      "id": "swsh3-1",
      "name": "Butterfree V",
      "category": "Pokemon",
      "hp": 180,
      "types": ["Grass"],
      "rarity": "Ultra Rare",
      "setName": "Darkness Ablaze",
      "stage": "Basic",
      "retreat": 1,
      "attacks": [
        { "name": "Dizzy Powder", "damage": "", "cost": ["Grass", "Colorless"] }
      ],
      "image": "https://assets.tcgdex.net/en/swsh/swsh3/1"
    }
  ]
}
```

### TCGdex → local field map

| Local | TCGdex Card ([reference](https://tcgdex.dev/reference/card)) |
|-------|--------------------------------------------------------------|
| `id` | `id` |
| `name` | `name` |
| `category` | `category` |
| `hp` | `hp` (0 if absent) |
| `types` | `types` |
| `rarity` | `rarity` |
| `setName` | `set.name` |
| `stage` | `stage` |
| `retreat` | `retreat` (0 if absent) |
| `attacks[].name` | `attacks[].name` |
| `attacks[].damage` | `attacks[].damage` as string |
| `attacks[].cost` | `attacks[].cost` |
| `image` | `image` (asset base URL) |

Dropped intentionally: pricing, variants, legality, illustrator, weaknesses.

## `collection.json`

```json
{
  "owned": [
    { "cardId": "swsh3-1", "quantity": 2 }
  ]
}
```

## `decks.json`

```json
{
  "decks": [
    {
      "name": "Grass Starters",
      "entries": [
        { "cardId": "swsh3-1", "quantity": 1 }
      ]
    }
  ]
}
```

Deck `quantity` for a card must be ≤ owned quantity for that `cardId`.
