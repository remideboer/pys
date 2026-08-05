def _pys_format(value):
    return "null" if value is None else str(value)
# line comment only
print(_pys_format(1))
print(_pys_format(2))
