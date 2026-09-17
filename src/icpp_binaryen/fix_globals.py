"""The one high-level entry point: the IC globals-limit fix.

The Internet Computer rejects a wasm module with more than 1000 *defined*
globals (install error IC0505). A wasi-sdk build of a large C++ project blows
past this. The fix: remove every export of kind global (an exported global is
otherwise kept alive), then run Binaryen's optimizer, which drops the now-dead
globals.
"""

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Union

from icpp_binaryen.module import Module


@dataclass(frozen=True)
class GlobalsFixReport:
    """Before/after counts of a fix_globals_limit run."""

    wasm_path: Path
    backup_path: Path
    exports_before: int
    exports_after: int
    globals_before: int
    globals_after: int

    def summary(self) -> str:
        """The 4-line summary optimize_wasm.py prints today."""
        return (
            f"Exports before optimization: {self.exports_before}\n"
            f"Exports after  optimization: {self.exports_after}\n"
            f"Globals before optimization: {self.globals_before}\n"
            f"Globals after  optimization: {self.globals_after}"
        )


def fix_globals_limit(
    wasm_path: Union[Path, str], *, backup_suffix: str = "_before_opt"
) -> GlobalsFixReport:
    """Rewrite the wasm at wasm_path in place, keeping a backup copy.

    The backup (default `<stem>_before_opt.wasm`) is a byte-identical copy of
    the input: the optimize pass strips the wasm name section, and the backup
    is what keeps named backtraces possible (e.g. under wasmtime).
    """
    path = Path(wasm_path).resolve()
    backup_path = path.with_name(path.stem + backup_suffix + path.suffix)
    shutil.copy(path, backup_path)

    with Module.load(path) as module:
        exports_before = module.num_exports
        globals_before = module.num_globals

        # Two passes: removing while iterating would invalidate the indices.
        for name in module.global_export_names():
            module.remove_export(name)

        # Levels 0/0: this is an export-strip + dead-global removal, not a
        # size optimization.
        module.optimize(shrink_level=0, optimize_level=0)

        exports_after = module.num_exports
        globals_after = module.num_globals
        module.write(path)

    return GlobalsFixReport(
        wasm_path=path,
        backup_path=backup_path,
        exports_before=exports_before,
        exports_after=exports_after,
        globals_before=globals_before,
        globals_after=globals_after,
    )
