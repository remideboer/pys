def _pys_format(value):
    return "null" if value is None else str(value)
x = 1
if not (x == 0):
    print(_pys_format("nz"))
elif not (x > 10):
    print(_pys_format("small"))
else:
    print(_pys_format("other"))
