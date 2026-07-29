"""Runtime helpers for PYS tasks / await / shared (reference; codegen inlines a preamble)."""

from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from threading import Event, Lock
from typing import Any, Callable


class PysShared:
    """Locked cell for `shared` variables mutated across tasks."""

    __slots__ = ("value", "_lock")

    def __init__(self, value: Any) -> None:
        self.value = value
        self._lock = Lock()

    def set(self, value: Any) -> Any:
        with self._lock:
            self.value = value
            return value

    def iadd(self, delta: Any) -> Any:
        with self._lock:
            self.value += delta
            return self.value

    def isub(self, delta: Any) -> Any:
        with self._lock:
            self.value -= delta
            return self.value


def pys_await(value: Any) -> Any:
    if isinstance(value, Future):
        return value.result()
    result = getattr(value, "result", None)
    if callable(result):
        return result()
    return value


class PysTaskGroup:
    """Autos start on run(); parameterized templates via call(name, *args)."""

    def __init__(self) -> None:
        self.futures: dict[str, Future] = {}
        self.templates: dict[str, Callable[..., Any]] = {}
        self._autos: dict[str, Callable[[], Any]] = {}
        self._pending: list[Future] = []
        self._pool: ThreadPoolExecutor | None = None
        self._gate = Event()
        self._lock = Lock()

    def add_auto(self, name: str, fn: Callable[[], Any]) -> None:
        self._autos[name] = fn

    def add_template(self, name: str, fn: Callable[..., Any]) -> None:
        self.templates[name] = fn

    def call(self, name: str, *args: Any) -> Future:
        fn = self.templates.get(name)
        if fn is None:
            raise NameError(f"unknown task template {name!r}")

        def _run(fn: Callable[..., Any] = fn, args: tuple[Any, ...] = args) -> Any:
            self._gate.wait()
            return fn(*args)

        assert self._pool is not None
        fut = self._pool.submit(_run)
        with self._lock:
            self._pending.append(fut)
        return fut

    def run(self) -> None:
        workers = max(1, len(self._autos) + max(len(self.templates), 1))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            self._pool = pool
            for name, fn in self._autos.items():

                def _run(fn: Callable[[], Any] = fn) -> Any:
                    self._gate.wait()
                    return fn()

                fut = pool.submit(_run)
                self.futures[name] = fut
                with self._lock:
                    self._pending.append(fut)
            self._gate.set()
            while True:
                with self._lock:
                    batch = list(self._pending)
                    self._pending.clear()
                if not batch:
                    break
                done, not_done = wait(batch, return_when=FIRST_COMPLETED)
                with self._lock:
                    self._pending.extend(not_done)
                for fut in done:
                    fut.result()
