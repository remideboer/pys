# JIT — Functions and imports

## Function forms

```pys
global function hello() {
    print("hi")
}

package function greet(string name) {
    print("hi #s{name}")
}

function hidden() {
    print("module only")
}
```

## Import forms

```pys
import toolbox
import greet from toolbox
import all from toolbox
import math
import tkinter as tk
```

`.pys` modules: local file / same-folder discovery.  
Python packages: stdlib or `pys.deps`. Alias `as` is for those packages.

**All imports first** in the file (before declarations/statements) —
[J-member-order](J-member-order.md).

## Visibility quick map

| Keyword on export | Who can import it |
|-------------------|-------------------|
| default | nobody outside the file |
| `package` | same folder |
| `global` | anywhere |

Model: [S3](../supportive/S3-visibility-and-modules.md)
