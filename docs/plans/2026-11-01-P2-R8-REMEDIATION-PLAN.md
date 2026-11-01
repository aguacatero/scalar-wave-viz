# Phase P2 R8 Remediation Plan — Exodus Patent US11511891B2 Reproduction

**Document:** `docs/plans/2026-11-01-P2-R8-REMEDIATION-PLAN.md`  
**Governing Review:** Independent scientific review P2 R7 ([issuecomment-6559262041](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6559262041))  
**Target Milestone:** Phase P2 R8 Independent Scientific Re-Review  
**Operating Mode:** MANUAL-ONLY (Merge authorization NOT GRANTED; draft status preserved; no P3 kickoff)  
**Previous Baseline:** PR #11 HEAD `404e29ef914c0e141deb055ed82f6bf33d1af544` (CI Run 41275682251 passed)

---

## 1. Review Findings & Remediation Strategy

| Finding ID | Severity | Core Issue | Implemented R8 Remediation |
| :--- | :--- | :--- | :--- |
| **P2-R7-F1** | **HIGH** | FIG. 21 convergence uses 25.4 mm surrogate without transfer validation to declared 101.6 mm article; no per-body bounds; ground sheet thins with grid. | 1. Formally define model variants: `FIG21_MODEL_VARIANT_DECLARED_ARTICLE_101MM` and `FIG21_MODEL_VARIANT_SHORTENED_AXIAL_SURROGATE_25MM`.<br>2. Implement transfer benchmark `compare_fig21_surrogate_to_declared_article` validating linear $L_z$ scaling and isolating end-cap force excess.<br>3. Publish level-by-level numerical values with predeclared per-body tolerances across 3 levels.<br>4. Truthfully label coarse-grid convergence as `NON_ASYMPTOTIC_COARSE_GRID_GEOMETRIC_THINNING_AND_CORNER_SINGULARITY`. |
| **P2-R7-F2** | **HIGH** | Domain calibration helper disconnected from solver and production gate; wall reaction still passed as domain uncertainty; $z$ clearance omitted. | 1. Expand `calibrate_domain_clearance_uncertainty_3d` to full 3D clearance expansion ($x, y, z$).<br>2. Integrate domain clearance sensitivity into `solve_exodus_electrostatics_3d` with separate fields: `direct_wall_reaction_x_n` (physical force) vs `domain_boundary_placement_sensitivity_n` (numerical sensitivity).<br>3. Propagate measured sensitivity to gate and manifest.<br>4. Test that changing sensitivity directly impacts gate input/outcome. |
| **P2-R7-F3** | **HIGH** | FIG. 21 dielectric agreement lacks quantitative tests: no $(\varepsilon_r-1)$ scaling verification, single grid, unverified status. | 1. Implement multi-permittivity sweep ($\varepsilon_r \in [1.5, 2.5, 3.8, 5.0]$) verifying $F_{\text{int}} \propto (\varepsilon_r - 1)$ ($R^2 > 0.99$).<br>2. Multi-resolution interface-to-contour agreement study at nominal $\varepsilon_r = 3.8$ showing stable bounded Cartesian discrepancy ($15-35\%$).<br>3. Document Korteweg-Helmholtz material-side limiting field conventions.<br>4. Preserve unverified whole-body status and fail-closed gate. |
| **P2-R7-F4** | **HIGH** | Mesh uncertainty derived only from blade force; $u_{\text{mesh},z}$ is an assumed-order estimate omitted from production gate. | 1. Disclose $u_{\text{mesh},z}$ as an assumed $p=1$ finite-difference sensitivity estimate: `axial_grid_sensitivity_estimate_n`.<br>2. Combine lateral and axial mesh uncertainties into total mesh discretization uncertainty: $u_{\text{mesh,total}} = \sqrt{u_{\text{mesh},xy}^2 + u_{\text{mesh},z}^2}$ and pass to gate.<br>3. Track multi-body convergence metrics across all components.<br>4. Re-assert fail-closed status `NOT_RESOLVED_AT_CURRENT_3D_GRID_RESOLUTION`. |
| **P2-R7-M1** | **MED** | 3D H1 quadrature offset sensitivity tested on x-invariant field; indices clamped; precision claim overstated. | 1. Test offset sensitivity on non-uniform field with $\partial E / \partial x \ne 0$, proving $F(\text{offset}=1) \ne F(\text{offset}=2)$ and quantifying $\Delta F / \Delta x$.<br>2. Raise `ValueError` on out-of-bounds sample offset.<br>3. Refine precision claim to $< 10^{-9}$ (tested 9 decimal places).<br>4. Retain provisional designation. |
| **P2-R7-M2** | **LOW** | Manifest `governing_review` is manually updated constant. | 1. Implement `discover_governing_review_round()` dynamically inspecting `docs/reviews/`.<br>2. Update default to `"P2_R7_REMEDIATION"`.<br>3. Add unit test asserting metadata-manifest consistency. |

