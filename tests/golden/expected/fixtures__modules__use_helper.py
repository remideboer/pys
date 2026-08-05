def _pys_format(value):
    return "null" if value is None else str(value)
from helper import *
v = double(21)
print(_pys_format(v))
