# Static file webserver

Serves files from `www/` over HTTP/1.1 (port **8100**). Blocks `..` traversal.

## Run

```bash
python -m transpiler run examples/webserver-static/src/main.pys
curl http://127.0.0.1:8100/
curl http://127.0.0.1:8100/about.html
curl http://127.0.0.1:8100/css/site.css
```

Expected: HTML for `/` and `/about.html`; CSS for `/css/site.css`; `404` for missing paths; `404` for `/../secrets`.

## Tests

```bash
set PYS_WORKSPACE_ROOT=examples\webserver-static
python -m transpiler run examples/webserver-static/tests/test_static_resolve.pys
python -m pytest tests/test_webserver_static.py -q
```
