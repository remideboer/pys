from abc import ABC, abstractmethod
def _pys_format(value):
    return "null" if value is None else str(value)
# Curated OO + control sample (no MySQL / no sibling vehicle imports)
x = 10
y = 20
print(_pys_format(f"x={_pys_format(x)} y={_pys_format(y)}"))
for _pys_b1_i in range(0, 2):
    print(_pys_format(_pys_b1_i))

if x < y:
    print(_pys_format("lt"))
else:
    print(_pys_format("ge"))

def mul(a, b):
    return a * b

print(_pys_format(mul(3, 4)))
class Named(ABC):
    @abstractmethod
    def label(self):
        pass

class Point(Named):
    x = 0
    y = 0
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

    def label(self):
        return "({self.x},{self.y})"

p = Point(1, 2)
print(_pys_format(p.label()))
