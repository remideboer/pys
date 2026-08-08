# Proxy

**Category:** Structural  
**Demo:** [proxy.pys](proxy.pys)  
**Wikipedia:** [Proxy pattern](https://en.wikipedia.org/wiki/Proxy_pattern) · [Design Patterns (book)](https://en.wikipedia.org/wiki/Design_Patterns)

## Intent

Provide a surrogate or placeholder for another object to control access to it.

## Explanation

`ImageProxy` implements `Image` and creates `RealImage` only on first `display` (virtual / lazy proxy). Other proxy kinds add access control, remote stubs, or logging — same shape, different reason.

## Classic structure (UML)

```mermaid
classDiagram
    class Subject {
        <<interface>>
        +request()
    }
    class RealSubject
    class Proxy
    class Client
    Subject <|.. RealSubject
    Subject <|.. Proxy
    Proxy --> RealSubject
    Client --> Subject
```

## This demo

`Image` is Subject; `RealImage` is RealSubject; `ImageProxy` is Proxy and holds a nullable real image until needed.

```mermaid
classDiagram
    class Image {
        <<interface>>
    }
    class RealImage
    class ImageProxy
    Image <|.. RealImage
    Image <|.. ImageProxy
    ImageProxy --> RealImage
```

## Real-world use cases

- Lazy-loading images or large documents until first paint.
- Protection proxies enforcing permissions before calling a service.
- Remote proxies / stubs that forward calls across a network.

## Run

```text
python -m transpiler run examples/patterns/design/structural/proxy.pys
```
