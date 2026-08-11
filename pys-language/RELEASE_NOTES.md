# PYS Language Support 0.0.104

## Fix: `Type.method()` highlighting

- Method declarations required a return type to be followed by whitespace, so
  `greet()` is no longer split into type `gree` + method `t`.
- Call sites `Character.greet()` use class color on the type and function color
  on the method (`meta.method-call.static.pys`).

## Install

Package/install the VSIX or run `install-extension.bat`, then **Reload Window**.
