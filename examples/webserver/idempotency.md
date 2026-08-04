# Idempotency classification (§5). Version with endpoint changes (PR5).
# Unclassified endpoints default to Unsafe / no retry (PR1).

| Endpoint | Idempotent by method? | Idempotent in practice? | Mechanism | Retry classification | Downstream side effects |
|---|---|---|---|---|---|
| `GET /health` | Yes | Yes | Natural | Safe | None |
| `GET /proxy/data` | Yes | Yes | Natural | Safe | Downstream GET (read-only) |
| `GET /proxy/slow` | Yes | Yes | Natural | Safe | Downstream GET with injected latency (load demos) |
| `GET /proxy/b` | Yes | Yes | Natural | Safe | Downstream B GET (bulkhead B) |
| `POST /orders` | No | No | None | Unsafe | Create order (write) |
| `GET /metrics` | Yes | Yes | Natural | Safe | None |
