def _pys_format(value):
    return "null" if value is None else str(value)
x = 10
y = 2.5
z = 30
MAX = 100
fixed = 1 + 2
print(_pys_format(x))
print(_pys_format(y))
print(_pys_format(z))
print(_pys_format(MAX))
print(_pys_format(fixed))
