# Scalar Wave Viz P0 — independent scientific review handoff

**Status: READY FOR CHATGPT INDEPENDENT REVIEW. NOT APPROVED FOR MERGE.**

Updated 2026-10-13 after preliminary figure-mask review. Persistent entry point for a new ChatGPT/Hermes/Antigravity session.

## Locate the work

- Repository: https://github.com/aguacatero/scalar-wave-viz
- PR: https://github.com/aguacatero/scalar-wave-viz/pull/5 (**draft**, base `main`)
- Branch: `scientific-baseline-exodus-2026-10-13`
- Current physics-and-figure code commit: `2b180d6916d95978062ded6a6f6cbad7bfe301b3` (8-test version); **read PR head SHA at review time** for the current exact commit, and do not mistake docs-only handoff commits for physics changes.
- P1 issue: https://github.com/aguacatero/scalar-wave-viz/issues/6
- P2 issue: https://github.com/aguacatero/scalar-wave-viz/issues/7
- Separate existing Jev draft: https://github.com/aguacatero/scalar-wave-viz/pull/4 (out of scope)

## Intended changes

1. `electrostatics_baseline.py`: analytic ideal parallel-plate electrostatic pressure/force **and separately** a 2D Dirichlet finite-difference solution for a grounded box containing two circular conductive cross-sections.
2. `tests/test_electrostatics_baseline.py`: eight unit tests for ideal-plate laws, linear Laplace solution, electrode symmetry, fixed boundary potentials, and invalid inputs.
3. `examples/electrostatics_demo.py`: three-panel scientifically labeled static preview (V, |E| in kV/m, and signed force in µN from **a different idealized reference geometry**). Latest improvement masks field/color/arrows within fixed-potential conducting cells and shows unit direction arrows only in vacuum; specifically test this.
4. New scientific charter, Exodus source-bound force-model contract, roadmap, `AGENTS.md`, GitHub Actions test+figure-artifact workflow, and revised README marking all old exotic material speeds as what-if assumptions.

## Evidence obtained

- Initial local command `python -m unittest discover -s tests -v`: **7 tests passed**; updated code at `2b180d691` has **8 tests passed on GitHub Actions**, including a visualization-regression test.
- Local command `MPLBACKEND=Agg python examples/electrostatics_demo.py`: wrote `electrostatics_baseline.png` (2240 × 768); visual appearance locally inspected.
- GitHub Actions push and pull_request succeeded for latest physics code HEAD `2b180d6916d95978062ded6a6f6cbad7bfe301b3`, including 8 tests, static plot and artifact upload. Pull-request CI: https://github.com/aguacatero/scalar-wave-viz/actions/runs/38441594552 . Subsequent handoff/documentation commits require checking their new CI result.
- Workflow now uploads downloadable artifact named `conventional-electrostatics-preview` (30-day retention). Link: https://github.com/aguacatero/scalar-wave-viz/actions/workflows/physics-tests.yml

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
