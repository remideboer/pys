# Mutual TLS (mTLS)

**Category:** Authentication  
**Status: stub — implement later**

**Wikipedia:** [Mutual authentication](https://en.wikipedia.org/wiki/Mutual_authentication)

## Intent

Both client and server present X.509 certificates so each side authenticates
the other at the TLS layer.

## Why stubbed

Requires TLS termination, certificate issuance, and trust stores — not
expressible as a pure in-process PYS teaching demo without OS/network plumbing.

## Related

- Application-level auth demos in this folder (session / token / API key / Basic)
