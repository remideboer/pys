def _pys_format(value):
    return "null" if value is None else str(value)
a = 3
b = 5
print(_pys_format(a + b))
print(_pys_format("sum: " + str(a) + str(b)))
print(_pys_format(a > 1 and b < 10))
print(_pys_format(a < 1 or b > 1))
print(_pys_format(not (a == 0)))
f = 3.14
casted = int(f)
print(_pys_format(casted))
print(_pys_format(f"a is {_pys_format(a)}"))
print(_pys_format(f"{_pys_format(a)} typed"))
print(_pys_format(f"the # hash"))