---

## 2. File Modification Inventory

- **`exodus_hypothesis_evaluator.py`**:
  - Add model variant constants: `FIG21_MODEL_VARIANT_DECLARED_ARTICLE_101MM`, `FIG21_MODEL_VARIANT_SHORTENED_AXIAL_SURROGATE_25MM`.
  - Update `CURRENT_GOVERNING_REVIEW = "P2_R7_REMEDIATION"` and add `discover_governing_review_round()`.
  - Update `compute_3d_patent_face_h1_quadrature` with strict index bounds validation raising `ValueError`.
  - Update `calibrate_domain_clearance_uncertainty_3d` with full 3D ($x, y, z$) clearance expansion.
  - Update `Finite3DModelResult`:
    - Add `domain_boundary_placement_sensitivity_n: float`
    - Add `direct_wall_reaction_x_n: float`
    - Add `axial_grid_sensitivity_estimate_n: Optional[float] = None`
    - Add `fig21_model_variant: Optional[str] = None`
  - Update `solve_exodus_electrostatics_3d`:
    - Support `calibrate_domain_sensitivity: bool = False` (or compute paired sensitivity).
    - Combine lateral and axial mesh uncertainties: $u_{\text{mesh,total}} = \sqrt{u_{\text{mesh},xy}^2 + u_{\text{mesh},z}^2}$.
    - Pass separated `domain_boundary_placement_sensitivity_n` into gate.
  - Add `compare_fig21_surrogate_to_declared_article` evaluating transfer scaling.
  - Update `generate_exodus_patent_manifest` with dynamic review discovery and separated wall reaction vs placement sensitivity.

- **`tests/test_p2_exodus_patent.py`**:
  - Update `test_fig21_nine_blade_multilevel_mesh_convergence`: label as shortened surrogate, add per-body convergence metrics and predeclared bounds.
  - Add `test_fig21_surrogate_to_declared_article_transfer_scaling`.
  - Update `test_calibrate_domain_clearance_uncertainty_3d` asserting full 3D ($x, y, z$) expansion and gate sensitivity impact.
  - Update `test_fig21_dielectric_closure_and_permittivity_sensitivity` verifying $(\varepsilon_r-1)$ scaling across 4 permittivities and multi-resolution interface-to-contour agreement.
  - Update `test_finite_3d_z_mesh_refinement_and_full_3d_discretization_bounds` asserting combined multi-axis mesh uncertainty in gate.
  - Update `test_true_3d_patent_face_h1_uniform_field_analytic_benchmark` testing non-uniform field offset sensitivity and bounds rejection.
  - Add `test_governing_review_metadata_consistency`.

- **Documentation & Manifests**:
  - `docs/PR_DESCRIPTION.md`: update to R8 draft.
  - `README.md` & `docs/ROADMAP.md`: update to R8 re-review.
  - `docs/handoffs/2026-11-01-P2-CHATGPT-R8-READY.md`: persistent handoff document.
