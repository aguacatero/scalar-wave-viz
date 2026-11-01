# SCALAR WAVE VIZ — Phase P2 R7 Remediation Plan

**Repository:** `aguacatero/scalar-wave-viz`  
**PR:** https://github.com/aguacatero/scalar-wave-viz/pull/11  
**Issue:** https://github.com/aguacatero/scalar-wave-viz/issues/7  
**Branch:** `p2-patent-geometry-exodus-2026-10-25`  
**Governing Review:** Independent Scientific Review P2 R6 ([issuecomment-6553125965](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6553125965))  
**Operating Mode:** MANUAL-ONLY  
**Merge Authorization:** NOT GRANTED  

---

## 1. Objectives & Review Finding Breakdown

Address all four High findings (`P2-R6-F1`, `P2-R6-F2`, `P2-R6-F3`, `P2-R6-F4`) and two Medium findings (`P2-R6-M1`, `P2-R6-M2`) from ChatGPT's P2 R6 independent review.

| Finding ID | Severity | Core Root Cause | Planned Technical Remediation |
| :--- | :--- | :--- | :--- |
| **`P2-R6-F1`** | **HIGH** | 1. `run_3d_mesh_convergence_study` defaulted to `refine_z=False`; FIG. 21 only refined x/y.<br>2. Sourced ground plane thickness $T_2 = 0.25\text{ mm}$ was misrepresented as $1.27\text{ mm}$ with claim of ratio 1.0000; thin-sheet discretization was obscured.<br>3. FIG. 21 convergence test lacked 3-level triplet, per-body numerical tables, and predeclared tolerances.<br>4. Longitudinal $u_{\text{mesh},z}$ claimed $0.05\ \mu\text{N}$ without an exposed numerical bound in the solver. | 1. Make `refine_z=True` default and execute 3-level commensurate full 3D refinement on FIG. 21.<br>2. Reconcile $T_2 = 0.25\text{ mm}$ (`EXTERNAL_ESTIMATE_FOR_UNSPECIFIED`) truthfully. Discretize $n_{\text{gnd}} = \max(1, \text{round}(T_2/dx))$, report actual thickness $n_{\text{gnd}} \times dx$, and explicitly report discretization ratios ($5.08, 2.54, 1.69$) in all docs and tests without claiming 1.0000.<br>3. Run 3-level full 3D sequence on FIG. 21, asserting predeclared per-body tolerances on blade, ground, dielectric, wall, net, and H1 quantities.<br>4. Compute and expose actual longitudinal discretization bound $u_{\text{mesh},z} = |F_{z1} - F_{z2}| / (r_z - 1)$ in Newtons in `Finite3DModelResult`. |
| **`P2-R6-F2`** | **HIGH** | 1. Domain clearance uncertainty equated to wall force $|F_{\text{wall}}|$, rather than boundary sensitivity.<br>2. Missing parameter uncertainty was pseudo-quantified as $50\ \mu\text{N}$ without calibration sweeps.<br>3. Gate received blade-only Richardson difference rather than multi-body convergence evidence. | 1. Implement paired matched-grid clearance sensitivity function `calibrate_domain_clearance_uncertainty_3d` computing $|F_{\text{blade}}(U_{\text{expanded}}) - F_{\text{blade}}(U_{\text{nominal}})|$.<br>2. Report unbounded model parameters explicitly as unquantified/unbounded rather than a fixed pseudo-calibrated $50\ \mu\text{N}$.<br>3. Track multi-body convergence (maximum error across all bodies and net closure) in decision budget. |
| **`P2-R6-F3`** | **HIGH** | Production gate used `not whole_body_status.startswith("UNVERIFIED")`, which accepted `VACUUM_NO_DIELECTRIC_UNVERIFIED_PENDING_CONVERGENCE` because it did not start with `"UNVERIFIED"`. Gate lacked input validation for non-finite/negative inputs. | 1. Define explicit `VERIFIED_WHOLE_BODY_STATES` frozenset allowlist. Only allowlisted states pass the gate.<br>2. Add strict input validation rejecting NaN, Inf, negative, empty, or None uncertainties.<br>3. Add adversarial unit tests verifying fail-closed behavior on `VACUUM_NO_DIELECTRIC_UNVERIFIED_PENDING_CONVERGENCE`, all actual dielectric states, invalid inputs, and empty strings. |
| **`P2-R6-F4`** | **HIGH** | FIG. 21 dielectric interface-to-contour discrepancy was only asserted nonzero, not bounded or analyzed across meshes/permittivities. Whole-body closure remains unverified. | 1. Track interface-to-contour agreement metric across FIG. 21 mesh refinement levels and across permittivity values ($\varepsilon_r = 2.0, 3.8, 5.0$).<br>2. Clearly document constitutive Korteweg-Helmholtz traction assumptions and Cartesian staircasing limitations.<br>3. Preserve `whole_body_3d_mechanical_accounting = "UNVERIFIED_PENDING_CONFORMING_INTERFACE_MESHING"` and fail closed in the gate. |
| **`P2-R6-M1`** | **MED** | Claimed uniform-field validation for 3D H1 quadrature called a 2D benchmark and inspected text, rather than testing the actual 3D numerical quadrature function on a 3D field array. | 1. Extract pure function `compute_3d_patent_face_h1_quadrature` in `exodus_hypothesis_evaluator.py`.<br>2. In `test_true_3d_patent_face_h1_uniform_field_analytic_benchmark`, construct a known 3D field array on a grid with known faces, run the quadrature function, and assert exact agreement with $E^2 A$ analytical formulas to $< 10^{-12}$.<br>3. Test on non-uniform field verifying strict Cauchy-Schwarz inequality, test controlled face offset sensitivity, and perform full surface normal/area audit. Label provisional. |
| **`P2-R6-M2`** | **MED** | Manifest generator hardcoded `"governing_review": "P2_R4_REMEDIATION"`. | 1. Define `CURRENT_GOVERNING_REVIEW = "P2_R6_REMEDIATION"` at module level.<br>2. Pass and serialize governing review dynamically in `generate_exodus_patent_manifest`.<br>3. Add unit test asserting `manifest["git_provenance"]["governing_review"] == "P2_R6_REMEDIATION"`. |

