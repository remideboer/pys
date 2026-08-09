"""JavaScript runtime helpers for shared / atomic / tasks / await.

Cooperative (same-thread) task group: ``await`` of a sibling auto-task
runs that task to completion via a trampoline. True OS-thread races are
not simulated — shared counter demos may always show the sequential total.
Atomic RMW stays indivisible on the single thread.
"""

JS_CONCURRENCY_PREAMBLE = r"""
class _PysShared {
  constructor(value) { this.value = value; }
  set(value) { this.value = value; return value; }
  iadd(delta) { this.value += delta; return this.value; }
  isub(delta) { this.value -= delta; return this.value; }
}
class _PysAtomic {
  constructor(value) { this._value = value; }
  get() { return this._value; }
  set(value) { this._value = value; return value; }
  iadd(delta) { this._value += delta; return this._value; }
  isub(delta) { this._value -= delta; return this._value; }
  compareAndSet(expected, newValue) {
    if (this._value === expected) { this._value = newValue; return true; }
    return false;
  }
}
function _pys_await(value) {
  if (value == null) return value;
  if (typeof value.result === "function") return value.result();
  return value;
}
class _PysTaskGroup {
  constructor() {
    this.futures = {};
    this.templates = {};
    this._autos = {};
    this._status = {};
  }
  add_auto(name, fn) { this._autos[name] = fn; }
  add_template(name, fn) { this.templates[name] = fn; }
  call(name, ...args) {
    const fn = this.templates[name];
    if (!fn) throw new Error("unknown task template " + JSON.stringify(name));
    const value = fn(...args);
    return { result: () => value };
  }
  _ensure(name) {
    const st = this._status[name];
    if (!st) throw new Error("unknown task " + JSON.stringify(name));
    if (st.done) return st.value;
    if (st.running) throw new Error("task deadlock on " + JSON.stringify(name));
    st.running = true;
    try {
      st.value = st.fn();
      st.done = true;
      return st.value;
    } finally {
      st.running = false;
    }
  }
  run() {
    for (const [name, fn] of Object.entries(this._autos)) {
      this._status[name] = { done: false, running: false, fn, value: undefined };
      const self = this;
      this.futures[name] = { result: () => self._ensure(name) };
    }
    for (const name of Object.keys(this._autos)) {
      this._ensure(name);
    }
  }
}
"""

JS_VALUE_HELPERS = r"""
function _pys_struct_copy(value) {
  if (value != null && typeof value._pys_copy === "function") return value._pys_copy();
  return value;
}
function _pys_value_eq(a, b) {
  if (a === b) return true;
  if (a != null && typeof a.equals === "function") return a.equals(b);
  return false;
}
function _pys_to_base(value, width, radix, name) {
  const n = Number(value);
  if (!Number.isFinite(n) || !Number.isInteger(n) || n < 0) {
    throw new Error(name + " requires a non-negative integer");
  }
  let digits = n.toString(radix);
  if (width != null && width !== undefined) {
    const w = Number(width);
    if (!Number.isInteger(w) || w < 1) {
      throw new Error(name + " width must be an integer >= 1");
    }
    digits = digits.padStart(w, "0");
  }
  return digits;
}
function _pys_to_bin(value, width) { return _pys_to_base(value, width, 2, "toBin"); }
function _pys_to_hex(value, width) { return _pys_to_base(value, width, 16, "toHex"); }
function _pys_to_oct(value, width) { return _pys_to_base(value, width, 8, "toOct"); }
function _pys_panic(result) {
  const msg = result && result.value !== undefined ? result.value : result;
  console.error("PYS panic: " + _pys_format(msg));
  if (result && Array.isArray(result.sites)) {
    for (const site of result.sites) {
      console.error("  at " + site[0] + ":" + site[1] + " in " + site[2]);
    }
  }
  process.exit(1);
}
"""
