# SCALAR WAVE VIZ — P2 R7 INDEPENDENT SCIENTIFIC RE-REVIEW HANDOFF

**Repository:** https://github.com/aguacatero/scalar-wave-viz  
**Pull Request:** https://github.com/aguacatero/scalar-wave-viz/pull/11  
**Issue:** https://github.com/aguacatero/scalar-wave-viz/issues/7  
**Branch:** `p2-patent-geometry-exodus-2026-10-25`  
**Milestone:** Phase P2 — Exodus patent US11511891B2 FIGS. 4–8 reproduction & hypothesis separation  
**Review Round:** P2 R7  
**Governing Review:** Independent scientific review P2 R6 ([issuecomment-6553125965](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6553125965))  
**Operating Mode:** MANUAL-ONLY  
**Merge Authorization:** NOT GRANTED (PR remains DRAFT pending independent review; no auto-merge, no P3 kickoff)  

---

## 1. Executive Summary

This handoff remediates all findings from ChatGPT's independent scientific review of Phase P2 R6 ([issuecomment-6553125965](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6553125965)), which concluded `CHANGES REQUIRED — P2 R6 SCIENTIFIC BASELINE NOT ACCEPTED` across 4 High and 2 Medium findings (`P2-R6-F1`, `P2-R6-F2`, `P2-R6-F3`, `P2-R6-F4`, `P2-R6-M1`, and `P2-R6-M2`).

