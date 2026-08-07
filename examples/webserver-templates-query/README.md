# Template HTTP server — query-string binding

Extends the if/for template server
([`../webserver-templates-logic/`](../webserver-templates-logic/), CER-040) with:

| Piece | Meaning |
|-------|---------|
| `?name=Ada&vip=1` | Parsed into `HttpRequest.query` (first value per key) |
| `/hello?name=…` | Binds `name`, `title`, `vip` into `hello.html` |
| `/shop?name=…&sale=0` | Same binding for shopper name + sale flag |

Port **8103**.

## Run

```bash
python -m transpiler run examples/webserver-templates-query/src/main.pys
curl "http://127.0.0.1:8103/hello?name=Ada&vip=1"
curl "http://127.0.0.1:8103/shop?name=Remi&sale=0"
```

Missing `name` defaults to `friend` (hello) or `guest` (shop). Values are HTML-escaped by the engine.

## Tests

```bash
set PYS_WORKSPACE_ROOT=examples\webserver-templates-query
set PYS_TEMPLATES_DIR=examples\webserver-templates-query\templates
python -m transpiler run examples/webserver-templates-query/tests/test_query.pys
python -m pytest tests/test_webserver_templates_query.py -q
```
