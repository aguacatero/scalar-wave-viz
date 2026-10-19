# P0 Scientific Baseline — ChatGPT Independent R8 Sign-Off / Acceptance Ledger

**REVIEW DISPOSITION: ACCEPTED (R8 INDEPENDENT REVIEW) — P0 SCIENTIFIC BASELINE SIGNED OFF. PR REMAINS DRAFT; AWAITING OWNER MERGE AUTHORIZATION.**  
Date: 2026-10-18. Persistent handoff and disposition ledger recording independent scientific sign-off for PR #5 P0 baseline.

---

## 1. Immutable Review Baseline (R8)

- **Repository:** https://github.com/aguacatero/scalar-wave-viz
- **Draft PR:** https://github.com/aguacatero/scalar-wave-viz/pull/5 (base `main`)
- **Branch:** `scientific-baseline-exodus-2026-10-13`
- **Accepted Code HEAD SHA:** `57067164b47d7d374a1d7bb1c8ce00bb79aa07f8`
- **Canonical Independent R8 Review URL:** https://github.com/aguacatero/scalar-wave-viz/pull/5#pullrequestreview-5566614469
- **Owner R8 Sign-Off / Pickup Comment:** https://github.com/aguacatero/scalar-wave-viz/pull/5#issuecomment-6259060825
- **Verified CI Run at Accepted HEAD:** https://github.com/aguacatero/scalar-wave-viz/actions/runs/39187698432
  - Job logs: **Ran 35 tests / OK** (0 failures, 0 errors)
  - Manifest provenance gate passed
  - Artifact upload confirmed
- **Independently Inspected Artifact Bundle:** https://github.com/aguacatero/scalar-wave-viz/actions/runs/39187698432/artifacts/12158189698
  - Verified 2480 × 832 PNG (`electrostatics_baseline.png`)
  - Strict RFC 8259 JSON manifest (`electrostatics_manifest.json`, schema 1.2.0)
  - Both PR source head and tested checkout SHA match `57067164b47d7d374a1d7bb1c8ce00bb79aa07f8`

---

## 2. Review Findings Verified Resolved

### R7-F1 (Continuous requested-probe geometry vacuum guard) — PASS
- **Resolution:** In `electrode_pair_mesh_study` (`electrostatics_baseline.py`), continuous electrode and grounded enclosure wall geometry is verified directly at requested physical coordinates `(requested_probe_x_m, requested_probe_y_m)`, independently of discrete snapped lattice node membership.
- **Behavior:** Physical penetration into conductors or walls raises `ValueError` in strict mode (`require_vacuum_probe=True`). In non-strict mode, sets fields to `None`/`null` and assigns `NON_VACUUM` probe status. `requested_probe_in_vacuum` and `sampled_node_in_vacuum` are exposed separately in `MeshRefinementResult` and serialized in `mesh_study_probe` table in `electrostatics_manifest.json`.
- **Regression:** `test_r7_f1_requested_probe_continuous_conductor_membership` covers strict rejection, non-strict masking, `assess_probe_convergence` fail-closed behavior, manifest serialization, and outer-boundary penetration.

### R7-F2 (Stability-only diagnostic vs formal convergence flag) — PASS
- **Resolution:** In `assess_probe_convergence` (`electrostatics_baseline.py`), finite-grid stability within tolerance returns `convergence_status='STABLE_WITHIN_TESTED_GRID_TOLERANCE'`, with `is_stable=True` but explicitly `is_converged=False`. The flag `is_converged` is strictly reserved for formal asymptotic convergence proofs (such as Richardson extrapolation).
- **Behavior:** Serialized manifest includes `is_stable: true`, `is_converged: false`, explicit `convergence_flag_note` explanation, and overall Case 1 status `ILLUSTRATIVE / NON-CONVERGED`.
- **Regression:** `test_r7_f2_stability_flag_distinction_and_manifest_flags` verifies both dataclass evaluation and JSON manifest serialization.

---

## 3. Test Suite & Baseline Health

- **Total unit tests:** **35 passed** (0 failures, 0 errors).
- **Regression coverage:** Comprehensive coverage of F1–F6, R2-F1–R2-F5, R3-F1–R3-F3, R4-F1–R4-F3, R5-F1–R5-F4, R6-F1–R6-F3, and R7-F1–R7-F2.
- **Local test command:** `python3 -m unittest discover -s tests -v`
- **Demo execution:** `MPLBACKEND=Agg python3 examples/electrostatics_demo.py` generates valid 2480 × 832 PNG and RFC 8259 compliant JSON manifest with full provenance.

---

## 4. Epistemic Scope and Explicit Non-Claims

This sign-off applies strictly to the **P0 conventional electrostatic baseline** and scientific governance foundation:
1. **No patent geometry reproduction:** Plotted electrode disks are an idealized baseline inside a grounded box; they do not reproduce Exodus patent US11511891B2 FIGS. 4–8.
2. **No net thrust claim:** Plotted Case 2 forces are equal-and-opposite reactions on ideal parallel plates summing to 0 N. No anomalous propulsion or net mechanical thrust is established.
3. **No novel field physics:** No scalar electromagnetic mode, unusual materials (e.g. bismuth/moscovium), or non-Maxwellian effects are validated.
4. **No whole-device stress tensor:** 2D finite-difference field plot does not evaluate Maxwell-stress boundary integrals or reaction forces on the grounded enclosure; outer boundary and mesh convergence are not yet asymptotically established.

---

## 5. Autonomous Status and Next Milestones

1. **P0 Code Frozen:** Code tree at SHA `57067164b47d7d374a1d7bb1c8ce00bb79aa07f8` is frozen. Subsequent documentation updates are tracked separately as doc-only commits without misrepresenting the accepted implementation SHA.
2. **PR #5 Lifecycle:** PR #5 remains **DRAFT, OPEN, UNMERGED** pending explicit repository owner authorization. Agents must not self-approve or merge.
3. **P1 Milestone:** Next work is tracked separately under **Issue #6**:
   - Numerical/outer-boundary convergence of electrostatic solver.
   - Maxwell-stress contour integration and reaction accounting for the whole apparatus (electrodes, grounded shield, supports).
   - Validated absorbing boundaries and dispersion benchmarks for legacy 3D wave solver.
4. **P2 Milestone:** Followed separately under **Issue #7**:
   - Sourced, reproducible reproduction of Exodus patent FIGS. 4–8 geometry with strict H0/H1 separation and experimental null controls.
