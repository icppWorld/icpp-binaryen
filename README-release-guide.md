# icpp-binaryen release guide

This guide explains how to release icpp-binaryen to PyPI. It is the source of
truth for Ceremony 7 of [README-feature-guide.md](README-feature-guide.md);
the Claude Code skill `icpp-binaryen-release` wraps it.

Unlike icpp-pro/icpp-candid, the wheels are **platform-specific** (they bundle
the Binaryen shared library) and are therefore built and published by GitHub
Actions on a tag push — never uploaded from a laptop. Publishing uses PyPI
trusted publishing (OIDC); there is no long-lived token and no `.pypirc`.

## Version scheme

`<binaryen>.<minor>.<patch>` per [pep-0440](https://peps.python.org/pep-0440/),
e.g. `116.0.0`:

- The major component IS the bundled Binaryen version. Bumping it changes the
  emitted wasm bytes and triggers the downstream hash-change ceremony.
- Minor/patch releases keep the bundled Binaryen version and MUST be
  byte-identical in `fix_globals_limit` output (the parity gate below).

## Checkout `main` branch

All feature PRs of the release are merged; working tree clean; CI green on
`main`.

## Pre-release gates

```bash
conda activate icpp-binaryen

make all-static                # black + pylint + mypy
make all-tests                 # unit + smoke suites
make parity-test               # byte-identical output vs the golden hash
make check-downstream-pins     # see what will need bumping after release
make downstream-verify-full    # per the phases that have landed (heavy)
```

The parity golden hash was established at `116.0.0`: a real
`llama_cpp_before_opt.wasm` artifact run through `binaryen.py==0.0.2` (on
macOS, where 0.0.2 works) and through this package produced byte-identical
output. Every same-Binaryen release re-verifies against that hash. A bundled
Binaryen bump re-establishes the golden hash and is by definition
hash-changing downstream — plan the llama_cpp_canister `WASM-HASHES.md`
ceremony (and, from Phase 2 on, the icpp-pro release ceremony) before
tagging.

## Version bump

- Update the version in `src/icpp_binaryen/version.py` (single source; the
  bundled-Binaryen assert reads its major component).
- Commit directly to `main` with the version as the single-line message,
  e.g. `116.0.0` (or `116.0.0rc1` for release candidates), and push.
- Make sure CI passes on the bump commit.

## Tag & publish

```bash
git tag v116.0.0
git push origin v116.0.0
```

The tag push triggers the release workflow, which per platform (macOS x86_64,
macOS arm64, Linux x86_64):

1. Downloads the official Binaryen release tarball for the bundled version
   and verifies its published `.sha256`.
2. Ships the `libbinaryen.dylib` as-is (macOS) or relinks the official
   `libbinaryen.a` into `libbinaryen.so` (Linux), plus `version.txt`.
3. Assembles the `py3-none-<platform>` wheel and checks it (`auditwheel` on
   Linux).
4. Installs the wheel and runs the smoke suite against it.
5. Publishes all wheels to PyPI via trusted publishing — only when every
   platform's test job is green.

Monitor the workflow to completion; a red leg means nothing was published.

## Test the released package

```bash
# create a brand new python environment
conda create --name test python=3.11
conda activate test
pip cache purge

pip install icpp-binaryen==116.0.0

# run the smoke suite against the released wheel, from the repo:
pytest -vv test/smoke

conda deactivate
conda remove --name test --all
```

The smoke suite is the definitive check: import + `BINARYEN_VERSION` assert,
`fix_globals_limit` on the checked-in fixture, wasmtime instantiation of the
result, name section intact in the `_before_opt` copy, determinism. Check
pytest's exit code itself — not a piped tail.

## Follow-up steps

- Bump the downstream pins, then `make check-downstream-pins` until green:
  - `llama_cpp_canister/requirements.txt` — `icpp-binaryen==X.Y.Z` (hard
    pin: the version decides the wasm bytes) and
    `llama_cpp_canister/docker/docker-compose.yml` — the `icpp_binaryen`
    anchor.
  - Byte-identical release: rebuild llama's wasm and verify the hash is
    unchanged — no new `WASM-HASHES.md` row.
  - Binaryen-bump release: follow the llama repo's own release process
    (`.claude/skills/llama_cpp_canister-release`) — the wasm hash changes.
  - From Phase 2 on: the icpp-pro dependency pin, verified with
    `make -C ../icpp-pro check-sibling-pins`.
- Update `CHANGELOG.md`: move the unreleased lines under the new version.
- Announcement in OpenChat.
