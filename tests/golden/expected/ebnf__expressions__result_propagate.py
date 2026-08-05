class _PysResult:
    __slots__ = ("_pys_result_kind", "value", "sites")

    def __init__(self, kind, value, sites=None):
        self._pys_result_kind = kind
        self.value = value
        self.sites = list(sites or ())

    def __repr__(self):
        return f"{self._pys_result_kind}({self.value!r})"


class _PysPropagateSignal(BaseException):
    __slots__ = ("result",)

    def __init__(self, result):
        self.result = result


def _pys_ok(value=None):
    return _PysResult("ok", value)


def _pys_err(value):
    return _PysResult("err", value)


def _pys_propagate(result, file, line, function):
    kind = getattr(result, "_pys_result_kind", None)
    if kind == "ok":
        return result.value
    if kind != "err":
        raise TypeError("propagate expected a PYS result value")
    sites = [*result.sites, (file, line, function)]
    raise _PysPropagateSignal(_PysResult("err", result.value, sites))


def _pys_panic(result):
    import sys as _pys_sys
    print(f"PYS panic: {result.value}", file=_pys_sys.stderr)
    for file, line, function in result.sites:
        print(f"  at {file}:{line} in {function}", file=_pys_sys.stderr)
    raise SystemExit(1)
def _pys_format(value):
    return "null" if value is None else str(value)
def readNumber(valid):
    try:
        if valid == False:
            return _pys_err("invalid")
        return _pys_ok(4)
    except _PysPropagateSignal as _pys_signal:
        return _pys_signal.result

def addOne(valid):
    try:
        value = _pys_propagate(readNumber(valid), '<memory>', 9, 'addOne')
        return _pys_ok(value + 1)
    except _PysPropagateSignal as _pys_signal:
        return _pys_signal.result

outcome = addOne(True)
_pys_result_0 = outcome
if _pys_result_0._pys_result_kind == 'ok':
    _pys_b1_value = _pys_result_0.value
    print(_pys_format(_pys_b1_value))
elif _pys_result_0._pys_result_kind == 'err':
    _pys_b2_error = _pys_result_0.value
    print(_pys_format(_pys_b2_error))