---

## 2. Implementation Steps

1. **Step 1: Core Pure Functions in [`exodus_hypothesis_evaluator.py`](file:///Users/chrisrodriguez/Documents/scalar-wave/exodus_hypothesis_evaluator.py):**
   - Extract `compute_3d_patent_face_h1_quadrature`.
   - Implement `calibrate_domain_clearance_uncertainty_3d`.
   - Update `evaluate_physical_scale_discrimination_gate` with strict allowlist and robust input validation.
   - Refactor `run_3d_mesh_convergence_study` and `run_3d_z_mesh_convergence_study` with full 3D refinement (`refine_z=True` default), axial bound $u_{\text{mesh},z}$, and multi-body convergence metrics.
   - Update `generate_exodus_patent_manifest` with dynamic `governing_review = "P2_R6_REMEDIATION"`.
2. **Step 2: Update [`tests/test_p2_exodus_patent.py`](file:///Users/chrisrodriguez/Documents/scalar-wave/tests/test_p2_exodus_patent.py):**
   - Implement true 3D uniform-field & non-uniform analytic benchmark for `compute_3d_patent_face_h1_quadrature`.
   - Update `test_fig21_nine_blade_multilevel_mesh_convergence` to 3 levels with full 3D refinement, per-body tables, and predeclared tolerances.
   - Update ground thickness assertions to verify true physical discretization ratios ($5.08, 2.54, 1.69$).
   - Add adversarial unit tests for gate allowlist and input validation.
   - Add regression for manifest governing review.
3. **Step 3: Verification & Execution:**
   - Run full unit test suite, verify P0 hash, regenerate artifacts, update docs, commit, push, verify CI, and post timestamped R7 handoff.
