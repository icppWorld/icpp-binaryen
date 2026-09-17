"""Unit tests for the raw lib and the Module wrapper."""

from icpp_binaryen import BINARYEN_VERSION, Module, lib

EXPECTED_BINARYEN_VERSION = 116


def test_lib_loads() -> None:
    assert BINARYEN_VERSION == EXPECTED_BINARYEN_VERSION
    assert callable(lib.BinaryenModuleRead)


def test_module_inspection(fixture_wasm_bytes: bytes) -> None:
    with Module.read(fixture_wasm_bytes) as module:
        assert module.num_exports == 9  # memory + sum + bump + g2..g7
        assert module.num_globals == 8  # g0..g7
        assert module.global_export_names() == ["g2", "g3", "g4", "g5", "g6", "g7"]
        assert module.validate()


def test_emit_roundtrip(fixture_wasm_bytes: bytes) -> None:
    with Module.read(fixture_wasm_bytes) as module:
        wasm = module.emit()
    assert wasm[:4] == b"\x00asm"
    with Module.read(wasm) as module:
        assert module.num_exports == 9


def test_remove_exports_and_optimize(fixture_wasm_bytes: bytes) -> None:
    with Module.read(fixture_wasm_bytes) as module:
        for name in module.global_export_names():
            module.remove_export(name)
        module.optimize(shrink_level=0, optimize_level=0)
        assert module.num_exports == 3  # memory + sum + bump
        assert module.num_globals == 2  # only g0, g1 (used by sum) survive
        assert module.validate()
