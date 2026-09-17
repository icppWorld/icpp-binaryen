# icpp-binaryen

[cffi](https://cffi.readthedocs.io/) bindings over
[Binaryen](https://github.com/WebAssembly/binaryen)'s C API, with the official
Binaryen shared library bundled per platform.

Built and maintained by [icppWorld](https://github.com/icppWorld) for the
[icpp-pro](https://docs.icpp.world) toolchain of the Internet Computer, and
usable by any project that needs Binaryen from Python.

## Why

The Internet Computer rejects a wasm module with more than 1000 *defined*
globals (install error `IC0505`). A wasi-sdk build of a large C++ project
blows past this. The fix: remove every export of kind global (an exported
global is otherwise kept alive), then run Binaryen's optimizer, which drops
the now-dead globals. `fix_globals_limit` does exactly that.

## Install

```bash
pip install icpp-binaryen
```

One wheel per platform (macOS x86_64 / arm64, Linux x86_64) covers every
Python version >= 3.11: the bindings use cffi in ABI mode, so there is no
compiled extension module. On Windows, use WSL.

## Public API — all of it

```python
from icpp_binaryen import fix_globals_limit  # the one high-level entry point
from icpp_binaryen import Module             # load / optimize / emit / write
from icpp_binaryen import ffi, lib           # raw escape hatch
from icpp_binaryen import BINARYEN_VERSION   # int, from the bundled version.txt
```

### fix_globals_limit

```python
from pathlib import Path
from icpp_binaryen import fix_globals_limit

report = fix_globals_limit(Path("build/my_canister.wasm"))
print(report.summary())
```

Rewrites the wasm in place and keeps a byte-identical backup copy (default
`<stem>_before_opt.wasm`). Returns a `GlobalsFixReport` with the
before/after counts of exports and defined globals.

Documented side effect: the optimize pass strips the wasm *name section*.
The `_before_opt` backup is what keeps named backtraces possible (e.g. under
wasmtime). This is by design — do not delete the backup pair.

### Module

```python
from icpp_binaryen import Module

with Module.load("my.wasm") as module:      # or Module.read(wasm_bytes)
    print(module.num_exports, module.num_globals)
    for name in module.global_export_names():
        module.remove_export(name)
    module.optimize(shrink_level=0, optimize_level=0)
    assert module.validate()
    module.write("my_fixed.wasm")           # or wasm_bytes = module.emit()
```

### ffi / lib

The raw ABI-mode cffi handles, for post-processing needs beyond the wrapper.
The cdef is a hand-curated subset of `binaryen-c.h` — see
`src/icpp_binaryen/_cdef.py` for what is available. `module.ref` hands you
the raw `BinaryenModuleRef` for use with `lib` directly.

## Versioning

`<binaryen>.<minor>.<patch>` — the major component IS the bundled Binaryen
version, asserted at import time. The wasm bytes this package emits are part
of its contract: minor/patch releases are byte-identical in
`fix_globals_limit` output; a Binaryen bump is a major release.

## Contributing

See [README-feature-guide.md](README-feature-guide.md) (the ceremony-based
development process) and
[README-release-guide.md](README-release-guide.md). Development setup:

```bash
conda create --name icpp-binaryen python=3.11
conda activate icpp-binaryen
make install-python
make get-binaryen        # fetch the official Binaryen lib for this platform
make all-tests
```

## Credits & license

Apache-2.0, like [Binaryen](https://github.com/WebAssembly/binaryen) itself.
The cffi-over-libbinaryen approach was inspired by
[jonathanharg/binaryen.py](https://github.com/jonathanharg/binaryen.py),
which this package replaces for the icpp-pro toolchain.
