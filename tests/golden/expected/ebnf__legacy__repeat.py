def _pys_format(value):
    return "null" if value is None else str(value)
for _ in range(3):
    print(_pys_format("hi"))
