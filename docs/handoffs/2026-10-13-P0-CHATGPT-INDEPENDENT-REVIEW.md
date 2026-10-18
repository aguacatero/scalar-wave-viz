# Scalar Wave Viz P0 — independent scientific review handoff

**Status: READY FOR CHATGPT INDEPENDENT R6 REVIEW. NOT APPROVED FOR MERGE.**

Updated 2026-10-18 after resolving the independent R5 review findings (R5-F1 through R5-F4). Persistent entry point for ChatGPT/Hermes/Antigravity independent review.

## Locate the work

- Repository: https://github.com/aguacatero/scalar-wave-viz
- PR: https://github.com/aguacatero/scalar-wave-viz/pull/5 (**draft**, base `main`)
- Branch: `scientific-baseline-exodus-2026-10-13`
- R5 Fix Queue Report: `docs/handoffs/2026-10-18-P0-CHATGPT-R5-FIX-QUEUE.md`
- Historical R4 Report: `docs/handoffs/2026-10-18-P0-CHATGPT-R4-FIX-QUEUE.md`
- Historical R3 Report: `docs/handoffs/2026-10-14-P0-CHATGPT-R3-FIX-QUEUE.md`
- Historical R1/R2 Report: `docs/handoffs/2026-10-13-P0-CHATGPT-R1-FIX-QUEUE.md`
- **Read PR head SHA at review time** for the current exact commit.
- P1 issue: https://github.com/aguacatero/scalar-wave-viz/issues/6
- P2 issue: https://github.com/aguacatero/scalar-wave-viz/issues/7
- Separate existing Jev draft: https://github.com/aguacatero/scalar-wave-viz/pull/4 (out of scope)

## Intended changes

1. `electrostatics_baseline.py`:
   - (R5-F1) Replaced `np.isclose` with exact criteria (`==`) in `check_configuration_symmetries`; added exact transformed fixed mask, conductor mask, and fixed potential parity verification on discrete solutions.
   - (R5-F2) Added `requested_probe_x_m` and `requested_probe_y_m` to `MeshRefinementResult`; added `assess_probe_convergence` rigorously splitting vacuum validity from quantitative convergence, checking row count and sampled coordinate stability.
   - (R5-F3) Added continuous geometry validation before rasterization in both `GroundedBoxConfig.__post_init__` and `electrode_pair_in_grounded_box` (checking continuous disk disjointness and enclosure boundary containment).
   - (R5-F4) Extracted `format_voltage_title` and `format_panel_a_title` using exact symmetry criteria.
2. `examples/electrostatics_demo.py`:
   - (R5-F2) Integrated `assess_probe_convergence`, serializing `requested_probe_xy_m`, `sampled_probe_coords`, and structured `probe_convergence_details` to JSON manifest; removed unconditional positive convergence statement from `epistemic_warning`.
   - (R5-F4) Use `format_panel_a_title(cfg)` to render Panel A title.
3. `tests/test_electrostatics_baseline.py`:
   - 30 unit tests (4 new targeted regressions for R5-F1, R5-F2, R5-F3, and R5-F4).

## Evidence obtained

- Local command `python3 -m unittest discover -s tests -v`: **30 tests passed** (including all F1–F6, R2-F1–R2-F5, R3-F1–R3-F3, R4-F1–R4-F3, and R5-F1–R5-F4 regression tests).
- Local command `MPLBACKEND=Agg python3 examples/electrostatics_demo.py`: writes `electrostatics_baseline.png` (2480 × 832) and paired `electrostatics_manifest.json` (schema 1.2.0); strict RFC 8259 JSON and provenance verified.
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
