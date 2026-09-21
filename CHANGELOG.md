# Changelog

## 116.0.1 (2026-09-21)

- **Fix the macOS wheel tags.** 116.0.0 tagged both macOS wheels
  `..._universal2`, but each bundles the single-arch libbinaryen downloaded
  for the runner it was built on. pip could not tell them apart and resolved
  on the macOS version alone, handing the arm64 dylib to Intel macs:
  `incompatible architecture (have 'arm64', need 'x86_64')`. The wheels are
  now tagged `macosx_10_14_x86_64` and `macosx_11_0_arm64`. Intel macOS users
  of 116.0.0 must upgrade; no API change.
- `make pypi-build` now verifies that every wheel's platform tag matches the
  architecture of the library inside it (`scripts/check_wheel_arch.py`), so a
  tag that misdescribes its payload can no longer be published.

## 116.0.0 (2026-09-21)

- Initial release, bundling official Binaryen 116 (macOS x86_64/arm64
  dylibs as-is; Linux x86_64 relinked from the official static archive).
- `fix_globals_limit`: the IC globals-limit fix (IC0505) with `_before_opt`
  backup and before/after report.
- `Module`: load / inspect / optimize / emit / write wrapper.
- `ffi` / `lib`: raw cffi ABI-mode escape hatch over a hand-curated
  `binaryen-c.h` subset.
- Byte-identical parity with `binaryen.py==0.0.2` output, verified on a real
  `llama_cpp_before_opt.wasm` artifact (see `test/parity/golden-116.json`).
