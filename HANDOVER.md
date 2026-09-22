# HANDOVER — icpp_binaryen

**Goal:** a minimal, icppWorld-maintained Python package (`icpp-binaryen`, import name
`icpp_binaryen`) that provides cffi bindings over Binaryen's C API plus Binaryen's
prebuilt library per platform. It replaces the brittle `binaryen.py==0.0.2` dependency
in `llama_cpp_canister`, and is designed from day one to become a direct dependency of
`icppWorld/icpp-pro`, which will run the IC globals-limit fix as a standard part of
every `icpp build-wasm`.

Research date of the facts below: 2026-09-16.

## 1. Why this package exists

### The problem it solves for canisters

The Internet Computer rejects a wasm module with more than 1000 *defined* globals
(install error `IC0505`). A wasi-sdk build of a large C++ project blows past this:
`llama_cpp_canister` links to ~1046 defined globals. The fix, in place today in
`llama_cpp_canister/scripts/optimize_wasm.py` (run by icpp-pro's `post_wasm_function`
hook, configured in `icpp.toml`), is:

1. Load the linked wasm with Binaryen (`BinaryenModuleRead`).
2. Remove every export of kind *global* (`BinaryenRemoveExport`). This is what frees
   the globals to be optimized away — an exported global is otherwise kept alive.
3. Run Binaryen's optimizer at shrink level 0 / optimize level 0
   (`BinaryenModuleOptimize`). Defined globals drop from ~1046 to 1.
4. Emit the wasm back to disk (`BinaryenModuleAllocateAndWriteData` via the wrapper's
   `emit_binary()`).

Every wasi-built canister near the limit has this problem, which is why the end state
is to run this inside icpp-pro itself, not per-project.

Known side effect to preserve and document: the optimize pass strips the wasm *name
section*. `llama_cpp_canister` deliberately keeps a `_before_opt` copy for named
backtraces in its wasmtime harness. Do not "fix" this; downstream tooling relies on
the before/after pair.

### Why the current dependency (jonathanharg/binaryen.py) is unacceptable

- Upstream is dormant: last commit and last release (117.1.1) on 2024-04-26, last push
  of any kind September 2024, 3 stars, 2 open issues without resolution. Binaryen
  itself is at version 132 (August 2026) — 16 major versions ahead.
- `llama_cpp_canister` is pinned to `binaryen.py==0.0.2` (October 2023, bundles
  Binaryen 116) because 117.x requires Python >= 3.12 with cp312-only wheels, while
  the icpp-pro toolchain is Python 3.11 (conda env and the `python:3.11-slim-bookworm`
  Docker base image).
- The 0.0.2 Linux packaging is broken: it ships a static `libbinaryen.a` and then
  tries to `dlopen()` it. `llama_cpp_canister/docker/Dockerfile.base` carries a
  workaround that relinks the archive into a `.so` and patches the package's `lib.py`
  with `sed`. A host-side `icpp build-wasm` on Linux is impossible without it.
- `optimize_wasm.py` barely uses the pythonic wrapper anyway — nearly everything goes
  through the raw cffi layer (`from binaryen import ffi, lib`). The real dependency
  surface is about ten C functions.

### Alternatives considered and rejected

| Alternative                          | Why rejected                                                                |
|--------------------------------------|-----------------------------------------------------------------------------|
| Maintain the icppWorld/binaryen.py fork | Inherits a half-finished pythonic wrapper we do not use; larger surface   |
| pybinaryen (irmen, active on PyPI)   | Requires a system-installed libbinaryen; moves the packaging problem to CI  |
| nxbinaryen                           | Single release from 2022, dead                                              |
| wasm-opt CLI subprocess              | Unverified whether any CLI pass removes *exports* of globals; C API does    |

The existing `icppWorld/binaryen.py` fork (zero commits beyond upstream) can be
archived or deleted once this package ships.

## 2. What to build

### Package shape

- Repo: `icppWorld/icpp_binaryen` (this folder). PyPI distribution name
  `icpp-binaryen`, import name `icpp_binaryen`. License Apache-2.0 (same as Binaryen
  and as the binaryen.py code that inspired the approach; credit jonathanharg in the
  README).
- **cffi in ABI mode** (`ffi.dlopen`), not API mode. No compiled extension module, so
  no compiler at install time and — the big win — wheels are tagged
  `py3-none-<platform>`: one wheel per platform covers every Python version >= 3.10.
  No per-Python wheel matrix, ever.
