"""Smoke tests: run against the INSTALLED icpp-binaryen package (wheel or
editable install) — import, end-to-end fix, wasmtime instantiation,
determinism."""

import re
from pathlib import Path
from typing import Callable

import wasmtime

from icpp_binaryen import BINARYEN_VERSION, __version__, fix_globals_limit, lib

EXPECTED_BINARYEN_VERSION = 116


def test_import_and_version() -> None:
    assert BINARYEN_VERSION == EXPECTED_BINARYEN_VERSION
    assert re.fullmatch(r"\d+\.\d+\.\d+(rc\d+)?", __version__)
    assert int(__version__.split(".", maxsplit=1)[0]) == BINARYEN_VERSION
    assert callable(lib.BinaryenModuleRead)


def test_end_to_end(
    tmp_path: Path,
    fixture_wasm_bytes: bytes,
    has_name_section: Callable[[bytes], bool],
) -> None:
    wasm_path = tmp_path / "module.wasm"
    wasm_path.write_bytes(fixture_wasm_bytes)

    report = fix_globals_limit(wasm_path)
    assert report.globals_after < report.globals_before

    # The _before_opt copy keeps its name section (named backtraces contract)
    assert has_name_section(report.backup_path.read_bytes())

    # The optimized wasm instantiates and runs under wasmtime
    engine = wasmtime.Engine()
    store = wasmtime.Store(engine)
    module = wasmtime.Module(engine, wasm_path.read_bytes())
    instance = wasmtime.Instance(store, module, [])
    sum_func = instance.exports(store)["sum"]
    assert isinstance(sum_func, wasmtime.Func)
    assert sum_func(store) == 1  # g0 + g1 = 0 + 1


def test_determinism(tmp_path: Path, fixture_wasm_bytes: bytes) -> None:
    outputs = []
    for i in range(2):
        wasm_path = tmp_path / f"run{i}.wasm"
        wasm_path.write_bytes(fixture_wasm_bytes)
        fix_globals_limit(wasm_path)
        outputs.append(wasm_path.read_bytes())
    assert outputs[0] == outputs[1]