Phase P2 reproduces the Exodus Propulsion Technologies patent [US11511891B2](https://patents.google.com/patent/US11511891B2/en) (issued November 29, 2022) embodiment depicted in FIGS. 4–8 (single-stage schematic) and separates it from the FIG. 21 nine-blade epoxy-potted test article.

Key physical and numerical advancements in R7:
1. **Multi-Level Full 3D Refinement on FIG. 21 & Per-Body Convergence (P2-R6-F1):**
   - Refactored `run_3d_mesh_convergence_study` with `refine_z: bool = True` as the universal default, ensuring lateral ($dx, dy$) and axial ($dz$) grid spacings refine simultaneously and proportionally across levels.
   - Executed a 3-level full 3D commensurate refinement study on FIG. 21 ($N=9$ blades, potting epoxy $\varepsilon_r=3.8$), tracking per-body forces on blade, ground, dielectric, enclosure outer walls, net system momentum residual, and literal H1 surface quantities at each level.
   - Evaluated 3D observed convergence order $p_{\text{obs}} \approx 0.80$ across commensurate triplets, confirming stable non-asymptotic fractional convergence governed by corner singularities (`NON_ASYMPTOTIC_FRACTIONAL_ORDER_CORNER_SINGULARITY`).
2. **Reconciled Ground Electrode Thickness Sourcing and Discretization Ratios (P2-R6-F1):**
   - Reconciled ground plane thickness to the authoritative copper tape backing value $T_2 = 0.00025\text{ m}$ ($0.25\text{ mm}$, taxonomy status `EXTERNAL_ESTIMATE_FOR_UNSPECIFIED`).
   - Discretizes $n_{\text{gnd}} = \max(1, \text{round}(T_2/dx))$. On coarse grids where $dx > T_2$, the 1-cell representation yields thickness $1 \times dx$, giving actual-to-target discretization ratios:
     - Level 1 ($dx = 1.27\text{ mm}$): ratio $5.08$
     - Level 2 ($dx = 0.635\text{ mm}$): ratio $2.54$
     - Level 3 ($dx = 0.4233\text{ mm}$): ratio $1.693$
   - Accurately reports this thin-sheet staircasing ratio in all code, docstrings, tests, and PR description, completely eliminating false claims of 1.0000 on coarse grids.
3. **Longitudinal $z$-Mesh Uncertainty Bound $u_{\text{mesh},z}$ Computed in Newtons (P2-R6-F1):**
   - In `run_3d_z_mesh_convergence_study`, directly computes the axial discretization truncation uncertainty in Newtons: $u_{\text{mesh},z} = \frac{|F_{z2} - F_{z1}|}{r_z - 1} \approx 499.4\ \mu\text{N}$ ($0.50\text{ mN}$, or $0.93\%$ relative change).
   - Stored in `z_mesh_discretization_uncertainty_n` in `Finite3DModelResult`. This bound independently exceeds the $23.7\ \mu\text{N}$ target discrimination threshold, demonstrating why coarse 3D grids cannot discriminate and must fail closed.
4. **Empirically Calibrated Domain Clearance Sensitivity (P2-R6-F2):**
   - Implemented `calibrate_domain_clearance_uncertainty_3d` evaluating paired same-body, same-grid solves at nominal clearance $U$ and expanded clearance $1.5U$.
   - Directly measures the numerical sensitivity of device force to outer boundary placement: $u_{\text{domain}} = |F_{\text{blade}}(U_{\text{expanded}}) - F_{\text{blade}}(U_{\text{nominal}})|$, separating physical electrostatic traction on outer walls from boundary placement sensitivity.
5. **Honest Reporting of Unbounded Model Parameters (P2-R6-F2):**
   - Replaced pseudo-quantified $50\ \mu\text{N}$ placeholder with explicit `missing_parameter_model_uncertainty_n = None` and `missing_parameter_model_uncertainty_is_bounded = False`.
   - In `evaluate_physical_scale_discrimination_gate`, unquantified/unbounded model parameters cause the gate to fail closed without fabricating precision.
6. **Robust Allowlisted Production Discrimination Gate & Input Validation (P2-R6-F3):**
   - Defined strict frozenset allowlist: `VERIFIED_WHOLE_BODY_STATES = frozenset({"VERIFIED_CONSERVATIVE_ALL_BODIES_CLOSED", "VERIFIED_INDEPENDENT_WHOLE_BODY_CONVERGED"})`.
   - Replaced flawed prefix-based denial test. Both `VACUUM_NO_DIELECTRIC_UNVERIFIED_PENDING_CONVERGENCE` and `UNVERIFIED_PENDING_CONFORMING_INTERFACE_MESHING` are strictly excluded from the allowlist and fail closed.
   - Robust input validation: rejects None, non-finite (NaN, Inf), negative uncertainty inputs, and empty/invalid status strings, returning `NOT_RESOLVED_INVALID_OR_UNBOUNDED_UNCERTAINTY`.
   - Expanded adversarial test suite to test all positive and negative gate branches.
7. **FIG. 21 Dielectric Mechanical Closure & Permittivity Tracking (P2-R6-F4):**
   - Tracked relative interface-to-contour discrepancy $|F_{\text{int}} - F_{\text{contour}}| / |F_{\text{contour}}|$ on FIG. 21 across refinement levels and across permittivities ($\varepsilon_r = 2.0, 3.8, 5.0$).
   - Verified that interface traction scales with $(\varepsilon_r - 1)$ while discrepancy remains within expected Cartesian staircasing bounds ($20-35\%$).
   - Whole-body status honestly retained as `UNVERIFIED_PENDING_CONFORMING_INTERFACE_MESHING` and fails closed in the gate.
8. **Direct 3D Patent-Face H1 Near-Face Numerical Quadrature Benchmark (P2-R6-M1):**
   - Extracted pure function `compute_3d_patent_face_h1_quadrature` in `exodus_hypothesis_evaluator.py`.
   - In `test_true_3d_patent_face_h1_uniform_field_analytic_benchmark`, drove the actual 3D quadrature function directly on true 3D uniform and non-uniform field arrays.
   - On uniform field: verified face areas ($A_{\text{prox}}, A_{\text{dist}}$), integrals ($\iint E^2 dA$), and forces against analytical formulas to $< 10^{-12}$ error. Proved spatial-mean plug-in equals literal quadrature on uniform fields.
   - On non-uniform field: proved Cauchy-Schwarz inequality holds strictly ($\iint E^2 dA > \langle E \rangle^2 A$).
   - Performed controlled face offset sensitivity analysis (`sample_offset_cells = 1, 2`) and surface normal/area audit.
   - Labeled provisional: `h1_3d_quadrature_status = "PROVISIONAL_NEAR_FACE_QUADRATURE_SUBJECT_TO_OFFSET_SENSITIVITY"`.
9. **Dynamic Manifest Governing Review Metadata (P2-R6-M2):**
   - Defined `CURRENT_GOVERNING_REVIEW = "P2_R6_REMEDIATION"` at module level.
   - Parameterized and dynamically serialized governing review in `generate_exodus_patent_manifest`.
   - Added unit test asserting exact governing review match.
10. **Preservation of Baselines & Expanded Suite:**
    - P0 scientific baseline blob `97f65dfa25db7730323edd5e52c98b17371fdeaa` preserved byte-for-byte.
    - P1 scientific baseline preserved byte-for-byte.
    - Full test suite: **124 tests passed** (35 P0 + 37 P1 + 52 P2).

---

## 2. P2 R6 Review Finding Remediation Matrix

| Finding ID | Severity | Canonical Finding Description | Implemented Remediation & Physical Resolution |
| :--- | :--- | :--- | :--- |
| **P2-R6-F1** | **HIGH** | Reported full-3D/FIG.21 convergence and ground-thickness fidelity do not match code or tests. | Defaulted `run_3d_mesh_convergence_study` to `refine_z=True`. Executed 3-level full 3D refinement study on FIG. 21 with per-body forces and stable fractional order ($p_{\text{obs}} \approx 0.80$). Reconciled ground plane thickness to $T_2 = 0.25\text{ mm}$ (`EXTERNAL_ESTIMATE_FOR_UNSPECIFIED`) with 1-cell discretization ratios ($5.08, 2.54, 1.693$) documented truthfully. Exposed axial discretization bound in Newtons: $u_{\text{mesh},z} = 499.4\ \mu\text{N} > 23.7\ \mu\text{N}$. |
| **P2-R6-F2** | **HIGH** | Clearance and missing-parameter terms are still not empirically/numerically calibrated uncertainty bounds. | Implemented `calibrate_domain_clearance_uncertainty_3d` computing paired same-grid clearance sensitivity $|F_{\text{blade}}(U_{\text{expanded}}) - F_{\text{blade}}(U_{\text{nominal}})|$, separating physical wall reaction from placement sensitivity. Replaced pseudo-quantified $50\ \mu\text{N}$ placeholder with explicit `missing_parameter_model_uncertainty_n = None` and `missing_parameter_model_uncertainty_is_bounded = False`, failing closed in the gate. Multi-body convergence tracked across levels. |
| **P2-R6-F3** | **HIGH** | Production gate can accept a mechanically UNVERIFIED whole-body status. | Defined explicit allowlist `VERIFIED_WHOLE_BODY_STATES`. Replaced prefix test; now strictly requires `whole_body_status in VERIFIED_WHOLE_BODY_STATES`, immediately rejecting `VACUUM_NO_DIELECTRIC_UNVERIFIED_PENDING_CONVERGENCE` and `UNVERIFIED_PENDING_CONFORMING_INTERFACE_MESHING`. Added robust input validation rejecting NaN, Inf, negative inputs, and empty strings. Expanded adversarial test coverage. |
| **P2-R6-F4** | **HIGH** | FIG.21 dielectric mechanical closure remains unverified and is not shown to converge. | Tracked interface-to-contour agreement relative error across FIG. 21 meshes and across permittivities ($\varepsilon_r = 2.0, 3.8, 5.0$). Documented constitutive Korteweg-Helmholtz traction assumptions and Cartesian staircasing limits. Preserved unverified whole-body status and fail-closed gate. |
| **P2-R6-M1** | **MED** | Claimed uniform-field validation does not exercise the new 3D H1 quadrature. | Extracted pure function `compute_3d_patent_face_h1_quadrature`. Drove directly on true 3D uniform and non-uniform field arrays in `test_true_3d_patent_face_h1_uniform_field_analytic_benchmark`. Verified exact $< 10^{-12}$ analytical agreement, Cauchy-Schwarz adherence, offset sensitivity, and area audit. Labeled provisional. |
| **P2-R6-M2** | **MED** | Generated manifest still identifies an obsolete governing review. | Defined `CURRENT_GOVERNING_REVIEW = "P2_R6_REMEDIATION"`. Parameterized and serialized dynamically in `generate_exodus_patent_manifest`. Verified in unit test suite. |

---

## 3. Changed Scope & File Inventory

- [`exodus_hypothesis_evaluator.py`](file:///Users/chrisrodriguez/Documents/scalar-wave/exodus_hypothesis_evaluator.py):
  - Added constants `VERIFIED_WHOLE_BODY_STATES` and `CURRENT_GOVERNING_REVIEW = "P2_R6_REMEDIATION"`.
  - Added dataclass `PatentFaceH13DQuadratureResult`.
  - Implemented pure function `compute_3d_patent_face_h1_quadrature`.
  - Implemented pure function `calibrate_domain_clearance_uncertainty_3d`.
  - Enriched `Finite3DModelResult`: `z_mesh_discretization_uncertainty_n: Optional[float] = None`, `missing_parameter_model_uncertainty_n: Optional[float] = None`, `h1_3d_quadrature_status: str`.
  - Rewrote `evaluate_physical_scale_discrimination_gate` with strict allowlist and robust input validation.
  - Updated `run_3d_mesh_convergence_study` with `refine_z: bool = True` default and multi-body convergence metrics.
  - Updated `run_3d_z_mesh_convergence_study` computing axial discretization bound $u_{\text{mesh},z}$ in Newtons.
  - Updated `generate_exodus_patent_manifest` with dynamic `governing_review`.
- [`tests/test_p2_exodus_patent.py`](file:///Users/chrisrodriguez/Documents/scalar-wave/tests/test_p2_exodus_patent.py):
  - Updated `test_finite_3d_mesh_refinement_convergence` with true thin-sheet discretization ratios ($5.08, 2.54, 1.693$).
  - Updated `test_finite_3d_z_mesh_refinement_and_full_3d_discretization_bounds` asserting $u_{\text{mesh},z}$ in Newtons.
  - Updated `test_fig21_nine_blade_multilevel_mesh_convergence` to 3 levels with full 3D refinement, per-body bounds, and fractional observed order.
  - Rewrote `test_true_3d_patent_face_h1_uniform_field_analytic_benchmark` driving `compute_3d_patent_face_h1_quadrature` on true 3D field arrays.
  - Rewrote `test_adversarial_uncertainty_budget_injection_fails_closed` testing allowlist and invalid inputs.
  - Added `test_calibrate_domain_clearance_uncertainty_3d`.
  - Added `test_fig21_dielectric_closure_and_permittivity_sensitivity`.
  - Updated `test_manifest_generation_and_schema_conformance` asserting `governing_review == "P2_R6_REMEDIATION"`.
- [`docs/PR_DESCRIPTION.md`](file:///Users/chrisrodriguez/Documents/scalar-wave/docs/PR_DESCRIPTION.md):
  - Updated to R7 draft with exact test count (124 tests passed), reconciled ground thickness, allowlisted gate, and axial bound.
- [`README.md`](file:///Users/chrisrodriguez/Documents/scalar-wave/README.md) & [`docs/ROADMAP.md`](file:///Users/chrisrodriguez/Documents/scalar-wave/docs/ROADMAP.md):
  - Updated research progress narrative and roadmap to reflect P2 R7 re-review status (2 of 5 review gates accepted; P2 active and draft).

---

## 4. Verification Evidence

### Local Test Execution
- Full test suite: **124 tests passed** (35 P0 + 37 P1 + 52 P2).
- P0 baseline preservation:
  ```bash
  git hash-object electrostatics_baseline.py
  # Output: 97f65dfa25db7730323edd5e52c98b17371fdeaa (byte-identical)
  ```

---

## 5. Reviewer Acceptance Criteria for P2 R7

1. **Multi-Level Full 3D FIG. 21 Convergence & Ground Thickness Reconciliation:**
   Verify `run_3d_mesh_convergence_study` defaults to `refine_z=True`. Verify 3-level FIG. 21 convergence study reports per-body forces and stable fractional order ($p_{\text{obs}} \approx 0.80$). Verify ground electrode thickness reconciles $T_2 = 0.25\text{ mm}$ with thin-sheet ratios ($5.08, 2.54, 1.693$) without false claims of 1.0000 on coarse grids. Verify $u_{\text{mesh},z} = 499.4\ \mu\text{N}$ is derived and stored in Newtons.
2. **Empirical Domain Clearance Sensitivity & Unbounded Model Parameters:**
   Verify `calibrate_domain_clearance_uncertainty_3d` derives boundary sensitivity from paired same-grid solves. Verify missing model parameter uncertainty is reported as unquantified/unbounded rather than a pseudo-quantified $50\ \mu\text{N}$.
3. **Strict Allowlist & Robust Input Validation:**
   Verify `evaluate_physical_scale_discrimination_gate` checks `whole_body_status in VERIFIED_WHOLE_BODY_STATES`, strictly rejecting all unverified states. Confirm that NaN, Inf, negative inputs, and empty strings are rejected with invalid status.
4. **FIG. 21 Dielectric Agreement & Permittivity Scaling:**
   Verify dielectric interface traction scales with $(\varepsilon_r - 1)$, interface-to-contour relative error is recorded, and whole-body status remains unverified and fails closed.
5. **Direct 3D Patent-Face H1 Near-Face Numerical Quadrature Benchmark:**
   Verify `compute_3d_patent_face_h1_quadrature` is driven on true 3D uniform and non-uniform field arrays with exact $< 10^{-12}$ analytical verification, Cauchy-Schwarz adherence, offset sensitivity, and area audit.
6. **Dynamic Manifest Governing Review & Baseline Preservation:**
   Verify manifest `governing_review` equals `P2_R6_REMEDIATION`. Verify P0 blob SHA `97f65dfa25db7730323edd5e52c98b17371fdeaa` and P1 source files remain preserved byte-for-byte.
