# Local TLS material — do not commit PEMs, keys, or openssl configs.
# Generate with: python examples/webserver/scripts/gen_dev_certs.py

Regenerate self-signed localhost cert + key into this folder (gitignored):

```bash
python examples/webserver/scripts/gen_dev_certs.py
```

Requires `cryptography` or `openssl` on PATH. Ops/prod TLS is out of band.
