# icpp-binaryen feature development guide

The ceremonies for developing icpp-binaryen features across the repo family.
Any new contributor — human or AI agent — follows this guide for planning,
implementation, testing, and release. The package rationale and target design
live in [HANDOVER.md](HANDOVER.md); the release mechanics live in
[README-release-guide.md](README-release-guide.md).

Claude Code sessions: the skills `icpp-binaryen-new-feature`,
`icpp-binaryen-verify-downstream`, `icpp-binaryen-coderabbit`, and
`icpp-binaryen-release` (in `.claude/skills/`) wrap the ceremonies below.

## The repo family

All repos are cloned as siblings (same parent directory as this repo):

| Repo                 | What it is                                     | Couples to icpp-binaryen via                                                                 |
|----------------------|------------------------------------------------|-----------------------------------------------------------------------------------------------|
| `icpp-binaryen`      | cffi bindings + bundled Binaryen (this repo)   | —                                                                                              |
| `llama_cpp_canister` | llama.cpp as a C++ canister (Phase 1 consumer) | `requirements.txt` hard pin `icpp-binaryen==X.Y.Z`; `docker/docker-compose.yml` anchor; wasm-hash sensitive (`WASM-HASHES.md`) |
| `icpp-pro`           | The C++ CDK (Phase 2 consumer)                 | Pinned dependency; `icpp build-wasm` runs `fix_globals_limit` as a built-in post-link step     |

Coupling activates per the integration phases in HANDOVER.md section 4:
llama_cpp_canister at Phase 1, icpp-pro at Phase 2. Until a phase has landed,
its downstream-verification tier is not applicable yet.

`make check-downstream-pins` verifies the version pins across the family —
run it whenever in doubt.

## The output-bytes rule

This is icpp-binaryen's analog of icpp-pro's backward-compatibility rule.

**The rewritten wasm bytes are part of the public contract.** The package
exists to rewrite canister wasm, so the bytes it emits determine downstream
wasm hashes (`WASM-HASHES.md` in llama_cpp_canister). Concretely:

- Version scheme `<binaryen>.<minor>.<patch>` (e.g. `116.0.0`): the major
  component IS the bundled Binaryen version.
- Within a bundled Binaryen version, every change keeps `fix_globals_limit`
  output **byte-identical** for the same input. The determinism test and the
  fixture golden hashes are the gate. A minor/patch bump never changes a
  downstream wasm hash.
- Bumping the bundled Binaryen version is a major bump and a deliberate,
  separate release with its own downstream hash-change ceremony (new
  `WASM-HASHES.md` row in llama_cpp_canister; from Phase 2 on, an icpp-pro
  release ceremony).
- The public Python API only grows: existing signatures are never changed or
  removed; extend with new functions/parameters (with defaults).
- The cffi `cdef` stays a hand-curated subset of `binaryen-c.h` — only what
  the public API needs. Never auto-translate the full header; that is the
  maintenance trap the wrapper projects fell into (HANDOVER.md section 2).
- Documented side effects are preserved, not "fixed": the optimize pass
  strips the wasm name section, and the `_before_opt` backup keeps it —
  downstream debugging (named backtraces under wasmtime) relies on the pair.

Breaking any of these is the rare exception: it requires explicit maintainer
sign-off in the plan and a documented migration path.

## Branching & PRs

Feature work never happens on `main`. One feature = one branch name, and that
**exact same branch name is used in every repo the feature touches**.

- Name: `feature/<short-kebab-slug>`. Pick it once, in the plan (Ceremony 1).
- Create it in icpp-binaryen when implementation starts:
  `git checkout -b feature/<slug>`. Create the same branch in a downstream
  repo lazily — at the moment that repo actually needs a change — never
  preemptively.
- One PR per repo, all from the same branch name. Cross-reference the
  icpp-binaryen PR from each downstream PR.
- **After a PR is created, every CodeRabbit finding on it is evaluated and
  resolved before the maintainer review** — use the `icpp-binaryen-coderabbit`
  skill: fix the legitimate ones (commit to the same branch), reply on the
  thread with reasoning for anything assessed as a false positive.
- **Every PR requires a manual approval by the maintainer before merging** —
  no self-merges, no auto-merge, in every repo. An AI agent never merges a PR
  on its own; it asks and waits for the approval.
- Merge order: **icpp-binaryen first** (downstream builds against it), then
  llama_cpp_canister, then icpp-pro.
- Exception: the release ceremony pushes the version-bump commit directly to
  `main`, as prescribed by README-release-guide.md.

## Ceremony 1 — Plan

1. Start from the roadmap: `todo/feature-inventory.html` and its published
   Claude artifact (same URL every time, recorded in `todo/artifacts.md`).
   Check it before and after. HANDOVER.md sections 4-5 remain the background
   design document; record resolved open decisions there in place.
2. Explore first: what does `binaryen-c.h` of the **bundled** Binaryen version
   offer (the header is in every official release tarball), what does
   `llama_cpp_canister/scripts/optimize_wasm.py` need, what exists in
   icpp-binaryen already.
3. Write the plan with three mandatory sections:
   - **Definition of Done** (see Ceremony 2 — all four layers).
   - **Output-bytes assessment**: classify the change byte-identical vs
     hash-changing for `fix_globals_limit` output, and additive vs breaking
     for the Python API. The default answer must be **byte-identical and
     additive**; anything else needs explicit maintainer sign-off.
   - **Branch name**: the `feature/<slug>` used in every repo the feature
     touches (see Branching & PRs), plus the list of repos expected to change.

## Ceremony 2 — Implement

