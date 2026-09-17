"""Shared fixtures for the icpp-binaryen unit & smoke test suites."""

from pathlib import Path
from typing import Callable

import pytest
import wasmtime

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _leb128(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _name_section(module_name: str) -> bytes:
    """A minimal wasm `name` custom section (module-name subsection only)."""
    sub_payload = _leb128(len(module_name)) + module_name.encode("utf-8")
    subsection = bytes([0]) + _leb128(len(sub_payload)) + sub_payload
    payload = _leb128(4) + b"name" + subsection
    return bytes([0]) + _leb128(len(payload)) + payload


def _target_features_section(*features: str) -> bytes:
    """A wasm `target_features` custom section, as wasi-sdk builds carry it.

    Binaryen applies it to the module's feature set on read; without it the
    fixture's exported mutable globals would be invalid under bare MVP.
    """
    payload = _leb128(len(features))
    for feature in features:
        payload += b"+" + _leb128(len(feature)) + feature.encode("utf-8")
    body = _leb128(len("target_features")) + b"target_features" + payload
    return bytes([0]) + _leb128(len(body)) + body


def _read_leb128(wasm: bytes, i: int) -> tuple[int, int]:
    value, shift = 0, 0
    while True:
        byte = wasm[i]
        i += 1
        value |= (byte & 0x7F) << shift
        shift += 7
        if not byte & 0x80:
            return value, i


def _has_name_section(wasm: bytes) -> bool:
    assert wasm[:4] == b"\x00asm"
    i = 8
    while i < len(wasm):
        sec_id = wasm[i]
        i += 1
        size, i = _read_leb128(wasm, i)
        if sec_id == 0:
            name_len, j = _read_leb128(wasm, i)
            if wasm[j : j + name_len] == b"name":
                return True
        i += size
    return False


@pytest.fixture(scope="session")
def fixture_wasm_bytes() -> bytes:
    """globals.wat compiled to wasm, with a name section appended (the wat
    compiler emits none, and the name-section contract is part of the API)."""
    wat = (FIXTURES_DIR / "globals.wat").read_text(encoding="utf-8")
    wasm = wasmtime.wat2wasm(wat)
    return (
        bytes(wasm)
        + _target_features_section("mutable-globals")
        + _name_section("globals_fixture")
    )


@pytest.fixture(scope="session")
def has_name_section() -> Callable[[bytes], bool]:
    """Predicate: does the wasm binary contain a `name` custom section?"""
    return _has_name_section
