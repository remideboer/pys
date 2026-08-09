# Phase 2 — Express MySQL shop (JavaScript target)

Same JSON routes as the memory Express shop on **8191**, persistence via
**mysql2** callbacks (Node has no sync cursor API). Schema/seed match the
Python shop (`shop.sql`, `seed_boardgames.sql`).

## Setup

```bash
mysql -u pys -p < shop.sql
mysql -u pys -p shop < seed_boardgames.sql
```

## Run

```bash
python -m transpiler run examples/by-target/javascript/rest-api/express/mysql/src/main.pys
```

Or **Run Project** on `pys.toml`.

## Layout

| Path | Role |
|------|------|
| `src/db.pys` | `ShopDatabase` + mysql2 connection |
| `src/mappers.pys` | SQL + row→entity (callbacks) |
| `src/repositories.pys` / `store.pys` | Ports + composition |
| `src/app.pys` | Express wiring |
