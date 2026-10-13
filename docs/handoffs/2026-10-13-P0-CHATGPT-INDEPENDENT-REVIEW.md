# Scalar Wave Viz P0 — independent scientific review handoff

**Status: READY FOR CHATGPT INDEPENDENT REVIEW. NOT APPROVED FOR MERGE.**

Updated 2026-10-13. Persistent entry point for a new ChatGPT/Hermes/Antigravity session.

## Locate the work

- Repository: https://github.com/aguacatero/scalar-wave-viz
- PR: https://github.com/aguacatero/scalar-wave-viz/pull/5 (**draft**, base `main`)
- Branch: `scientific-baseline-exodus-2026-10-13`
- Implementation commit before this handoff: `9e214db87052f0471d76a185761aa418fc895879`; **read PR head SHA at review time** for the current exact commit, and do not mistake docs-only handoff commits for physics changes.
- P1 issue: https://github.com/aguacatero/scalar-wave-viz/issues/6
- P2 issue: https://github.com/aguacatero/scalar-wave-viz/issues/7
- Separate existing Jev draft: https://github.com/aguacatero/scalar-wave-viz/pull/4 (out of scope)

## Intended changes

1. `electrostatics_baseline.py`: analytic ideal parallel-plate electrostatic pressure/force **and separately** a 2D Dirichlet finite-difference solution for a grounded box containing two circular conductive cross-sections.
2. `tests/test_electrostatics_baseline.py`: seven unit tests for ideal-plate laws, linear Laplace solution, electrode symmetry, fixed boundary potentials, and invalid inputs.
3. `examples/electrostatics_demo.py`: three-panel scientifically labeled static preview (V, |E| in kV/m, and signed force in µN from **a different idealized reference geometry**).
4. New scientific charter, Exodus source-bound force-model contract, roadmap, `AGENTS.md`, GitHub Actions test+figure-artifact workflow, and revised README marking all old exotic material speeds as what-if assumptions.

## Evidence obtained

- Local command `python -m unittest discover -s tests -v`: **7 tests passed** on 2026-10-13.
- Local command `MPLBACKEND=Agg python examples/electrostatics_demo.py`: wrote `electrostatics_baseline.png` (2240 × 768); visual appearance locally inspected.
- GitHub Actions on earlier code+AGENTS head `884c573323ab258c11dfac29102b74e062a3bba5`: push and pull_request runs both succeeded. Verify workflow for current PR head after subsequent README/artifact/handoff commits.
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
4. Identify ways numerical differentiation at sharp conducting boundaries could mislead interpretation; propose boundary/mesh convergence tests before interpreting electrode forces.
5. Independently inspect `docs/EXODUS_MODEL_CONTRACT.md` against https://patents.google.com/patent/US11511891B2/en and the [Tajmar/Schreiber 2020 null tests](https://doi.org/10.1016/j.elstat.2020.103477).
6. Confirm the actual CI status and downloadable artifact for the precise current HEAD; no inference from older green runs.
7. Evaluate epistemic labels in README/charter: no model output treated as empirical confirmation.
8. Any discovered bug: submit reproducible finding with file/line and physical consequence, and require regression test in fix branch.

## Implementation agent instructions

Follow `AGENTS.md`. For any finding, fix it in this branch, add regression coverage, rerun CI, update the code HEAD and regenerate review handoff. Keep PR draft. Do not call the work accepted until a truly independent adversarial re-review explicitly signs off. Do not merge without user authorization.

If accepted, next planned work is issue #6 (validated fields/forces), then issue #7 (reproduction of patent FIGS. 4–8). Do not shortcut H0/H1 separation.
