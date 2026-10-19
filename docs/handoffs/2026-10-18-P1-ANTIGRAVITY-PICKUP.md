# P1 — Antigravity / Hermes implementation pickup and independent review contract

**STATE: P1 IMPLEMENTATION REQUESTED — NOT YET READY FOR INDEPENDENT SCIENTIFIC REVIEW.**

- Repository: https://github.com/aguacatero/scalar-wave-viz
- Tracker: [Issue #6](https://github.com/aguacatero/scalar-wave-viz/issues/6)
- Branch: `p1-numerics-force-accounting-2026-10-18`; base: `main`
- P0 merged [PR #5](https://github.com/aguacatero/scalar-wave-viz/pull/5) as merge commit `174c6b895a0c2ec416b6d46ab9e0835b14a8cb49` on 2026-10-18 (Pacific)
- Independently accepted P0 implementation code SHA: `57067164b47d7d374a1d7bb1c8ce00bb79aa07f8` — [R8 scientific acceptance](https://github.com/aguacatero/scalar-wave-viz/pull/5#pullrequestreview-5566614469), [35-test CI](https://github.com/aguacatero/scalar-wave-viz/actions/runs/39187698432), [sign-off ledger](2026-10-18-P0-CHATGPT-R8-ACCEPTED.md).
- Next milestone: P1 **only**. P2 patent FIGS. 4–8 model is reserved for [Issue #7](https://github.com/aguacatero/scalar-wave-viz/issues/7) after P1's independent acceptance.
- Read `AGENTS.md`, `docs/SCIENCE_CHARTER.md`, `docs/EXODUS_MODEL_CONTRACT.md`, `docs/ROADMAP.md`, and Issue #6 before editing.

## Pickup workflow — mandatory

1. Refresh `main` and the P1 branch, check Issue #6 and the *latest* P1 draft PR Conversation/reviews/threads, and check for new owner instructions. Treat this handoff as a starting contract, not evidence of completed work.
2. Work only on the P1 branch. Keep P1 PR **DRAFT** and do not merge or self-approve. Keep P0's 35 tests green. Make small separately testable commits with exact claims and source/derivation links.
3. If not yet implemented, perform red-green numerical tests *before* declaring success. Prefer independently derived analytic/manufactured solutions and an independent implementation, not a comparison of code to itself.
4. For each numerical diagnostic, include equations, boundary conditions, grid resolution, units, residuals, chosen tolerances, provenance, and quantitative convergence/error tables. Define acceptance tolerances before examining results; record any failure honestly.
5. Update permanent handoff with current source HEAD SHA, tests, real GitHub CI run URL, artifact IDs, uncertainty and blocked criteria. Timestamp both Pacific and UTC from the **actual clock** immediately before posting.
6. **Only when reviewable:** post on the P1 PR `READY FOR CHATGPT INDEPENDENT REVIEW — P1 R1` with exact source SHA and tested checkout SHA. On fixes, advance P1 review round and consult latest independent comments. Independent reviewer is a distinct gate; a green CI job does not authorize merging.
7. If unattended GitHub pickup/polling is not actually configured, explicitly state `PICKUP: MANUAL-ONLY` or `UNVERIFIED`. Do not claim that these written instructions autonomously launch a worker.

## Work packages and falsifiable acceptance

### P1-A — electrostatic numerical convergence and enclosure sensitivity
- Retain the P0 2D grounded-outer-box Dirichlet physics and vacuum/conductor masking; add at least one independent analytic harmonic or manufactured-solution field benchmark with quantified potential and field errors.
- Demonstrate mesh refinement, consistent observation locations and electric field evaluation, outer-box/domain-size sweeps, and residuals. Demonstrate measured error trends rather than calling finite-grid stability formal convergence. R7-F1 vacuum-probe geometry guard and R7-F2 `is_stable` vs `is_converged` semantics must remain intact.
- Where conductor corner fields or geometry discretization preclude an asymptotic claim, record the limitation and use suitable away-from-singularity observables; do not fabricate an extrapolated accuracy.

### P1-B — Maxwell stress and *whole-apparatus* force bookkeeping
- Implement vacuum closed-contour/surface stress accounting from `T_ij = epsilon_0(E_i E_j - |E|² delta_ij/2)` with correct traction normals. Benchmark simple analytically tractable configurations.
- For the 2D cross-section, all integrated forces are **N/m**. Do not label as Newtons or 3D device thrust. Include contour location and refinement sensitivity, conductor masks/guard, and integral closure checks.
- Report separate force budgets for electrodes, grounded enclosure, external field boundary, and any explicitly modeled other conductors. Supports, wiring and power supply are NOT implicitly modeled by the 2D grid: identify them as missing mechanical reactions, not fictitious zeros. Never infer net propulsion from partial forces or a nonzero residual.
- Establish what the modeled system boundary encloses and demonstrate sign consistency and force balance for applicable static test cases before a whole-device claim. If system is open/coupled to an external ground, clearly state the limitation.

### P1-C — legacy 3D mathematical scalar-wave numerical repairs
- Move forcing outside the damping/absorbing region. Explicitly choose and describe implemented boundary scheme; do not label heuristic damping as PML.
- Establish CFL stability and grid-points-per-wavelength limits. Benchmark free-space propagation, numerical dispersion, known reflection/transmission cases, artificial-boundary reflection, and energy/source normalization against reference solutions.
- Report timestep, grid spacing, frequencies, error norms and repeated-refinement studies; under-resolved exotic-material presets remain **WHAT-IF** and numerically unvalidated. No inference of physical scalar electrodynamics or special Moscovium properties.

### P1-D — reproducibility and scientific UI
- Every plot/manifest must distinguish `ESTABLISHED MODEL`, `WHAT-IF PARAMETER`, `UNVERIFIED NUMERICAL OUTPUT`, and actual source-backed experimental data. Preserve exact source/tested SHA, units, plotted equations, tolerances, assumptions, confidence/uncertainty and any failed gate.
- Keep strict JSON serialization and all existing manifest provenance checks; include reproducible command lines and deterministic tests where possible.

## Independent P1 acceptance (must all be demonstrated, not merely promised)

- [ ] All existing P0 regression tests green and new focused analytic/independent cross-checks green.
- [ ] Explicit mesh, domain-size, contour-position and/or absorbing-boundary studies with defensible errors and convergence qualifications.
- [ ] Correct 2D N/m vs 3D N bookkeeping; no unmatched forces asserted as thrust and no unmodeled support reaction silently set to zero.
- [ ] CFL/wavelength resolution and reflection/dispersion/energy benchmarks for 3D wave numerics, including honest invalid or unverified cases.
- [ ] CI success at exact current P1 PR source HEAD, reproducible PNG/JSON artifacts, manifest provenance, and reviewed evidence.
- [ ] Independent ChatGPT scientific/numerical adversarial review with all blocking findings resolved; explicit owner authorization before merge.

**Explicit non-claims:** P1 does NOT reproduce Exodus patent FIGS. 4–8, validate a patent-specific H1 force law, establish exotic scalar EM waves, confirm anomalous propulsion, or reproduce an experiment. P2 is separate and remains blocked until P1 acceptance.

## First agent action

**ANTIGRAVITY / HERMES — PICK UP P1 ISSUE #6 NOW WHEN INVOKED.** Read current GitHub state and this handoff; make a prioritized implementation/test plan, then begin with P1-A analytic benchmark + convergence regression tests. Continue through P1-B/P1-C with isolated changes and independent validation. Do not stop at a plan, falsely claim CI, or post `READY FOR CHATGPT INDEPENDENT REVIEW` until there is reviewable code and actual CI evidence.
