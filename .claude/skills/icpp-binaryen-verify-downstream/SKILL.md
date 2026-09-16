---
name: icpp-binaryen-verify-downstream
description: Tiered verification of the downstream repos (llama_cpp_canister, icpp-pro) after an icpp-binaryen change — pick the tier from what changed, run the corresponding make targets
disable-model-invocation: false
user-invocable: true
---

# Verify the downstream repos

Read `README-feature-guide.md` Ceremony 4. Pick the tier from what changed
in icpp-binaryen, then run the target from the icpp-binaryen repo root:

| What changed                                                   | Run                                              |
|----------------------------------------------------------------|---------------------------------------------------|
| Internal only (no public API, no output-byte change possible)  | nothing (icpp-binaryen tests suffice)             |
| Public API surface (signatures, `Module`, `fix_globals_limit`) | `make downstream-verify-api`                      |
| Anything that could touch emitted bytes (cdef, lib, passes)    | `make parity-test` + `make downstream-verify-api` |
| Bundled Binaryen bump, or release                              | `make downstream-verify-full`                     |

What the targets do:

- `downstream-verify-api` = install this tree's wheel into the
  `../llama_cpp_canister` env, run its optimize path + model-free API suite
  (`test/test_canister_functions.py`). From Phase 2 on it adds the icpp-pro
  `make all-tests` leg. NOTE: llama's native leg needs an x86_64 host (ggml
  `arch/x86/` sources are hard-coded in its icpp.toml); on an arm64 Mac rely
  on llama's CI or docker path for that leg.
- `downstream-verify-full` = the above + the wasm-hash-sensitive llama
  docker build & prebuilt-wasm pytest (heavy: docker + models), ending with
  a `WASM-HASHES.md` comparison: byte-identical release ⇒ hash unchanged, no
  new row; Binaryen-bump release ⇒ new row via llama's own release process.

Also useful:

- `make check-downstream-pins` — version pins in sync across the family
  (llama `requirements.txt` + `docker/docker-compose.yml`; from Phase 2 on
  the icpp-pro pin, cross-checked by `make -C ../icpp-pro
  check-sibling-pins`).

Downstream test identities are per-repo (`llama-cpp-testing`) and
auto-created by each repo's Makefile; the machine-wide active identity is
never read or written.
