"""Generate self-signed localhost certs for examples/webserver (local/ops only).

Never commit PEMs, keys, or openssl.cnf — they are gitignored. Run from repo root
or from examples/webserver:

  python examples/webserver/scripts/gen_dev_certs.py
"""

from __future__ import annotations

import datetime
import ipaddress
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "certs"
CERT = OUT / "localhost.pem"
KEY = OUT / "localhost-key.pem"

# Written only as a temp file for openssl; never intended for the repo.
_OPENSSL_CNF = """\
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = localhost

[v3_req]
subjectAltName = @alt_names
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth

[alt_names]
DNS.1 = localhost
IP.1 = 127.0.0.1
"""


def ensure_certs() -> None:
    """Create cert+key if missing. Raises on failure."""
    if CERT.is_file() and KEY.is_file():
        return
    code = main()
    if code != 0 or not CERT.is_file() or not KEY.is_file():
        raise RuntimeError(
            "TLS material missing; run: python examples/webserver/scripts/gen_dev_certs.py"
        )


def _via_cryptography() -> None:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    san = x509.SubjectAlternativeName(
        [
            x509.DNSName("localhost"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ]
    )
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(san, critical=False)
        .sign(key, hashes.SHA256())
    )
    OUT.mkdir(parents=True, exist_ok=True)
    KEY.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    CERT.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def _via_openssl() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", suffix=".cnf", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(_OPENSSL_CNF)
        conf_path = tmp.name
    try:
        env = dict(os.environ)
        env["OPENSSL_CONF"] = conf_path
        subprocess.check_call(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-keyout",
                str(KEY),
                "-out",
                str(CERT),
                "-days",
                "3650",
                "-nodes",
                "-config",
                conf_path,
            ],
            env=env,
        )
    finally:
        Path(conf_path).unlink(missing_ok=True)


def main() -> int:
    try:
        _via_cryptography()
        print(f"wrote {CERT} and {KEY} (cryptography)")
        return 0
    except ImportError:
        pass
    try:
        _via_openssl()
        print(f"wrote {CERT} and {KEY} (openssl)")
        return 0
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        print(f"cert generation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
