# Repository agent contract — scientific simulations

Read [docs/SCIENCE_CHARTER.md](docs/SCIENCE_CHARTER.md), [docs/EXODUS_MODEL_CONTRACT.md](docs/EXODUS_MODEL_CONTRACT.md) and [docs/ROADMAP.md](docs/ROADMAP.md) before making physics-bearing changes.

## Roles and tools

- Implementation agents (including Antigravity and Hermes) may perform scoped development using relevant [Superpowers](https://github.com/obra/superpowers), [Matt Pocock skills](https://github.com/mattpocock/skills) and [Scientific Agent Skills](https://github.com/k-dense-ai/scientific-agent-skills).
- Use explicit domain modeling and red-green-refactor tests, reference-source verification, units/dimensional analysis, numerical benchmarks and critical adversarial review.
- Skills guide workflow; a skill or an AI is never an independent experimental measurement or physics authority.
- Do not introduce a novel scalar-field law or claimed net thrust as an established result.

## Commit and PR procedure

1. Start from the most recent reviewed code baseline. Make a scoped branch and draft PR; preserve the old notebooks until physics interpretation is corrected and validated.
2. Each PR needs: precise claim, source/derivation, boundary conditions, units, assumptions, alternative mechanisms, numeric benchmarks and error analysis.
3. Prefer changes with independent unit/regression tests and source-backed input data. Run relevant tests locally; report them precisely, without implying CI passed before confirming GitHub status.
4. Keep PR in **draft** until an independent adversarial ChatGPT/scientific re-review is completed; implement fixes in branch and request re-review at updated head SHA.
5. When ready for independent review, write a persistent handoff in repo containing: repo, PR number, branch, HEAD SHA, precise changed scope, tests/CI, remaining uncertainty and reviewer acceptance criteria. Announce **READY FOR CHATGPT INDEPENDENT REVIEW** (not merely ready for human review).
6. **Timestamp every readiness handoff.** In both the GitHub PR comment and Antigravity/Hermes's final user-visible status message, include **Issued at (Pacific):** `YYYY-MM-DD HH:MM:SS PDT/PST (UTC offset)` and **Issued at (UTC):** `YYYY-MM-DDTHH:MM:SSZ`. Generate these from the real clock **immediately before posting** (for example, `TZ=America/Los_Angeles date '+%Y-%m-%d %H:%M:%S %Z %z'` and `date -u '+%Y-%m-%dT%H:%M:%SZ'`). Do not recycle the CI completion timestamp or the previous handoff's date. Add the current review round (R3, R4, etc.), source HEAD SHA, and CI run link so completion is unambiguous.
7. **Pickup behavior for every resumed check (manual or scheduled):** refresh PR HEAD, latest GitHub Conversation comments, submitted reviews, and outstanding review threads; read the **newest independent changes-requested review and fix queue**, not just the static handoff. Work on that outstanding queue, run regression tests, push the updated SHA, verify CI/artifacts, and post the timestamped **READY FOR CHATGPT INDEPENDENT RE-REVIEW (R<next>)** handoff. Older READY messages are historical, not evidence that newer findings are resolved. This instruction applies when the agent runs; it does **not** by itself create or verify a scheduler.
8. Do not self-approve or merge based solely on test pass, aesthetics, a patent grant, or speculative interpretation. Merge only with authorization.

## Current starting point

- Draft [PR #5](https://github.com/aguacatero/scalar-wave-viz/pull/5): scientific charter and conventional electrostatic baseline.
- **CURRENT STATUS (2026-10-18): P0 SCIENTIFIC BASELINE ACCEPTED.** [Independent R8 review](https://github.com/aguacatero/scalar-wave-viz/pull/5#pullrequestreview-5566614469) and [Antigravity/Hermes R8 pickup instructions](https://github.com/aguacatero/scalar-wave-viz/pull/5#issuecomment-6259060825) explicitly accepted implementation code SHA `57067164b47d7d374a1d7bb1c8ce00bb79aa07f8` (all 35 tests passed in [CI Run 39187698432](https://github.com/aguacatero/scalar-wave-viz/actions/runs/39187698432); artifact bundle 12158189698 independently inspected). R7-F1 and R7-F2 resolved and verified. **PR #5 remains DRAFT, OPEN, UNMERGED** pending explicit owner merge authorization. Do not self-approve or merge. [R8 sign-off ledger](docs/handoffs/2026-10-18-P0-CHATGPT-R8-ACCEPTED.md), [R7 fix queue](docs/handoffs/2026-10-18-P0-CHATGPT-R7-FIX-QUEUE.md), [R6 fix queue](docs/handoffs/2026-10-18-P0-CHATGPT-R6-FIX-QUEUE.md), [R5 fix queue](docs/handoffs/2026-10-18-P0-CHATGPT-R5-FIX-QUEUE.md), [R4 fix queue](docs/handoffs/2026-10-18-P0-CHATGPT-R4-FIX-QUEUE.md), [R3 fix queue](docs/handoffs/2026-10-14-P0-CHATGPT-R3-FIX-QUEUE.md) and [R1/R2 fix queue](docs/handoffs/2026-10-13-P0-CHATGPT-R1-FIX-QUEUE.md) document complete review history.
- Next work **after independent review**: P1 numerical validation and Maxwell stress/whole-apparatus accounting ([Issue #6](https://github.com/aguacatero/scalar-wave-viz/issues/6)), then P2 reproducible patent-figure geometry and separate patent claims ([Issue #7](https://github.com/aguacatero/scalar-wave-viz/issues/7)).
- The existing [PR #4](https://github.com/aguacatero/scalar-wave-viz/pull/4) about Jev classification is distinct; Jev must not decide physical validity.