- Bundle the platform's shared library inside the wheel next to a `version.txt`
  (Binaryen version number), asserted at import time like the current Docker build
  asserts 116.
- The cffi `cdef` is a hand-curated subset of `binaryen-c.h` — only the declarations
  the API below needs (~15 lines). Do NOT attempt to auto-translate the full header;
  that is the maintenance trap the wrapper projects fell into.

### Public API (all of it — YAGNI applies)

```python
from icpp_binaryen import ffi, lib          # raw escape hatch, same idea as binaryen.py
from icpp_binaryen import Module            # load(path) / optimize(shrink, opt) / emit() / write(path)
from icpp_binaryen import fix_globals_limit # the one high-level entry point
from icpp_binaryen import BINARYEN_VERSION  # int, from the bundled version.txt
```

`fix_globals_limit(wasm_path: Path, *, backup_suffix: str = "_before_opt") -> GlobalsFixReport`
is the function icpp-pro and llama_cpp_canister will both call. It performs exactly
the four steps of section 1 (including saving the `_before_opt` copy) and returns the
before/after counts of exports and of defined globals, so callers can print the same
summary `optimize_wasm.py` prints today. Everything else (`Module`, `ffi`, `lib`) is
the escape hatch for users with their own post-processing needs.

C functions the cdef must cover: `BinaryenModuleRead`, `BinaryenModuleDispose`,
`BinaryenModuleOptimize`, `BinaryenModuleAllocateAndWrite` (or the sized write API),
`BinaryenGetNumExports`, `BinaryenGetExportByIndex`, `BinaryenExportGetKind`,
`BinaryenExportGetName`, `BinaryenRemoveExport`, `BinaryenGetNumGlobals`,
`BinaryenSetShrinkLevel`, `BinaryenSetOptimizeLevel`. Check `binaryen-c.h` of the
bundled version for exact signatures; the header is in every official release tarball.

### Obtaining the shared library per platform (verified 2026-09-16 against version_132)

Official release tarballs at https://github.com/WebAssembly/binaryen/releases contain:

| Platform            | Tarball lib/ contents  | Action for our wheel                                  |
|---------------------|------------------------|-------------------------------------------------------|
| macOS x86_64, arm64 | `libbinaryen.dylib`    | Ship as-is                                            |
| Linux x86_64, aarch64 | `libbinaryen.a` only | Relink to `.so`: `g++ -shared -o libbinaryen.so -Wl,--whole-archive libbinaryen.a -Wl,--no-whole-archive -lpthread` |
| Windows             | (not needed)           | Out of scope; icpp-pro on Windows means WSL = Linux wheel |

The Linux relink is the exact technique already proven in
`llama_cpp_canister/docker/Dockerfile.base` (in production at Binaryen 116). It keeps
the official Binaryen object code byte-for-byte instead of compiling a divergent build.

Linux caveat to verify early: the official Linux binaries are built against a glibc
that may be newer than the `manylinux2014`/`manylinux_2_28` baselines. Run `auditwheel
show` on the first candidate wheel. If the official archive's glibc floor is too new,
fall back to building Binaryen from source with `-DBUILD_SHARED_LIBS=ON` inside a
manylinux container — more CI code, same public API, decide only if forced.

### Versioning and the first release

Version scheme `<binaryen_version>.<minor>.<patch>`, e.g. `116.0.0`.

**The first release must bundle Binaryen 116, not 132.** The package rewrites the
canister wasm, so the bundled Binaryen version determines the shipped wasm bytes and
therefore the `WASM-HASHES.md` hash in llama_cpp_canister. Bundling 116 first makes
migration a pure packaging swap that can be verified by byte-identical output
(acceptance test below). Bumping to 132 is a separate, deliberate release with its own
hash-change ceremony downstream. Binaryen 116 tarballs are still downloadable from the
GitHub releases page (tag `version_116`).

### CI (GitHub Actions)

- Build job per platform: download official tarball, verify its published `.sha256`,
  extract dylib / relink `.a`, assemble wheel (cibuildwheel is overkill for a
  py3-none wheel; a plain `python -m build` with the right platform tag is enough —
  `wheel tags` or a small `bdist_wheel --plat-name` setup does it).
- Test job per platform: install the wheel, run the test suite below.
- Release: tag-triggered publish to PyPI (trusted publishing, no long-lived token).

## 3. Tests and acceptance criteria

1. **Import + version test** on every platform: `BINARYEN_VERSION == expected`,
   `lib.BinaryenModuleRead` callable.
