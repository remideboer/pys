def _pys_format(value):
    return "null" if value is None else str(value)
msg = "café"
print(_pys_format(msg))
