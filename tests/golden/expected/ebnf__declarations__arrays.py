from array import array
def _pys_format(value):
    return "null" if value is None else str(value)
numbers = array('i', [1, 2, 3, 4, 5])
primes = array('i', [2, 3, 5])
print(_pys_format(numbers[0]))
print(_pys_format(primes[1]))
