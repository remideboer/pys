from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait as _pys_wait
from threading import Event as _PysEvent, Lock as _PysLock

class _PysShared:
    __slots__ = ("value", "_lock")
    def __init__(self, value):
        self.value = value
        self._lock = _PysLock()
    def set(self, value):
        with self._lock:
            self.value = value
            return value
    def iadd(self, delta):
        with self._lock:
            self.value += delta
            return self.value
    def isub(self, delta):
        with self._lock:
            self.value -= delta
            return self.value

class _PysAtomic:
    """Lock-backed indivisible get / set / iadd / isub / compareAndSet."""
    __slots__ = ("_value", "_lock")
    def __init__(self, value):
        self._value = value
        self._lock = _PysLock()
    def get(self):
        with self._lock:
            return self._value
    def set(self, value):
        with self._lock:
            self._value = value
            return value
    def iadd(self, delta):
        with self._lock:
            self._value += delta
            return self._value
    def isub(self, delta):
        with self._lock:
            self._value -= delta
            return self._value
    def compareAndSet(self, expected, new_value):
        with self._lock:
            if self._value == expected:
                self._value = new_value
                return True
            return False

def _pys_await(value):
    if isinstance(value, Future):
        return value.result()
    result = getattr(value, "result", None)
    if callable(result):
        return result()
    return value

class _PysTaskGroup:
    """Autos start on run(); parameterized templates via call(name, *args)."""
    def __init__(self):
        self.futures = {}
        self.templates = {}
        self._autos = {}
        self._pending = []
        self._pool = None
        self._gate = _PysEvent()
        self._lock = _PysLock()

    def add_auto(self, name, fn):
        self._autos[name] = fn

    def add_template(self, name, fn):
        self.templates[name] = fn

    def call(self, name, *args):
        fn = self.templates.get(name)
        if fn is None:
            raise NameError("unknown task template %r" % (name,))
        def _run(fn=fn, args=args):
            self._gate.wait()
            return fn(*args)
        fut = self._pool.submit(_run)
        with self._lock:
            self._pending.append(fut)
        return fut

    def run(self):
        workers = max(1, len(self._autos) + max(len(self.templates), 1))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            self._pool = pool
            for name, fn in self._autos.items():
                def _run(fn=fn):
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
                done, not_done = _pys_wait(batch, return_when=FIRST_COMPLETED)
                with self._lock:
                    self._pending.extend(not_done)
                for fut in done:
                    fut.result()

counter = _PysShared(0)
if True:
    _pys_tg_0 = _PysTaskGroup()
    def __pys_task__anon_1():
        counter.set(counter.value + 1)
    _pys_tg_0.add_auto('_anon_1', __pys_task__anon_1)
    def __pys_task__anon_2():
        counter.set(counter.value + 1)
    _pys_tg_0.add_auto('_anon_2', __pys_task__anon_2)
    _pys_tg_0.run()
print(counter.value)
