# Request–reply

**Category:** Messaging  
**Demo:** [request_reply.pys](request_reply.pys)  
**Wikipedia / ref:** [Request–reply](https://www.enterpriseintegrationpatterns.com/patterns/messaging/RequestReply.html)

## Intent

Correlation id ties a reply to its request.

## Prompting an AI

**Say this:** “Mailbox expect(correlationId); accept only matching replies.”

**Not this:** “Assume message order without correlation ids.”

**Confusion to avoid:** Request–reply ≠ pub-sub broadcast.

## Run

```text
python -m transpiler run examples/patterns/messaging/request_reply.pys
```
