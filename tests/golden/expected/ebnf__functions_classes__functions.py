def _pys_format(value):
    return "null" if value is None else str(value)
def add(a, b):
    return a + b
def greet(name):
    print(_pys_format(name))
def secret():
    print(_pys_format("priv"))
s = add(1, 2)
print(_pys_format(s))
greet("hi")
secret()
