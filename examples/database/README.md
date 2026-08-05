# Shop example — `entity` identity + MySQL CRUD (OO / SOLID layout)

Console app that maps [`shop.sql`](shop.sql) tables to PYS **`entity`** types
and exercises identity equality while doing CRUD. Teaching companion to
[`docs/DATA_ENTITY.md`](../../docs/DATA_ENTITY.md).

## Layers (SOLID)

| File | Responsibility |
|------|----------------|
| [`shop.sql`](shop.sql) | MySQL schema (`product`, `order`, `order_line`) |
| [`seed_boardgames.sql`](seed_boardgames.sql) | Reproducible Dutch board-game catalog + sample orders |
| [`models.pys`](models.pys) | Domain entities (`Product`, `Order`, `OrderLine`) |
| [`db.pys`](db.pys) | MySQL session + cell conversion (**S**) |
| [`mappers.pys`](mappers.pys) | [Data Mapper](https://martinfowler.com/eaaCatalog/dataMapper.html) contracts + MySQL mapping: SQL and tuple/entity translation |
| [`repositories.pys`](repositories.pys) | Typed abstract [Repository](https://martinfowler.com/eaaCatalog/repository.html) contracts + mapper-backed implementations |
| [`console.pys`](console.pys) | `Console` port + `StdConsole` adapter (**S**, **D**) |
| [`menus.pys`](menus.pys) | One class per screen (**S**); depends on repository **ports** |
| [`shop_app.pys`](shop_app.pys) | Composition root — wiring only |
| [`pys.toml`](pys.toml) | `[project].main = shop_app.pys` |

- **S**ingle responsibility: SQL/row translation stays in mappers; entity
  collection operations stay in repositories; prompts stay in menus/console.
- **O**pen/closed: add a new `Menu` implementor and one `MainMenu` case.
- **L**iskov: `OrderLine` is a substitutable `Order` for identity inheritance.
- **I**nterface segregation: separate product / order / line repository contracts.
- **D**ependency inversion: menus take abstract `ProductRepository` etc.; default
  repositories take abstract mappers; only MySQL mappers know `ShopDatabase`.

## Repository vs Data Mapper

These are deliberately separate patterns:

- A **Data Mapper** transfers between relational rows and entities. It owns
  table/column names, SQL, and `tuple → Product/Order/OrderLine` conversion.
- A **Repository** presents persisted entities as a collection-like domain
  boundary: `all`, `get`, `add`, `save`, `remove`. It delegates storage work
  to a mapper and contains no SQL.

The Repository contracts are abstract classes because PYS abstract methods
preserve typed generic returns such as `list<Product>` while still allowing
the menus to depend on a nominal, substitutable port. The concrete
`Default*Repository` classes are intentionally database-agnostic.

## Credentials

```text
host=localhost
user=pys
password=123456789
database=shop
```

Requires `mysql-connector-python` (repo root [`pys.deps`](../../pys.deps)).

## Schema + seed data

1. Create tables (once):

```text
mysql -u pys -p < examples/database/shop.sql
```

2. Load a Dutch **board-game shop** demo catalog (products, orders, lines):

```text
mysql -u pys -p shop < examples/database/seed_boardgames.sql
```

[`seed_boardgames.sql`](seed_boardgames.sql) clears existing `shop` rows, then
inserts ~18 products (basisspellen, uitbreidingen, sleeves, dobbelaccessoires)
and a few sample orders with Dutch `customer_ref` values. Unit prices are
illustrative EUR snapshots inspired by common NL listings (bol.com,
Spellenhuis.nl, Lobbes, 999games.nl) — not live prices. Safe to re-run.

## Run

From the repo root:

```text
python -m transpiler run examples/database/shop_app.pys
```

Or (uses `pys.toml` main):

```text
python -m transpiler run examples/database
```

## What to try

1. **Products** — create / list / update name or price / activate / delete.
2. **Orders** — create / update status / delete (lines cascade).
3. **Order lines** — add a line (snapshots SKU + price from `Product`), change qty.
4. **Identity demos** — same `productId` with different names → `==`; composite
   `(orderId, lineNumber)` for `OrderLine`; load from DB, mutate `name` in
   memory, still equal to a second load of the same id.

Non-key fields are what CRUD updates; identity fields stay `fix` and drive `==`.

MySQL Data Mappers use `%s` parameters rather than concatenating user input
into SQL. This keeps the teaching example aligned with production-safe query
construction while leaving transaction policy intentionally small.
