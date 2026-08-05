from array import array
def _pys_format(value):
    return "null" if value is None else str(value)
for _pys_b1_i in range(0, 3):
    print(_pys_format(_pys_b1_i))
counter = 0
while counter < 3:
    print(_pys_format(counter))
    counter += 1
items = array('i', [10, 20])
for _pys_b2_n in items:
    print(_pys_format(_pys_b2_n))