Start on the branch: `git checkout -b feature/<slug>` in icpp-binaryen; the
same name in each downstream repo at the moment it needs a change.

Definition of Done for a new capability — four layers, always together:

1. **cdef** — the hand-curated declaration subset in
   `src/icpp_binaryen/_cdef.py`: add only the C declarations the new API
   needs, with signatures verified against the bundled version's
   `binaryen-c.h`.
2. **API** — `src/icpp_binaryen/`: the pythonic surface (`Module`,
   `fix_globals_limit`, or a new addition). Additive only; `ffi`/`lib`
   remain the raw escape hatch.
3. **Tests** — unit tests in `test/unit/` (the API against the checked-in
   wasm fixtures) AND smoke tests in `test/smoke/` (pytest, end-to-end
   against the installed package: import, version assert, fixture rewrite,
   wasmtime instantiation, determinism).
4. **Docs** — the public-API section of `README.md` plus a release-notes
   line (Ceremony 5).

Compatibility while coding: add, never change or remove, public signatures;
byte-identical output within a bundled Binaryen version; Python floor per
`pyproject.toml`.

## Ceremony 3 — Test

```bash
conda activate icpp-binaryen
make all-static                  # black + pylint + mypy
make all-tests                   # unit + smoke suites (pytest)
```

CI (mac + ubuntu matrix) must be green: each platform builds its wheel,
installs it, and runs the smoke suite against it.

**Parity test** — required for any release that keeps the bundled Binaryen
version, and for any change that could touch the emitted bytes:

```bash
make parity-test
```

This runs a real `*_before_opt.wasm` artifact through this tree's
`fix_globals_limit` and asserts the output bytes against the recorded golden
hash (established at `116.0.0` against `binaryen.py==0.0.2` — see
README-release-guide.md). Byte-identical means downstream migrates without a
new `WASM-HASHES.md` row.

## Ceremony 4 — Verify downstream (tiered)

| What changed                                                   | What to run                                                     |
|----------------------------------------------------------------|------------------------------------------------------------------|
| Internal only (no public API, no output-byte change possible)  | nothing beyond Ceremony 3                                        |
| Public API surface (signatures, `Module`, `fix_globals_limit`) | `make downstream-verify-api`                                     |
| Anything that could touch emitted bytes (cdef, lib, passes)    | `make parity-test` **plus** `make downstream-verify-api`         |
| Bundled Binaryen bump, or release                              | `make downstream-verify-full`                                    |

- `downstream-verify-api` = install this tree's wheel into the
  llama_cpp_canister env and run its optimize path + model-free API suite
  (`test/test_canister_functions.py`). From Phase 2 on it adds the icpp-pro
  `make all-tests` leg.
- `downstream-verify-full` = the above plus the wasm-hash-sensitive
  llama_cpp_canister docker build + prebuilt-wasm pytest (heavy: docker +
  models), with a `WASM-HASHES.md` comparison at the end.

Host caveat: llama's native leg needs an x86_64 host (see the note in its
`icpp.toml`); on an arm64 Mac rely on llama's CI or its docker path for that
leg.

Each downstream repo manages its own test identity (`llama-cpp-testing`);
nothing ever touches the machine-wide active identity.

## Ceremony 5 — Document

For every user-facing capability:

1. `README.md`: extend the public-API section (the API is small by design —
   HANDOVER.md section 2 — so the README is the API reference).
2. `CHANGELOG.md`: one line per capability under the unreleased version.
3. From Phase 2 on: the icpp-pro/icpp-docs surface for the built-in
   `fix_globals_limit` step follows icpp-pro's own Ceremony 5.

## Ceremony 6 — Track & commit

1. The roadmap lives in TWO synchronized places: the file
   `todo/feature-inventory.html` and its published Claude artifact (same URL
   every time, recorded in `todo/artifacts.md`). Every roadmap edit updates
   the file AND republishes the artifact in the same sitting — never one
   without the other.
2. Statuses reflect **merge state, not commit state**: work on a feature
   branch / open PR is "in progress" or "in review" (with the PR links) —
   never "done" until every PR of the feature has merged; "done" is set via
   a roadmap-only commit on `main` plus the artifact republish. When an item
   is split, the parts keep the parent's id (e.g. `02a`/`02b`) instead of
   being renumbered.
3. Commits: single-line message, no description body, no `Co-Authored-By`
   trailers, never `--no-verify`. One commit per repo, on the shared
   `feature/<slug>` branch. Push only when the maintainer says so.
4. PRs: one per changed repo from the same branch name, cross-referencing
   the icpp-binaryen PR; merge icpp-binaryen first, icpp-pro last.
5. CodeRabbit pass: evaluate and resolve every CodeRabbit finding on each PR
   (`icpp-binaryen-coderabbit` skill) — fix or rebut with reasoning, re-run
   the affected tests for any fix, push to the same branch.
6. Every PR needs a manual maintainer approval before it merges (see
   Branching & PRs).

## Ceremony 7 — Release

Follow [README-release-guide.md](README-release-guide.md) end to end. The
gates added by this guide:

- `make check-downstream-pins` — before and after the downstream pin bumps.
- `make parity-test` — byte-identical output is the release gate for every
  release that keeps the bundled Binaryen version.
- `make downstream-verify-full` — mandatory at release (per the phases that
  have landed).
- Downstream pin bumps (exact locations are in the release guide follow-ups):
  llama_cpp_canister `requirements.txt` + `docker/docker-compose.yml`; from
  Phase 2 on, the icpp-pro dependency pin (it joins the lockstep-pin family
  checked by `make -C ../icpp-pro check-sibling-pins`).
