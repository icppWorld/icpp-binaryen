"""Pythonic wrapper around the raw Binaryen C API (read / inspect / optimize /
emit). The raw `ffi` / `lib` pair stays available as the escape hatch."""

from pathlib import Path
from types import TracebackType
from typing import Any, Optional, Union

from icpp_binaryen._lib import ffi, lib, libc


class Module:
    """A Binaryen module handle."""

    def __init__(self, ref: Any, keepalive: Any = None) -> None:
        # keepalive holds the cffi buffer BinaryenModuleRead parsed from:
        # the C API takes a non-const char* and the buffer must outlive the
        # module.
        self._ref: Any = ref
        self._keepalive = keepalive

    @classmethod
    def read(cls, wasm_bytes: bytes) -> "Module":
        """Construct a Module from wasm bytes."""
        buf = ffi.new("char[]", wasm_bytes)
        ref = lib.BinaryenModuleRead(buf, len(wasm_bytes))
        if ref == ffi.NULL:
            raise ValueError("BinaryenModuleRead failed to parse the wasm")
        return cls(ref, keepalive=buf)

    @classmethod
    def load(cls, wasm_path: Union[Path, str]) -> "Module":
        """Construct a Module from a wasm file."""
        return cls.read(Path(wasm_path).read_bytes())

    @property
    def ref(self) -> Any:
        """The raw BinaryenModuleRef, for use with `lib` directly."""
        return self._ref

    @property
    def num_exports(self) -> int:
        """Number of exports of any kind."""
        return int(lib.BinaryenGetNumExports(self._ref))

    @property
    def num_globals(self) -> int:
        """Number of *defined* globals (what the IC's 1000 limit counts)."""
        return int(lib.BinaryenGetNumGlobals(self._ref))

    def global_export_names(self) -> list[str]:
        """Names of all exports of kind global."""
        kind_global = lib.BinaryenExternalGlobal()
        names: list[str] = []
        for i in range(self.num_exports):
            export_ref = lib.BinaryenGetExportByIndex(self._ref, i)
            if lib.BinaryenExportGetKind(export_ref) == kind_global:
                name = ffi.string(lib.BinaryenExportGetName(export_ref))
                if isinstance(name, bytes):
                    name = name.decode("utf-8")
                names.append(name)
        return names

    def remove_export(self, external_name: str) -> None:
        """Remove the export with the given external name."""
        lib.BinaryenRemoveExport(self._ref, external_name.encode("utf-8"))

    def optimize(self, shrink_level: int, optimize_level: int) -> None:
        """Run Binaryen's default optimization pipeline at the given levels.

        Note: the optimizer strips the wasm name section — keep a copy of the
        input when named backtraces matter.
        """
        lib.BinaryenSetShrinkLevel(shrink_level)
        lib.BinaryenSetOptimizeLevel(optimize_level)
        lib.BinaryenModuleOptimize(self._ref)

    def validate(self) -> bool:
        """Run Binaryen validation on the module."""
        return bool(lib.BinaryenModuleValidate(self._ref))

    def emit(self) -> bytes:
        """Serialize the module to wasm bytes."""
        result = lib.BinaryenModuleAllocateAndWrite(self._ref, ffi.NULL)
        try:
            return bytes(ffi.buffer(result.binary, result.binaryBytes))
        finally:
            libc.free(result.binary)
            if result.sourceMap != ffi.NULL:
                libc.free(result.sourceMap)

    def write(self, wasm_path: Union[Path, str]) -> None:
        """Serialize the module to a wasm file."""
        Path(wasm_path).write_bytes(self.emit())

    def dispose(self) -> None:
        """Free the Binaryen module; safe to call more than once."""
        if self._ref is not None:
            lib.BinaryenModuleDispose(self._ref)
            self._ref = None
            self._keepalive = None

    def __enter__(self) -> "Module":
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        self.dispose()

    def __del__(self) -> None:
        try:
            self.dispose()
        except Exception:  # pylint: disable = broad-exception-caught
            pass  # interpreter shutdown: lib may already be unloaded
