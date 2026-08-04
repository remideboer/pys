# examples/webserver deferred remaining work

Remaining full-spec items are tracked as [F-007](../../docs/TODO-FUTURE.md#f-007-webserver-full-spec-remainder).
Implementation is **halted** until [F-006](../../docs/TODO-FUTURE.md#f-006-source-roots-and-same-package-tests)
(package resolution / source roots) lands; then this tree is refactored to
`src/` + `tests/` mirrored packages.

Shipped teaching increments 1–6 stay as the working baseline (pool, breaker,
HTTP/1.1 keep-alive, TLS, HTTP/2, timeouts, k6 subsets).
