def _pys_format(value):
    return "null" if value is None else str(value)
print(_pys_format(42))
print(_pys_format(True))
print(_pys_format(False))
print(_pys_format(None))
f = 3.14
c = 'A'
s = "hello"
print(_pys_format(f))
print(_pys_format(c))
print(_pys_format(s))
