# P0 Scientific Baseline — ChatGPT Independent R7 Findings / Antigravity Fix Queue

**REVIEW DISPOSITION: CHANGES REQUIRED (R7) — RESOLVED FOR R8 RE-REVIEW. PR REMAINS DRAFT.**
Date: 2026-10-18. Persistent handoff and fix ledger resolving independent review findings R7-F1 through R7-F2.

## 1. Immutable Review Baseline (R7)

- **Repository:** https://github.com/aguacatero/scalar-wave-viz
- **Draft PR:** https://github.com/aguacatero/scalar-wave-viz/pull/5
- **Branch:** `scientific-baseline-exodus-2026-10-13`
- **Reviewed Code Baseline (R7):** `de2f51a264066c1332702ecfee02e713d9115030`
- **Independent R7 Review URL:** https://github.com/aguacatero/scalar-wave-viz/pull/5#pullrequestreview-5566144721
- **Owner R8 Pickup Instructions:** https://github.com/aguacatero/scalar-wave-viz/pull/5#issuecomment-6257895991
- **Verified CI at R7 HEAD:** Run 39174479049 (33 tests passed, artifact bundle 12153847013 downloaded and inspected).

---

## 2. Unresolved R7 Findings & Exact Resolutions

### R7-F1 — MED: Requested probe physically inside a conductor escapes the grid-node-only vacuum guard

- **Finding:** In `electrode_pair_mesh_study`, `probe_in_vac` previously evaluated `bool(sol.vacuum_mask[ix, iy])`, checking only the nearest snapped lattice node. At $n=41$, box width $0.04\text{ m}$, default left disk center $(-0.008\text{ m}, 0.0\text{ m})$, and radius $0.003\text{ m}$, a requested probe point $(-0.00549\text{ m}, 0.0006\text{ m})$ is physically inside the left conductor disk (distance $\approx 0.0025807\text{ m} \le 0.003\text{ m}$). However, the nearest lattice node $(-0.005\text{ m}, 0.001\text{ m})$ lies in vacuum (distance $\approx 0.0031623\text{ m} > 0.003\text{ m}$). `require_vacuum_probe=True` therefore passed incorrectly and exposed numerical finite vacuum field values for a point located inside an ideal conductor.
- **Resolution:**
  - In `MeshRefinementResult`: added `requested_probe_in_vacuum: bool = True` and `sampled_node_in_vacuum: bool = True`.
  - In `electrode_pair_mesh_study`:
    - Evaluated continuous physical geometry membership at requested coordinates: checked distance to left disk center, distance to right disk center, and outer enclosure boundaries.
    - Evaluated discrete lattice membership at nearest snapped node `sol.vacuum_mask[ix, iy]`.
    - Enforced `probe_in_vac = bool(requested_in_vac and sampled_node_in_vac)`.
    - If `require_vacuum_probe=True` and `not requested_in_vac`: raises `ValueError` with exact continuous distance and conductor location.
    - If `require_vacuum_probe=False` and `not requested_in_vac`: masks field values (`probe_ex_v_per_m = None`, `probe_ey_v_per_m = None`) and records descriptive `NON_VACUUM` probe status.
  - In `examples/electrostatics_demo.py` (`generate_manifest`): serialized `requested_probe_in_vacuum` and `sampled_node_in_vacuum` in `mesh_study_probe`.
- **Regression:**
  - Added `test_r7_f1_requested_probe_continuous_conductor_membership` in `tests/test_electrostatics_baseline.py`:
    - Tests the exact review reproduction: $n=41$, $W=0.04\text{ m}$, left disk $(-0.008\text{ m}, 0.0\text{ m})$, radius $0.003\text{ m}$, probe $(-0.00549\text{ m}, 0.0006\text{ m})$.
    - Asserts `require_vacuum_probe=True` raises `ValueError` citing physical conductor membership.
    - Asserts non-strict mode records `requested_probe_in_vacuum=False`, `sampled_node_in_vacuum=True`, `probe_in_vacuum=False`, and `None` fields.
    - Asserts `assess_probe_convergence` fails closed to `vacuum_status='NON_VACUUM'` and `convergence_status='NOT_ASSESSED'`.
    - Asserts manifest generation serializes `null` field values and `NON_VACUUM` details.
    - Asserts continuous boundary penetration check rejects points outside enclosure walls.

### R7-F2 — MED: Stability-only diagnostic leaks is_converged=true into machine-readable manifest

- **Finding:** When `assess_probe_convergence` evaluated finite grid drift within tolerance across tested resolutions, it returned `convergence_status='STABLE_WITHIN_TESTED_GRID_TOLERANCE'`, but set `is_converged=True` alongside `is_stable=True`. Setting `is_converged=True` upgraded coarse finite-grid stability to a claim of verified mathematical convergence in a machine-readable flag, contradicting Case 1's illustrative/non-converged validation status.
- **Resolution:**
  - In `electrostatics_baseline.py`:
    - In `ProbeConvergenceAssessment`: documented that `is_converged` is strictly reserved for formal asymptotic convergence proofs (e.g. Richardson extrapolation / formal rate verification), while finite-grid stability is reported by `is_stable`.
    - In `assess_probe_convergence`: for `STABLE_WITHIN_TESTED_GRID_TOLERANCE`, set `is_converged=False` and `is_stable=True`.
  - In `examples/electrostatics_demo.py` (`generate_manifest`):
    - Added `convergence_flag_note` in `probe_convergence_details` explaining that `is_converged` is reserved for formal asymptotic convergence proofs, and finite-grid stability is indicated by `is_stable`.
- **Regressions:**
  - Updated existing tests (`test_r5_f2`, `test_r6_f3`) to assert `is_converged is False` and `is_stable is True`.
  - Added `test_r7_f2_stability_flag_distinction_and_manifest_flags` in `tests/test_electrostatics_baseline.py`:
    - Asserts direct `assess_probe_convergence` returns `is_stable=True` and `is_converged=False`.
    - Asserts serialized JSON manifest records `is_stable: true`, `is_converged: false`, `convergence_flag_note`, and `validation_status: 'ILLUSTRATIVE / NON-CONVERGED'`.

---

## 3. Test Suite Summary

- Total unit tests: **35 passed** (0 failures, 0 errors; up from 33 in R7).
- All previous regression gates (F1–F6, R2-F1–R2-F5, R3-F1–R3-F3, R4-F1–R4-F3, R5-F1–R5-F4, R6-F1–R6-F3) remain green.
- Local command: `python3 -m unittest discover -s tests -v`
