# Changelog

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
