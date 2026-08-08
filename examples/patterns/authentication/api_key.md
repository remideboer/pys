# API key authentication

**Category:** Authentication  
**Demo:** [api_key.pys](api_key.pys)  
**Wikipedia:** [Application programming interface key](https://en.wikipedia.org/wiki/Application_programming_interface_key)

## Intent

Authenticate a caller with a pre-shared **API key** on each request (no
interactive login).

## Explanation

`ApiGateway` depends on an `ApiKeyValidator` port. A fixed-key validator is
injected at construction. Invalid keys get `deny:`; valid keys get `ok:`.

## Classic structure (UML)

```mermaid
classDiagram
    class Client
    class ApiGateway
    class ApiKeyValidator {
        <<interface>>
    }
    Client --> ApiGateway : api key
    ApiGateway --> ApiKeyValidator
```

## This demo

`FixedApiKeyValidator` implements the port; `ApiGateway.handle` is the gate.

```mermaid
classDiagram
    class ApiKeyValidator {
        <<interface>>
    }
    class FixedApiKeyValidator
    class ApiGateway
    ApiKeyValidator <|.. FixedApiKeyValidator
    ApiGateway --> ApiKeyValidator
```

## Real-world use cases

- Public HTTP APIs for partners (key in header or query).
- Server-to-server webhooks with a shared secret.
- Rate-limited developer portals issuing per-app keys.

## Run

```text
python -m transpiler run examples/patterns/authentication/api_key.pys
```
