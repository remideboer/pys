from abc import ABC, abstractmethod
def _pys_format(value):
    return "null" if value is None else str(value)
class Startable(ABC):
    @abstractmethod
    def start(self):
        pass

class Car(Startable):
    name = ''
    def __init__(self, name=''):
        self.name = name

    def start(self):
        print(_pys_format(f"{_pys_format(self.name)} start"))

c = Car("Dacia")
c.start()
s = c
s.start()
