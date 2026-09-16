---
name: icpp-binaryen-new-feature
description: The per-feature ceremony loop for icpp-binaryen — plan with an output-bytes assessment, implement all four layers (cdef, API, tests, docs), test including the byte-identical parity gate, and track progress on the roadmap
disable-model-invocation: false
user-invocable: true
---

# New feature development for icpp-binaryen

Read `README-feature-guide.md` (repo root) and follow Ceremonies 1-3, 5, 6 in
order. This skill is the checklist; the guide is the source of truth.

## 1. Plan (guide Ceremony 1)

- Check the roadmap first: HANDOVER.md sections 4 (integration phases) and 5
  (open decisions).
- Reference material: `binaryen-c.h` of the **bundled** Binaryen version (in
  the official release tarball), and
  `../llama_cpp_canister/scripts/optimize_wasm.py` (the consumer).
- The plan MUST contain an **output-bytes assessment**: byte-identical vs
  hash-changing for `fix_globals_limit` output, and additive vs breaking for
  the Python API. Default must be byte-identical + additive — a minor/patch
  bump never changes a downstream wasm hash. Anything else needs explicit
  maintainer sign-off.
- The plan MUST name the **branch**: `feature/<short-kebab-slug>`, used with
  the EXACT same name in every repo the feature touches, plus the expected
  repo list.

## 2. Implement (guide Ceremony 2) — four layers, always together

First: `git checkout -b feature/<slug>` — never work on `main`. Create the
same branch in a downstream repo only at the moment it needs a change.

1. cdef: `src/icpp_binaryen/_cdef.py` — add ONLY the declarations the new
   API needs, signatures verified against the bundled `binaryen-c.h`. Never
   auto-translate the full header.
2. API: `src/icpp_binaryen/` — additive only; `ffi`/`lib` stay the raw
   escape hatch.
3. Tests: unit (`test/unit/`, against the checked-in fixtures) AND smoke
   (`test/smoke/`, pytest end-to-end against the installed package).
4. Docs: README public-API section + CHANGELOG line (guide Ceremony 5).

Preserved side effects: the optimizer strips the wasm name section; the
`_before_opt` backup keeps it. Never "fix" this.

## 3. Test (guide Ceremony 3)

```bash
make all-static
make all-tests          # unit + smoke
make parity-test        # when the emitted bytes could be affected
```

Then run the downstream tier that matches the change — see the
`icpp-binaryen-verify-downstream` skill.

## 4. Track & commit (guide Ceremony 6)

- Update HANDOVER.md phase status / resolved decisions in the same sitting
  as the work that changes them.
- Statuses reflect merge state: an open PR is "in review", NEVER "done".
- Commit per repo on the shared `feature/<slug>` branch: single-line
  message, no trailers, no `--no-verify`. Push only when the user asks.
- PRs: one per changed repo from the same branch name, cross-referencing the
  icpp-binaryen PR. Merge order: icpp-binaryen → llama_cpp_canister →
  icpp-pro.
- After each PR is created: evaluate and resolve every CodeRabbit finding on
  it (use the `icpp-binaryen-coderabbit` skill) — fix or rebut with
  reasoning before the maintainer reviews.
- Every PR must receive a MANUAL approval from the maintainer before
  merging. Never merge a PR yourself — ask the user and wait.
