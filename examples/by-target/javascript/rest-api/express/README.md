# Express REST shop (JavaScript target)

Node **Express** twin of [`examples/rest-api/shop/`](../../../../rest-api/shop/)
(same JSON routes; no DIY HTTP stack).

| Folder | Phase | Port |
|--------|-------|------|
| [`memory/`](memory/) | In-memory CRUD | 8190 |
| [`mysql/`](mysql/) | mysql2 persistence | 8191 |
| [`jwt/`](jwt/) | Bearer on writes | 8192 |

Each silo has `pys.toml` with `target = "javascript"` and `[dependencies.npm]`.
Use **Run Project** on the silo toml.
