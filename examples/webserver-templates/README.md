# Template HTTP server

Renders HTML from `templates/` with `{{key}}` placeholders (HTML-escaped).
Port **8101**. Separate from the static-file server so students see the
templating layer alone.

## Run

```bash
python -m transpiler run examples/webserver-templates/src/main.pys
curl http://127.0.0.1:8101/hello
```

Expected body contains `Hello, <strong>Ada</strong>!`.

## Tests

```bash
set PYS_WORKSPACE_ROOT=examples\webserver-templates
set PYS_TEMPLATES_DIR=examples\webserver-templates\templates
python -m transpiler run examples/webserver-templates/tests/test_templates.pys
python -m pytest tests/test_webserver_templates.py -q
```
