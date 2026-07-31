from abc import ABC, abstractmethod
class Startable(ABC):
    @abstractmethod
    def start(self):
        pass

class Car(Startable):
    name = ''
    def __init__(self, name=''):
        self.name = name

    def start(self):
        print(f"{self.name} start")

c = Car("Dacia")
c.start()
s = c
s.start()
