"""icpp-binaryen: cffi bindings over Binaryen's C API, with the official
Binaryen shared library bundled per platform.

Public API — all of it:

    from icpp_binaryen import ffi, lib          # raw escape hatch
    from icpp_binaryen import Module            # load / optimize / emit / write
    from icpp_binaryen import fix_globals_limit # the IC globals-limit fix
    from icpp_binaryen import BINARYEN_VERSION  # int, from bundled version.txt
"""

from icpp_binaryen.version import __version__
from icpp_binaryen._lib import BINARYEN_VERSION, ffi, lib
from icpp_binaryen.module import Module
from icpp_binaryen.fix_globals import GlobalsFixReport, fix_globals_limit

__all__ = [
    "BINARYEN_VERSION",
    "GlobalsFixReport",
    "Module",
    "__version__",
    "ffi",
    "fix_globals_limit",
    "lib",
]