2. **Fixture test**: a small checked-in wasm with >5 defined globals and exported
   globals; `fix_globals_limit` reduces defined globals, removes global exports, the
   result instantiates under wasmtime, and the `_before_opt` copy still has its name
   section.
3. **Parity test (release gate for 116.0.0)**: take a real
   `llama_cpp_before_opt.wasm` artifact from llama_cpp_canister, run the fix through
   `icpp-binaryen==116.0.0` and through `binaryen.py==0.0.2` (macOS, where 0.0.2
   works), and require **byte-identical output**. If parity holds, llama_cpp_canister
   migrates without a new WASM-HASHES.md row.
4. **Determinism test**: two runs on the same input produce identical bytes.

## 4. Integration plan

### Phase 1 — llama_cpp_canister switches over

- `requirements.txt`: replace `binaryen.py==0.0.2` with `icpp-binaryen==116.0.0`
  (hard pin, same reason as today: the version decides the wasm bytes).
- `scripts/optimize_wasm.py` shrinks to a thin call to `fix_globals_limit` (keep the
  file: icpp.toml's `post_wasm_function` still points at it until Phase 2).
- Delete the relink hack and the `sed` patching from `docker/Dockerfile.base`; the
  Docker base image gets simpler and host-side Linux builds start working.
- `docker/docker-compose.yml`: replace the `binaryen_py` / `binaryen` anchors with a
  single `icpp_binaryen` anchor (the Binaryen version is implied by the package pin
  and asserted at import).
- No new WASM-HASHES.md row if the parity test held; verify by rebuilding and
  comparing the hash.

### Phase 2 — icpp-pro builds it in (the end goal)

- icpp-pro adds `icpp-binaryen` as a pinned dependency (it joins the lockstep-pin
  family checked by `make -C icpp-pro check-sibling-pins`; a bump changes downstream
  wasm hashes exactly like an icpp-pro release does).
- `icpp build-wasm` runs `fix_globals_limit` as a standard post-link step, after
  wasi2ic, **before** the user hook. Suggested icpp.toml surface:

  ```toml
  [build-wasm]
  # Built-in globals-limit fix, on by default. Set to false to opt out.
  fix_globals_limit = true
  # Unchanged semantics: the user's own optimization step, now guaranteed to run
  # AFTER the built-in fix, on the already-fixed wasm.
  post_wasm_function = "scripts.my_extra_opt.main"
  ```

- Ordering contract to document in icpp-pro: built-in fix first, user
  `post_wasm_function` second. The user hook keeps full freedom (it can even re-load
  the wasm with `icpp_binaryen.Module` for custom passes) while the IC0505 failure
  mode disappears for everyone by default.
- The `_before_opt` backup naming becomes an icpp-pro convention, so debugging docs
  (named backtraces under wasmtime) apply to every icpp-pro project.

### Phase 3 — cleanup

- llama_cpp_canister deletes `scripts/optimize_wasm.py` and the `post_wasm_function`
  line from `icpp.toml` (the built-in step covers it), keeping only any future
  project-specific extra passes.
- Archive `icppWorld/binaryen.py`.

## 5. Open decisions

Resolved 2026-09-16 (feature `01 initial-package`, see `todo/feature-inventory.html`):

1. **Linux aarch64 wheel in the first release?** ~~Open~~ → **No.** x86_64-linux plus
   both macOS archs first, add aarch64-linux when something needs it (YAGNI).
2. **manylinux strategy** — `auditwheel show` runs in the ubuntu CI on every build
   (early check); `auditwheel repair` retags at release. Fallback (source build in a
   manylinux container) only if auditwheel rejects the relinked official `.a`.
3. **Python floor**: **`>=3.11`**, matching icpp-pro's documented support matrix.
4. **Where the parity-test wasm fixture lives**: **neither checked in nor fetched.**
   `make parity-test` uses the sibling checkout's
   `../llama_cpp_canister/build/llama_cpp_before_opt_internal.wasm` — the backup
   icpp-pro's built-in globals-fix step writes (6.2.0+; before that, llama's own
   `post_wasm_function` hook wrote the same bytes as `llama_cpp_before_opt.wasm`).
   It compares against the recorded golden hashes in `test/parity/golden-116.json`
   (input + output sha256). Parity vs `binaryen.py==0.0.2` was verified
   byte-identical on macOS arm64 on 2026-09-16. NOTE: llama's final
   `build/llama_cpp.wasm` is NOT a valid comparison target — icpp-pro appends
   metadata custom sections (`icp:public candid:service`, `cdk:name`) after the
   built-in fix, and after any post_wasm hook.
