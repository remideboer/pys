from abc import ABC, abstractmethod
# Curated OO + control sample (no MySQL / no sibling vehicle imports)
x = 10
y = 20
print(f"x={x} y={y}")
for i in range(0, 2):
    print(i)

if x < y:
    print("lt")
else:
    print("ge")

def mul(a, b):
    return a * b

print(mul(3, 4))
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
print(p.label())
