def _pys_format(value):
    return "null" if value is None else str(value)
x = 10
y = 20
if x < y:
    print(_pys_format("lt"))
elif x == y:
    print(_pys_format("eq"))
else:
    print(_pys_format("gt"))
if not (x > 100):
    print(_pys_format("unless"))
if not (x > 100):
    print(_pys_format("ifnot"))
