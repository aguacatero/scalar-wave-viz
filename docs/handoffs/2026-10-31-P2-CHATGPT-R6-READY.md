# SCALAR WAVE VIZ — P2 R6 INDEPENDENT SCIENTIFIC RE-REVIEW HANDOFF

**Repository:** https://github.com/aguacatero/scalar-wave-viz  
**Pull Request:** https://github.com/aguacatero/scalar-wave-viz/pull/11  
**Issue:** https://github.com/aguacatero/scalar-wave-viz/issues/7  
**Branch:** `p2-patent-geometry-exodus-2026-10-25`  
**Milestone:** Phase P2 — Exodus patent US11511891B2 FIGS. 4–8 reproduction & hypothesis separation  
**Review Round:** P2 R6  
**Governing Review:** Independent scientific review P2 R5 ([issuecomment-6548482245](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6548482245))  
**Operating Mode:** MANUAL-ONLY  
**Merge Authorization:** NOT GRANTED (PR remains DRAFT pending independent review; no P3 kickoff)  

---

## 1. Executive Summary

This handoff remediates all findings from ChatGPT's independent scientific review of Phase P2 R5 ([issuecomment-6548482245](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6548482245)), which concluded `CHANGES REQUIRED — P2 R5 SCIENTIFIC BASELINE NOT ACCEPTED` across 4 High and 1 Medium findings (`P2-R5-F1`, `P2-R5-F2`, `P2-R5-F3`, `P2-R5-F4`, and `P2-R5-M1`).

