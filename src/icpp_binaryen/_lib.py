"""Load the bundled libbinaryen with cffi in ABI mode (ffi.dlopen).

No compiled extension module: the same wheel works for every supported
Python version on its platform.
"""

import platform
from pathlib import Path
from typing import Any, cast

from cffi import FFI

from icpp_binaryen._cdef import CDEF
from icpp_binaryen.version import __version__

LIB_DIR = Path(__file__).parent / "lib"

ffi = FFI()
ffi.cdef(CDEF)


def _lib_path() -> Path:
    system = platform.system()
    if system == "Darwin":
        return LIB_DIR / "libbinaryen.dylib"
    if system == "Linux":
        return LIB_DIR / "libbinaryen.so"
    raise ImportError(
        f"icpp-binaryen does not support platform '{system}'. "
        "Supported: macOS and Linux (on Windows, use WSL)."
    )


_path = _lib_path()
if not _path.exists():
    raise ImportError(
        f"icpp-binaryen: bundled library not found at {_path}. "
        "In a source checkout, run `make get-binaryen` first."
    )

lib = cast(Any, ffi.dlopen(str(_path)))

BINARYEN_VERSION: int = int(
    (LIB_DIR / "version.txt").read_text(encoding="utf-8").strip()
)
_expected = int(__version__.split(".", maxsplit=1)[0])
if BINARYEN_VERSION != _expected:
    raise ImportError(
        f"icpp-binaryen {__version__} expects bundled Binaryen {_expected}, "
        f"but lib/version.txt says {BINARYEN_VERSION}"
    )

# Binaryen's Allocate-and-write APIs return malloc'ed buffers that the caller
# must free. In ABI mode free() is not a libbinaryen symbol, so take it from
# the process' libc.
_ffi_libc = FFI()
_ffi_libc.cdef("void free(void *ptr);")
libc = cast(Any, _ffi_libc.dlopen(None))
