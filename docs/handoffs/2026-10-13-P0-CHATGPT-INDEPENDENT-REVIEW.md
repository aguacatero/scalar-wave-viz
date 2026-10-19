# Scalar Wave Viz P0 — independent scientific review handoff

**Status: P0 SCIENTIFIC BASELINE ACCEPTED (R8 INDEPENDENT REVIEW) — PR #5 REMAINS DRAFT; AWAITING OWNER MERGE AUTHORIZATION.**

Updated 2026-10-18 after independent scientific R8 review explicitly accepted PR #5 P0 baseline. Persistent entry point and disposition record for ChatGPT/Hermes/Antigravity independent review.

## Locate the work

- Repository: https://github.com/aguacatero/scalar-wave-viz
- PR: https://github.com/aguacatero/scalar-wave-viz/pull/5 (**draft**, base `main`)
- Branch: `scientific-baseline-exodus-2026-10-13`
- **Accepted Code HEAD SHA:** `57067164b47d7d374a1d7bb1c8ce00bb79aa07f8`
- **Canonical R8 Acceptance Review:** https://github.com/aguacatero/scalar-wave-viz/pull/5#pullrequestreview-5566614469
- **Owner R8 Sign-Off / Pickup Comment:** https://github.com/aguacatero/scalar-wave-viz/pull/5#issuecomment-6259060825
- **Verified CI Run:** https://github.com/aguacatero/scalar-wave-viz/actions/runs/39187698432 (35 tests passed, provenance verified)
- **Verified Artifact:** https://github.com/aguacatero/scalar-wave-viz/actions/runs/39187698432/artifacts/12158189698
- **R8 Acceptance Ledger:** `docs/handoffs/2026-10-18-P0-CHATGPT-R8-ACCEPTED.md`
- Historical R7 Report: `docs/handoffs/2026-10-18-P0-CHATGPT-R7-FIX-QUEUE.md`
- Historical R6 Report: `docs/handoffs/2026-10-18-P0-CHATGPT-R6-FIX-QUEUE.md`
- Historical R5 Report: `docs/handoffs/2026-10-18-P0-CHATGPT-R5-FIX-QUEUE.md`
- Historical R4 Report: `docs/handoffs/2026-10-18-P0-CHATGPT-R4-FIX-QUEUE.md`
- Historical R3 Report: `docs/handoffs/2026-10-14-P0-CHATGPT-R3-FIX-QUEUE.md`
- Historical R1/R2 Report: `docs/handoffs/2026-10-13-P0-CHATGPT-R1-FIX-QUEUE.md`
- P1 issue: https://github.com/aguacatero/scalar-wave-viz/issues/6
- P2 issue: https://github.com/aguacatero/scalar-wave-viz/issues/7
- Separate existing Jev draft: https://github.com/aguacatero/scalar-wave-viz/pull/4 (out of scope)

## Accepted P0 Scope

1. `electrostatics_baseline.py`:
   - 2D finite-difference Dirichlet boundary solver for grounded metallic enclosure with conductor disks.
   - Physical conductor & boundary masking; continuous geometry probe checks (R7-F1).
   - Mesh refinement study with separate `is_stable` vs `is_converged` semantics (R7-F2).
   - Independent 1D ideal parallel-plate analytic benchmark with non-tautological reaction force balance summing to 0 N and virtual-work crosschecks.
2. `examples/electrostatics_demo.py`:
   - Dual-panel diagnostic figure visually separating 2D grounded-box field map from analytic parallel-plate comparison.
   - Machine-readable RFC 8259 JSON manifest with strict provenance (`git_commit_source_head`, `git_commit_tested_checkout`, base SHA disclosure).
3. `tests/test_electrostatics_baseline.py`:
   - 35 unit tests verifying numerical scaling, analytic formulas, symmetry preconditions, interface tractions, continuous boundary containment, and provenance.