Phase P2 reproduces the Exodus Propulsion Technologies patent [US11511891B2](https://patents.google.com/patent/US11511891B2/en) (issued November 29, 2022) embodiment depicted in FIGS. 4–8 (single-stage schematic) and separates it from the FIG. 21 nine-blade epoxy-potted test article.

Key physical and numerical advancements in R6:
1. **Full 3D Commensurate Refinement ($dx, dy, dz$) & Multi-Level FIG. 21 Convergence (P2-R5-F1):**
   - Enabled simultaneous proportional refinement of lateral ($dx, dy$) and axial ($dz$) grid spacings ($h_k = 1.27\text{ mm} / k$, $dz_k = 2.54\text{ mm} / k$).
   - Ground electrode thickness ($T_{\text{gnd}} = 1.27\text{ mm}$) is tracked explicitly: target thickness, actual discretized thickness ($k$ cells), and discretization ratio remain exactly $1.0000$ across all refinement levels.
   - Implemented dedicated longitudinal $z$-grid refinement sensitivity study `run_3d_z_mesh_convergence_study` establishing an isolated axial discretization uncertainty bound $u_{\text{mesh},z} = 0.05\ \mu\text{N}$.
   - Implemented multi-level FIG. 21 nine-blade potted article convergence study with commensurate lateral and axial grids, tracking force evolution on blades, ground, potting dielectric, enclosure walls, and H1 surface quantities across refinement levels.
2. **Centralized Production Discrimination Gate & Dynamic Post-Refinement Re-evaluation (P2-R5-F2):**
   - Defined centralized pure production function `evaluate_physical_scale_discrimination_gate` in `exodus_hypothesis_evaluator.py`.
   - Gate rigorously checks all 5 budget components ($u_{\text{solver}}$, $u_{\text{closure}}$, $u_{\text{mesh}}$, $u_{\text{domain}}$, $u_{\text{model}}$), the combined RSS bound ($U_{\text{rss}} < 23.7\ \mu\text{N}$), relative residual $< 0.5\%$, bounded model parameter flag, and verified whole-body mechanical accounting.
   - Calibrated domain boundary clearance uncertainty directly from outer wall coupling force.
   - Added explicit `missing_parameter_model_uncertainty_is_bounded` flag to fail closed if model uncertainty is untracked or unbounded.
   - Re-evaluates production gate post-refinement in `run_3d_mesh_convergence_study` to dynamically update `physical_scale_discrimination_status` and `finite_3d_is_conserved`.
   - Adversarial injection tests directly call `evaluate_physical_scale_discrimination_gate`, verifying fail-closed behavior on excessive errors even when closure is small.
3. **Provisional 3D Dielectric Designation & Optional Virtual Work Semantics (P2-R5-F3):**
   - Benchmark status designated `PROVISIONAL_3D_DIELECTRIC_BENCHMARK_APPROXIMATE_AGREEMENT`, honestly acknowledging the approximate ($4.5\%$) agreement between 3D virtual work and Maxwell stress contour on Cartesian grids without premature full acceptance.
   - Virtual work field in `Finite3DModelResult` (`finite_3d_dielectric_virtual_work_x_n`) adopts strict `Optional[float] = None` semantics when uncomputed, rather than misleading 0.0.
   - Records relative interface-to-contour agreement metric (`finite_3d_dielectric_interface_to_contour_agreement_rel`).
4. **True 3D Patent-Face H1 Quadrature with Literal Eq. (11), Corrected Maxwell Traction, and Spatial-Mean Plug-in (P2-R5-F4):**
   - Samples true 3D field on proximal tip face 100a and distal base face 101a at material interfaces.
   - Evaluates literal Patent Eq. (11) without the $1/2$ factor: $F = \varepsilon_0 (\iint_{101a} E^2 dA - \iint_{100a} E^2 dA)$. Because the distal base area ($30.97\text{ cm}^2$) is $24\times$ larger than the proximal tip area ($1.29\text{ cm}^2$), literal Eq. (11) yields $+0.0650\text{ N}$ (rearward force away from ground, directly contradicting the patent's claim of forward net thrust!). On FIG. 21, 9 tips provide sufficient area to reverse literal force to $-0.0833\text{ N}$.
   - Evaluates corrected 0.5x Maxwell traction force ($+0.0325\text{ N}$ single blade, $-0.0416\text{ N}$ 9-blade).
   - Evaluates spatial-mean plug-in approximation ($+0.0617\text{ N}$ single blade, $-0.0768\text{ N}$ 9-blade).
   - Confirms Cauchy-Schwarz inequality holds across all faces ($\iint E^2 dA \ge \langle E \rangle^2 A$).
   - Validated against uniform-field analytic benchmark.
5. **Shared Dynamic Bar Chart Label Formatter (P2-R5-M1):**
   - Extracted `format_demo_bar_chart_labels` in `examples/exodus_patent_demo.py` to eliminate duplication and keep visualization code fully tested.
   - Tested dynamically across model configurations in `test_demo_plot_dynamic_parameter_label_updating`.
6. **Preservation of Accepted Baselines:**
   - P0 scientific baseline blob `97f65dfa25db7730323edd5e52c98b17371fdeaa` preserved byte-for-byte.
   - P1 scientific baseline preserved byte-for-byte.
   - Full test suite: **122 tests passed** (35 P0 + 37 P1 + 50 P2).

---

## 2. P2 R5 Review Finding Remediation Matrix

| Finding ID | Severity | Canonical Finding Description | Implemented Remediation & Physical Resolution |
| :--- | :--- | :--- | :--- |
| **P2-R5-F1** | **HIGH** | Commensurate 3D mesh refinement only refines in 2D ($dx, dy$); $dz$ is held constant. Multi-level FIG. 21 convergence missing. | Refactored `run_3d_mesh_convergence_study` to support full 3D refinement (`refine_z=True`), scaling $dz_k = 2.54\text{ mm} / k$ alongside lateral spacings. Tracked target ($1.27\text{ mm}$) and actual ground electrode thickness across all levels (ratio exactly 1.0000). Implemented dedicated longitudinal $z$-grid refinement study `run_3d_z_mesh_convergence_study` yielding axial bound $u_{\text{mesh},z} = 0.05\ \mu\text{N}$. Implemented multi-level FIG. 21 nine-blade potted article convergence study with commensurate lateral and axial grids. |
| **P2-R5-F2** | **HIGH** | Uncertainty discrimination gate not exposed as centralized pure function; post-refinement status stale; clearance uncertainty uncalibrated; model parameters unverified. | Extracted pure production function `evaluate_physical_scale_discrimination_gate` enforcing all 5 terms, RSS bound, relative residual $< 0.5\%$, bounded model parameter flag, and verified whole-body state against $23.7\ \mu\text{N}$. Re-evaluates gate post-refinement in `run_3d_mesh_convergence_study`. Calibrated domain clearance directly from outer wall coupling force. Added `missing_parameter_model_uncertainty_is_bounded` flag to fail closed if unbounded. Adversarial tests directly call production gate. |
| **P2-R5-F3** | **HIGH** | 3D dielectric benchmark claims full benchmark validation on approximate agreement; uncomputed virtual work marked 0.0. | Renamed benchmark status to `PROVISIONAL_3D_DIELECTRIC_BENCHMARK_APPROXIMATE_AGREEMENT`. Adopted strict `Optional[float] = None` semantics for uncomputed `finite_3d_dielectric_virtual_work_x_n`. Tracked relative interface-to-contour agreement metric (`finite_3d_dielectric_interface_to_contour_agreement_rel`). Retained fail-closed whole-body accounting state. |
| **P2-R5-F4** | **HIGH** | 3D H1 surface prediction relies on 2D extrusion / global enclosing surface; lacks true 3D patent-face quadrature for literal Eq. (11). | Implemented true 3D patent-face quadrature on proximal tip face 100a and distal base face 101a at material interfaces. Evaluates literal Patent Eq. (11) without 1/2 factor ($+0.0650\text{ N}$ single blade, $-0.0833\text{ N}$ 9-blade), corrected 0.5x Maxwell traction, and spatial-mean plug-in. Proved Cauchy-Schwarz inequality holds. Validated against uniform-field analytic benchmark. |
| **P2-R5-M1** | **MED** | Demo plot bar chart label formatter not shared or tested against custom model instances. | Extracted `format_demo_bar_chart_labels` as shared module-level function in `examples/exodus_patent_demo.py`. Tested dynamically across model instances in `test_demo_plot_dynamic_parameter_label_updating`. |

---

## 3. Changed Scope & File Inventory

- [`exodus_hypothesis_evaluator.py`](file:///Users/chrisrodriguez/Documents/scalar-wave/exodus_hypothesis_evaluator.py):
  - Added ground electrode thickness tracking fields to `Finite3DModelResult`: `target_ground_thickness_m`, `actual_ground_thickness_m`, `ground_thickness_discretization_ratio`.
  - Added true 3D H1 patent-face quantities: `h1_3d_proximal_area_m2`, `h1_3d_distal_area_m2`, `h1_3d_e2_integral_proximal_tip_v2_m`, `h1_3d_e2_integral_distal_base_v2_m`, `h1_3d_spatial_mean_e_proximal_v_per_m`, `h1_3d_spatial_mean_e_distal_v_per_m`, `h1_3d_literal_patent_eq11_force_n`, `h1_3d_half_factor_corrected_force_n`, `h1_3d_spatial_mean_plugin_force_n`.
  - Changed `finite_3d_dielectric_virtual_work_x_n` type to `Optional[float] = None`.
  - Added `finite_3d_dielectric_interface_to_contour_agreement_rel: Optional[float] = None`.
  - Added `missing_parameter_model_uncertainty_is_bounded: bool = False`.
  - Defined centralized production function `evaluate_physical_scale_discrimination_gate(...)`.
  - Designated 3D dielectric benchmark `PROVISIONAL_3D_DIELECTRIC_BENCHMARK_APPROXIMATE_AGREEMENT`.
  - Updated `solve_exodus_electrostatics_3d()` with material-side sampling for tip 100a and base 101a, literal Eq. (11) computation, corrected Maxwell traction, and centralized production gate evaluation.
  - Updated `run_3d_mesh_convergence_study()`: added `refine_z: bool = True`, multi-blade support, and dynamic post-refinement re-evaluation of production gate.
  - Implemented `run_3d_z_mesh_convergence_study()` for isolated axial sensitivity.
  - Updated `generate_exodus_patent_manifest()` with ground thickness, dielectric agreement, and true 3D H1 face quantities.
- [`examples/exodus_patent_demo.py`](file:///Users/chrisrodriguez/Documents/scalar-wave/examples/exodus_patent_demo.py):
  - Extracted `format_demo_bar_chart_labels(result: ExodusEvaluationResult) -> list[str]`.
  - Replaced inline label list in Panel B with `format_demo_bar_chart_labels(result)`.
- [`tests/test_p2_exodus_patent.py`](file:///Users/chrisrodriguez/Documents/scalar-wave/tests/test_p2_exodus_patent.py):
  - Added `test_finite_3d_z_mesh_refinement_and_full_3d_discretization_bounds`.
  - Added `test_fig21_nine_blade_multilevel_mesh_convergence`.
  - Added `test_true_3d_patent_face_h1_quadrature_and_cauchy_schwarz`.
  - Added `test_true_3d_patent_face_h1_uniform_field_analytic_benchmark`.
  - Updated `test_adversarial_uncertainty_budget_injection_fails_closed` to directly call production gate.
  - Updated `test_3d_independent_dielectric_reaction_and_virtual_work_benchmark` to expect provisional status.
  - Updated `test_demo_plot_dynamic_parameter_label_updating` to test `format_demo_bar_chart_labels`.
  - Updated `test_adversarial_rejection_of_stale_pr_or_literature_metadata` to verify 122 tests.
- [`docs/PR_DESCRIPTION.md`](file:///Users/chrisrodriguez/Documents/scalar-wave/docs/PR_DESCRIPTION.md):
  - Updated to R6 draft with exact test count (122 tests passed), full 3D refinement, centralized production gate, and true 3D patent-face H1 quadrature.
- [`README.md`](file:///Users/chrisrodriguez/Documents/scalar-wave/README.md) & [`docs/ROADMAP.md`](file:///Users/chrisrodriguez/Documents/scalar-wave/docs/ROADMAP.md):
  - Updated research progress narrative and roadmap to reflect P2 R6 re-review status (2 of 5 review gates accepted; P2 active and draft).

---

## 4. Verification Evidence

### Local Test Execution
- Full test suite: **122 tests passed** (35 P0 + 37 P1 + 50 P2).
- P0 baseline preservation:
  ```bash
  git hash-object electrostatics_baseline.py
  # Output: 97f65dfa25db7730323edd5e52c98b17371fdeaa (byte-identical)
  ```
- Demo & Manifest generation:
  `python3 examples/exodus_patent_demo.py` generated `exodus_patent_manifest.json` and `exodus_patent_comparison.png` with true 3D H1 quadrature and dynamic parameter labels.

---

## 5. Reviewer Acceptance Criteria for P2 R6

1. **Full 3D Commensurate Refinement ($dx, dy, dz$) & Multi-Level FIG. 21 Convergence:**
   Verify `run_3d_mesh_convergence_study` refines both lateral and axial grids proportionally with exact $1.0000$ geometry discretization ratios (including ground thickness). Verify `run_3d_z_mesh_convergence_study` isolates axial grid sensitivity ($u_{\text{mesh},z} = 0.05\ \mu\text{N}$). Verify multi-level FIG. 21 nine-blade potted article mesh convergence study reports multi-body forces and H1 surface quantities across refinement levels.
2. **Centralized Production Discrimination Gate with Dynamic Re-evaluation:**
   Verify `evaluate_physical_scale_discrimination_gate` is a pure production function enforcing all 5 terms, RSS bound, relative residual $< 0.5\%$, bounded model parameter flag, and verified whole-body state against $23.7\ \mu\text{N}$. Confirm the gate is re-evaluated post-refinement and adversarial injections directly test the production gate.
3. **Provisional 3D Dielectric Designation & Optional Virtual Work:**
   Verify the 3D dielectric benchmark is designated `PROVISIONAL_3D_DIELECTRIC_BENCHMARK_APPROXIMATE_AGREEMENT`. Verify uncomputed virtual work uses `Optional[float] = None` semantics. Confirm relative interface-to-contour agreement metric is tracked.
4. **True 3D Patent-Face H1 Quadrature:**
   Verify true 3D field is sampled on proximal tip 100a and distal base 101a. Verify literal Patent Eq. (11) (no 1/2 factor) is computed, correctly revealing positive rearward force on single blade ($+0.0650\text{ N}$) due to $24\times$ larger distal area, and negative force on FIG. 21 ($-0.0833\text{ N}$). Verify Cauchy-Schwarz inequality holds across all faces and uniform-field analytic benchmark passes.
5. **Shared Dynamic Bar Chart Formatter:**
   Verify `format_demo_bar_chart_labels` is a shared function tested dynamically against custom model instances.
6. **Baseline Preservation:**
   Verify P0 blob SHA `97f65dfa25db7730323edd5e52c98b17371fdeaa` and P1 source files remain preserved byte-for-byte.
