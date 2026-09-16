---
name: icpp-binaryen-release
description: Release ceremony for icpp-binaryen — pre-release gates including the byte-identical parity check, version bump, tag-triggered GitHub Actions publish to PyPI via trusted publishing, and the downstream version-pin bumps that follow
disable-model-invocation: false
user-invocable: true
---

# Release icpp-binaryen

Follow `README-release-guide.md` (repo root) step by step — it is the source
of truth. The gates and follow-ups to not skip:

## Before tagging

1. Version scheme `<binaryen>.<minor>.<patch>`: the major component IS the
   bundled Binaryen version. Decide up front whether this release is
   byte-identical (minor/patch) or a Binaryen bump (major, hash-changing
   downstream — plan the llama `WASM-HASHES.md` ceremony first).
2. On `main`, all PRs merged, CI green:
   `make all-static`, `make all-tests`, `make parity-test` (mandatory for
   every same-Binaryen release), `make check-downstream-pins`,
   `make downstream-verify-full` (heavy; per the phases that have landed).
3. Version bump: `src/icpp_binaryen/version.py`, committed directly to
   `main` with the version as the single-line message (e.g. `116.0.0`).
   CI must pass on the bump commit.

## Tag & publish

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

The wheels are platform-specific (bundled Binaryen shared library) and are
built and published ONLY by the tag-triggered GitHub Actions workflow:
official tarball + sha256 verify, dylib as-is / Linux relink, py3-none
platform wheel, auditwheel check, smoke suite per platform, then PyPI via
trusted publishing (no token, no laptop upload). Monitor the workflow to
completion — a red leg means nothing was published.

## After publish

1. Test the released package in a fresh conda env:
   `pip install icpp-binaryen==X.Y.Z`, then `pytest -vv test/smoke` — check
   pytest's own exit code.
2. Bump the downstream pins, then `make check-downstream-pins` until green:
   - `llama_cpp_canister/requirements.txt` (`icpp-binaryen==X.Y.Z`, hard
     pin) AND `llama_cpp_canister/docker/docker-compose.yml` (the
     `icpp_binaryen` anchor).
   - Byte-identical release: rebuild llama's wasm, verify the hash is
     unchanged — no new `WASM-HASHES.md` row.
   - Binaryen-bump release: llama's own release process
     (`llama_cpp_canister/.claude/skills/llama_cpp_canister-release`).
   - From Phase 2 on: the icpp-pro pin
     (`make -C ../icpp-pro check-sibling-pins`).
3. `CHANGELOG.md`: move the unreleased lines under the new version.
4. Announcement in OpenChat.
