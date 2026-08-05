def _pys_format(value):
    return "null" if value is None else str(value)
x = 1
if x > 0:
    print(_pys_format("pos"))
else:
    print(_pys_format("nonpos"))
