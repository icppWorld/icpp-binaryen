---
name: icpp-binaryen-coderabbit
description: Evaluate and resolve every CodeRabbit finding on an open PR in the icpp-binaryen repo family — fetch the review comments, fix legitimate findings on the same branch, rebut false positives with reasoning, until nothing is left unaddressed
disable-model-invocation: false
user-invocable: true
---

# Resolve CodeRabbit findings on a PR

Part of the Branching & PRs ceremony in `README-feature-guide.md`: after a
PR is created, every CodeRabbit finding is evaluated and resolved BEFORE the
maintainer reviews. Applies to every repo the feature touches
(icpp-binaryen, llama_cpp_canister, icpp-pro).

## 1. Fetch the findings

CodeRabbit posts a PR-level summary comment plus inline review comments.
Fetch both (from the repo the PR belongs to):

```bash
gh pr view <N> --comments                      # summary + discussion comments
gh api repos/<owner>/<repo>/pulls/<N>/comments # inline review comments (the findings)
gh api repos/<owner>/<repo>/pulls/<N>/reviews  # review bodies
```

CodeRabbit needs a few minutes after push — if there is no review yet, wait
and re-fetch rather than concluding there are no findings.

## 2. Evaluate each finding — three verdicts

- **Legitimate** → fix it. Follow the implementation rules
  (README-feature-guide.md Ceremony 2), re-run the tests the fix touches
  (at minimum `make all-tests`; `make parity-test` when the emitted bytes
  could be affected), and commit to the SAME feature branch — single-line
  message, no trailers. CodeRabbit re-reviews incrementally on push.
- **False positive / not applicable** → reply on that comment thread with
  the concrete reasoning (cite the code or spec that shows why), so the
  maintainer sees the assessment:
  ```bash
  gh api repos/<owner>/<repo>/pulls/<N>/comments/<comment_id>/replies -f body="..."
  ```
- **Real but out of scope** → reply saying so and record it: an open
  decision in HANDOVER.md section 5 or a GitHub issue, and link it in the
  reply.

Never dismiss a finding silently, and never suppress one by disabling
CodeRabbit or editing its configuration.

## 3. Done when

- Every finding has either a fixing commit or a reasoned reply.
- The repo's own checks are green after any fixes (`make all-static` +
  `make all-tests`).
- Report the tally to the user (fixed / rebutted / deferred, with links).
  The PR then waits for the maintainer's manual approval — never merge.
