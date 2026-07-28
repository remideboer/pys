from pathlib import Path
from transpiler.transpiler import transpile
p = Path('examples/hello.pys')
print('Transpiling', p)
text = p.read_text(encoding='utf-8')
print('\n--- PYS source ---\n')
print(text)
print('\n--- Generated Python ---\n')
print(transpile(text))