4. Scientific governance:
   - `docs/SCIENCE_CHARTER.md`: Scientific integrity charter, falsification criteria, H0/H1 hypothesis separation.
   - `docs/EXODUS_MODEL_CONTRACT.md`: Audit of Exodus patent US11511891B2, listing missing parameters, contested derivations (Eq. 4, Eq. 11), and experimental null controls.
   - `docs/ROADMAP.md`: Phased milestone plan (P0 baseline -> P1 validation -> P2 patent geometry reproduction).

## Evidence obtained

- Local command `python3 -m unittest discover -s tests -v`: **35 tests passed** (0 failures, 0 errors).
- Local command `MPLBACKEND=Agg python3 examples/electrostatics_demo.py`: writes `electrostatics_baseline.png` (2480 × 832) and paired `electrostatics_manifest.json` (schema 1.2.0); strict RFC 8259 JSON and provenance verified.
- CI Workflow Run: https://github.com/aguacatero/scalar-wave-viz/actions/runs/39187698432 — all 35 tests passed, manifest provenance gate passed, artifact bundle `conventional-electrostatics-preview` (artifact ID 12158189698) uploaded and independently inspected.

## What the result does NOT establish

- No reproduction of specific Exodus patent geometry; the actual cited benchmark is **not** patent shape.
- No force from the 2D finite-difference fields; no force on the grounded box; no Maxwell-stress contour integration yet.
- No anomalous thrust, new electromagnetic scalar mode, unusual bismuth response or stable moscovium.
- No demonstrated numerical/outer-boundary convergence of the 2D field solver yet. The outer boundary is a **real grounded conductor**.
- No fixes to under-resolved/high-contrast legacy 3D wave solver yet.

## Code Tree vs Doc Updates

The accepted P0 implementation code tree is **frozen** at SHA `57067164b47d7d374a1d7bb1c8ce00bb79aa07f8`.  
Any subsequent commits updating documentation, handoffs, or AGENTS.md status are strictly doc-only commits and do not modify the verified simulation code or test suite.

## Reviewer acceptance / adversarial checklist (Historical Record)

1. Verify the analytic ideal parallel-plate pressure and stored-energy formulas and numerical test scaling. (VERIFIED R1–R8)
2. Prove the 2D Dirichlet matrix assembly is correct, and check the sign and units of the derived field components. (VERIFIED R1–R8)
3. Validate whether the plotted descriptions and bars make clear that two **different geometries** are displayed, and whether the signed forces are coordinate-orientation-dependent bookkeeping rather than general thrust predictions. (VERIFIED R2–R8)
4. Review the conductor-mask fix in `display_field_data` and its new regression test; verify fields are hidden inside conductors and assess misleading near-interface gradients. Require boundary/mesh convergence before interpreting electrode forces. (VERIFIED R3–R8)
5. Independently inspect `docs/EXODUS_MODEL_CONTRACT.md` against https://patents.google.com/patent/US11511891B2/en and the [Tajmar/Schreiber 2020 null tests](https://doi.org/10.1016/j.elstat.2020.103477). (VERIFIED R1–R8)
6. Confirm the actual CI status and downloadable artifact for the precise current HEAD; no inference from older green runs. (VERIFIED R8)
7. Evaluate epistemic labels in README/charter: no model output treated as empirical confirmation. (VERIFIED R1–R8)
8. Any discovered bug: submit reproducible finding with file/line and physical consequence, and require regression test in fix branch. (VERIFIED R1–R8)

## Autonomous Next Actions & Next Milestones

1. **Maintain PR #5 Draft Status:** PR #5 remains **DRAFT, OPEN, UNMERGED** pending explicit owner merge authorization.
2. **Implementation Freeze:** Stop changes to the accepted P0 code except independently reviewed fixes.
3. **P1 Milestone:** Next planned work is tracked under [Issue #6](https://github.com/aguacatero/scalar-wave-viz/issues/6) (numerical/outer-boundary convergence, whole-apparatus Maxwell stress and reaction forces).
4. **P2 Milestone:** Followed separately under [Issue #7](https://github.com/aguacatero/scalar-wave-viz/issues/7) (source-bound reproduction of patent FIGS. 4–8 geometry with H0/H1 controls).
