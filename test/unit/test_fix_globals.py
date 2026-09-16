"""Unit tests for fix_globals_limit."""

from pathlib import Path
from typing import Callable

from icpp_binaryen import fix_globals_limit


def test_fix_globals_limit(
    tmp_path: Path,
    fixture_wasm_bytes: bytes,
    has_name_section: Callable[[bytes], bool],
) -> None:
    wasm_path = tmp_path / "module.wasm"
    wasm_path.write_bytes(fixture_wasm_bytes)

    report = fix_globals_limit(wasm_path)

    assert report.wasm_path == wasm_path
    assert report.backup_path == tmp_path / "module_before_opt.wasm"
    assert report.exports_before == 9
    assert report.exports_after == 3
    assert report.globals_before == 8
    assert report.globals_after == 2

    # The backup is a byte-identical copy of the input, name section included;
    # the optimized output loses the name section (documented side effect).
    backup = report.backup_path.read_bytes()
    assert backup == fixture_wasm_bytes
    assert has_name_section(backup)
    assert not has_name_section(wasm_path.read_bytes())


def test_summary_format(tmp_path: Path, fixture_wasm_bytes: bytes) -> None:
    wasm_path = tmp_path / "module.wasm"
    wasm_path.write_bytes(fixture_wasm_bytes)
    report = fix_globals_limit(wasm_path)
    # Same 4-line format llama_cpp_canister's optimize_wasm.py prints today
    assert report.summary() == (
        "Exports before optimization: 9\n"
        "Exports after  optimization: 3\n"
        "Globals before optimization: 8\n"
        "Globals after  optimization: 2"
    )


def test_custom_backup_suffix(tmp_path: Path, fixture_wasm_bytes: bytes) -> None:
    wasm_path = tmp_path / "module.wasm"
    wasm_path.write_bytes(fixture_wasm_bytes)
    report = fix_globals_limit(wasm_path, backup_suffix="_orig")
    assert report.backup_path == tmp_path / "module_orig.wasm"
    assert report.backup_path.exists()
