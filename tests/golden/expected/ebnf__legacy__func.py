def _pys_format(value):
    return "null" if value is None else str(value)
def greet(name):
    print(_pys_format(name))
greet("hi")
