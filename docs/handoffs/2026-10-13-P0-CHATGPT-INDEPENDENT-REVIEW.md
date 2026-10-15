# Scalar Wave Viz P0 — independent scientific review handoff

**Status: READY FOR CHATGPT INDEPENDENT R4 REVIEW. NOT APPROVED FOR MERGE.**

Updated 2026-10-14 after resolving the independent R3 review findings (R3-F1 through R3-F3). Persistent entry point for ChatGPT/Hermes/Antigravity independent review.

## Locate the work

- Repository: https://github.com/aguacatero/scalar-wave-viz
- PR: https://github.com/aguacatero/scalar-wave-viz/pull/5 (**draft**, base `main`)
- Branch: `scientific-baseline-exodus-2026-10-13`
- R3 Fix Queue Report: `docs/handoffs/2026-10-14-P0-CHATGPT-R3-FIX-QUEUE.md`
- Historical R1/R2 Report: `docs/handoffs/2026-10-13-P0-CHATGPT-R1-FIX-QUEUE.md`
- **Read PR head SHA at review time** for the current exact commit.
- P1 issue: https://github.com/aguacatero/scalar-wave-viz/issues/6
- P2 issue: https://github.com/aguacatero/scalar-wave-viz/issues/7
- Separate existing Jev draft: https://github.com/aguacatero/scalar-wave-viz/pull/4 (out of scope)

## Intended changes

1. `electrostatics_baseline.py`:
   - (R3-F1) Implemented exact vertical electrode placement using `center_y_m` for left and right electrodes in mask generation: `(x - center_x_m)**2 + (y - center_y_m)**2 <= radius_m**2`. Added finite-coordinate validation in `ElectrodeConfig` and `GroundedBoxConfig`.
   - (R3-F2) Enabled `electrode_pair_mesh_study` to accept typed `GroundedBoxConfig`, ensuring custom runs vary only grid resolution $n$ while strictly preserving configured geometries and voltages.
2. `examples/electrostatics_demo.py`:
   - (R3-F2) Pass active `config=cfg` directly to `electrode_pair_mesh_study`; serialize `mesh_study_geometry` in manifest to preserve custom study provenance.
   - (R3-F3) Implemented `get_git_provenance()` distinguishing PR source branch HEAD SHA (`pr_source_head_sha`) from GitHub Actions CI synthetic merge commit (`tested_checkout_sha`). Bumped schema to `1.1.0`.
3. `.github/workflows/physics-tests.yml`:
   - (R3-F3) Passed `PR_SOURCE_HEAD_SHA`, `PR_BASE_SHA`, and `GITHUB_EVENT_NAME` to demo execution; added a manifest provenance verification gate step.
4. `tests/test_electrostatics_baseline.py`:
   - 23 unit tests (3 new targeted regression tests for R3-F1, R3-F2, and R3-F3).

## Evidence obtained

- Local command `python3 -m unittest discover -s tests -v`: **23 tests passed** (including all F1–F6, R2-F1 through R2-F5, and R3-F1 through R3-F3 regression tests).
- Local command `MPLBACKEND=Agg python3 examples/electrostatics_demo.py`: writes `electrostatics_baseline.png` (2480 × 832) and paired `electrostatics_manifest.json` (schema 1.1.0); visual appearance and provenance verified.
- Workflow uploads downloadable artifact bundle named `conventional-electrostatics-preview` containing both PNG and JSON manifest (30-day retention). Link: https://github.com/aguacatero/scalar-wave-viz/actions/workflows/physics-tests.yml

## What the result does NOT establish

- No reproduction of specific Exodus patent geometry; the actual cited benchmark is **not** patent shape.
- No force from the 2D finite-difference fields; no force on the grounded box; no Maxwell-stress contour integration yet.
- No anomalous thrust, new electromagnetic scalar mode, unusual bismuth response or stable moscovium.
- No demonstrated numerical/outer-boundary convergence of the 2D field solver yet. The outer boundary is a **real grounded conductor**.
- No fixes to under-resolved/high-contrast legacy 3D wave solver yet.

## Reviewer acceptance / adversarial checklist

1. Verify the analytic ideal parallel-plate pressure and stored-energy formulas and numerical test scaling.
2. Prove the 2D Dirichlet matrix assembly is correct, and check the sign and units of the derived field components.
3. Validate whether the plotted descriptions and bars make clear that two **different geometries** are displayed, and whether the signed forces are coordinate-orientation-dependent bookkeeping rather than general thrust predictions.
4. Review the conductor-mask fix in `display_field_data` and its new regression test; verify fields are hidden inside conductors and assess misleading near-interface gradients. Require boundary/mesh convergence before interpreting electrode forces.
5. Independently inspect `docs/EXODUS_MODEL_CONTRACT.md` against https://patents.google.com/patent/US11511891B2/en and the [Tajmar/Schreiber 2020 null tests](https://doi.org/10.1016/j.elstat.2020.103477).
6. Confirm the actual CI status and downloadable artifact for the precise current HEAD; no inference from older green runs.
7. Evaluate epistemic labels in README/charter: no model output treated as empirical confirmation.
8. Any discovered bug: submit reproducible finding with file/line and physical consequence, and require regression test in fix branch.

## Implementation agent instructions

Follow `AGENTS.md`. For any finding, fix it in this branch, add regression coverage, rerun CI, update the code HEAD and regenerate review handoff. Keep PR draft. Do not call the work accepted until a truly independent adversarial re-review explicitly signs off. Do not merge without user authorization.

If accepted, next planned work is issue #6 (validated fields/forces), then issue #7 (reproduction of patent FIGS. 4–8). Do not shortcut H0/H1 separation.

## Important pending scientific scope

This code is **only P0**. The signed bar-force chart is an independent analytic parallel-plate comparison; it is **not derived** from the adjacent grounded-box field map, and a shared title must not create false causal linkage. No analytic Maxwell-stress integration of the plotted electrode pair is present. Treat the independent reviewer acceptance gate as still open even with green CI. In particular, independently check equations and boundary models, and inspect the **latest** CI-generated figure rather than an earlier local PNG.
