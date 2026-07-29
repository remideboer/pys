"""Runtime helpers for PYS tasks / await / shared (reference; codegen inlines a preamble)."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, wait
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
    """Wait until a task handle / Future is ready; pass other values through."""
    if isinstance(value, Future):
        return value.result()
    result = getattr(value, "result", None)
    if callable(result):
        return result()
    return value


def pys_run_tasks(fns: dict[str, Callable[[], Any]], futures: dict[str, Future]) -> None:
    """Submit all tasks (gated), then wait; sibling await uses the futures dict."""
    if not fns:
        return
    ready = Event()

    def _wrap(fn: Callable[[], Any]) -> Callable[[], Any]:
        def _inner() -> Any:
            ready.wait()
            return fn()

        return _inner

    with ThreadPoolExecutor(max_workers=max(1, len(fns))) as pool:
        for name, fn in fns.items():
            futures[name] = pool.submit(_wrap(fn))
        ready.set()
        done, _ = wait(futures.values())
        for fut in done:
            fut.result()
