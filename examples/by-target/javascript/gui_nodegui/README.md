# NodeGUI temperature converter (JS emit target).

Native desktop UI via [@nodegui/nodegui](https://github.com/nodegui/nodegui)
(Qt bindings for Node). Pair with the Python Tk track under `examples/gui/temperature_tk`.

## Run

`pys.toml` declares `@nodegui/nodegui` under `[dependencies.npm]` and
`target = "javascript"`. **Run** installs into
`~/.pys/repository/npm/<fingerprint>/` and prefers **qode** from
that cache (NodeGUI’s Qt-enabled Node). Plain `node` fails with
`ERR_DLOPEN_FAILED` on `nodegui_core.node` because Qt DLLs are not loaded.

```text
python -m transpiler run examples/by-target/javascript/gui_nodegui/main.pys
# or right-click pys.toml → Run Project
```

No local `npm install` / silo `node_modules` required.

## Requirements

- Desktop session (not headless CI). Acceptance tests only **transpile** (or
  resolve the central env when `npm` is available).
- If the native addon still fails to load after a bad install: delete the
  hashed folder under `~/.pys/repository/npm/` (or set `PYS_REPO` to a fresh
  temp) and re-Run; prefer an LTS Node for the **install** step (qode embeds
  Node 18).
