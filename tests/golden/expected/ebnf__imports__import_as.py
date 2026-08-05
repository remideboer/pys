def _pys_format(value):
    return "null" if value is None else str(value)
import tkinter as tk
print(_pys_format(tk))
