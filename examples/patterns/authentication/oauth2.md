# OAuth 2.0

**Category:** Authentication  
**Status: stub — implement later**

**Wikipedia:** [OAuth](https://en.wikipedia.org/wiki/OAuth)

## Intent

Delegate authentication / authorization to an external identity provider and
obtain tokens via standardized grant flows (authorization code, client
credentials, …).

## Why stubbed

Needs browser redirects, an IdP, and usually HTTPS callback URLs — beyond a
small in-process PYS demo. Prefer linking a future teaching sample to a local
mock IdP rather than inventing a fake OAuth.

## Related

- Runnable token shape: [token_based.md](token_based.md)
- HTTP JWT shop: [`examples/rest-api/shop/jwt/`](../../rest-api/shop/jwt/)
