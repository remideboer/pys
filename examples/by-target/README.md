# Target-dependent examples
#
# Showcase language demos that need a specific emit target / native packages
# live here so each silo can own a single `pys.toml` (entrypoint + deps).
#
# Target-independent dense showcase: [`../main.pys`](../main.pys)
# Existing Python GUI track (Tk / ttkbootstrap / PyQt): [`../gui/`](../gui/)

| Path | Target | Notes |
| --- | --- | --- |
| [`python/mysql/`](python/mysql/) | Python | `mysql-connector-python` via `[dependencies]` → central repo |
| [`javascript/mysql/`](javascript/mysql/) | JavaScript | `mysql2` via `[dependencies.npm]` → central npm cache |
| [`javascript/gui_nodegui/`](javascript/gui_nodegui/) | JavaScript | [@nodegui/nodegui](https://github.com/nodegui/nodegui) (runs under **qode**) |

## JavaScript deps (central repo)

Declare npm packages under `[dependencies.npm]` in the silo’s `pys.toml`, and
set `target = "javascript"` under `[project]`. **Run Project** on that toml
(or bare `transpiler run` without `--target`) uses it. **Run** installs into
`~/.pys/repository/npm/<fingerprint>/` — no local `npm install` / silo
`node_modules` required.

```text
python -m transpiler run examples/by-target/javascript/mysql/main.pys
# same as --target javascript when pys.toml has target = "javascript"
```

Override the cache root with `PYS_REPO` (same as Python wheels: `$PYS_REPO/npm/...`).
