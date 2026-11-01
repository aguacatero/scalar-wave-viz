# Phase P2 R9 Remediation Plan — Addressing ChatGPT R8 Scientific Review

**Date:** 2026-11-01  
**Target Pull Request:** [PR #11](https://github.com/aguacatero/scalar-wave-viz/pull/11) on branch `p2-patent-geometry-exodus-2026-10-25`  
**Governing Review:** Independent Scientific Review P2 R8 ([issuecomment-6564571034](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6564571034))  
**Operating Mode:** MANUAL-ONLY (PR remains DRAFT; merge authorization NOT GRANTED)

---

## 1. Executive Remediation Strategy

The ChatGPT R8 independent review issued **CHANGES REQUIRED — P2 R8 SCIENTIFIC BASELINE NOT ACCEPTED** with 5 High findings (`P2-R8-F1` through `P2-R8-F5`), 1 Medium finding (`P2-R8-M1`), and 1 Low finding (`P2-R8-M2`).

Our strategy systematically resolves every item:

1. **P2-R8-F1 (Surrogate Transfer & Multi-Length Sweep):**
   - Expand `compare_fig21_surrogate_to_declared_article` to sweep $\ge 3$ axial lengths: $L_z \in [0.0254, 0.0508, 0.1016\text{ m}]$ (1, 2, 4 inches).
   - Fit linear regression $F(L_z) = L_z \cdot f_{\text{interior}} + F_{\text{end}}$ across all 3 lengths, proving $R^2 > 0.99$ linearity without two-point overfitting.
   - Track per-body forces (blade, ground, dielectric, wall, net) and H1 proximal/distal face integrals across all 3 lengths.
   - In `test_fig21_nine_blade_multilevel_mesh_convergence`, track inter-level per-body differences $\Delta F_k = |F_{k+1} - F_k|$ and assert that $\Delta F_k > 23.7\ \mu\text{N}$, proving why coarse grids cannot resolve the physical scale and must fail closed.
   - Explicitly document that end-cap relief is an empirical single-grid observation, not a verified transfer law.

2. **P2-R8-F2 (Domain Clearance Calibration & Nomenclature):**
   - In `calibrate_domain_clearance_uncertainty_3d`, support sweeping $\ge 3$ clearances ($1.0\times, 1.5\times, 2.0\times$) and verify monotonic coupling decay.
   - Track per-body sensitivities (`delta_blade_n`, `delta_ground_n`, `delta_dielectric_n`, `delta_wall_n`, `delta_net_n`).
   - Standardize nomenclature: label as `domain_boundary_placement_sensitivity_n` (finite-difference sensitivity estimate), explicitly disclaiming that a two-box difference is a proven upper bound to unbounded space.

3. **P2-R8-F3 (Dielectric Permittivity Linearity, Closure Table & Fail-Closed Gate):**
   - In permittivity sweep, fit $F_{\text{int}}(\varepsilon_r) = c \cdot (\varepsilon_r - 1) + b$; assert $R^2 > 0.98$ and relative intercept $|b| / \max(|F|) < 0.05$ (near-zero intercept at vacuum $\varepsilon_r = 1$).
   - Record component-by-component closure table across mesh levels for FIG. 21, demonstrating millinewton-scale residual ($> 23.7\ \mu\text{N}$) from Cartesian staircasing.
   - Keep `finite_3d_dielectric_virtual_work_x_n = None`, keep `whole_body_3d_mechanical_accounting = "UNVERIFIED_PENDING_CONFORMING_INTERFACE_MESHING"`, and fail closed.

4. **P2-R8-F4 (Whole-Body Discretization Error & Contingent Axial Gate):**
   - In `evaluate_physical_scale_discrimination_gate`:
     - If `z_mesh_discretization_uncertainty_n is None`: do NOT set to 0.0. If `whole_body_status in VERIFIED_WHOLE_BODY_STATES`, reject and return `False, "NOT_RESOLVED_MISSING_AXIAL_GRID_DISCRETIZATION_EVIDENCE"`.
     - Report `axial_grid_sensitivity_estimate_n = None` when missing, never pseudo-zero.
     - If any required uncertainty term is missing/unbounded, return `rss_uncert_n = None, linear_uncert_n = None` (never `NaN`).
   - In `run_3d_mesh_convergence_study`:
     - Compute discretization error for all bodies (blade, ground, dielectric, wall, net), setting `mesh_force_discretization_uncertainty_n = max(body_errors)`.
     - When `refine_z=True`, simultaneous 3D refinement already includes axial error; clarify dependence.

5. **P2-R8-F5 (Exported Manifest Invariants & Non-Standard NaN Rejection):**
   - In `Finite3DModelResult`: `domain_boundary_clearance_uncertainty_n: Optional[float] = None`, `combined_uncertainty_rss_n: Optional[float] = None`.
   - Preserve `None/null` when uncalibrated (never substitute 0.0).
   - In all JSON dumps (`generate_exodus_patent_manifest`, `examples/exodus_patent_demo.py`): pass `allow_nan=False`, strictly forbidding `NaN` or `Infinity`.
   - In CI manifest provenance gate and unit tests: assert `json.loads` succeeds, assert all numeric fields are finite or null, assert `domain_boundary_clearance_uncertainty_n` is not 0.0 when placement sensitivity is null.

6. **P2-R8-M1 (H1 Input Validation):**
   - Validate `blade_tip_spans` is non-empty; validate $y_{\text{min}} < y_{\text{max}}$, $z_{\text{min}} < z_{\text{max}}$, and $dx, dy, dz > 0$, raising `ValueError`.

7. **P2-R8-M2 (Numeric-Round Review Discovery):**
   - Update `discover_governing_review_round()` with regex `*-P2-CHATGPT-R(\d+)-REVIEW.md` and integer sorting `max(..., key=lambda r: int(r[0]))`.
   - Set `CURRENT_GOVERNING_REVIEW = "P2_R8_REMEDIATION"`.
   - Add fail-closed assertion comparing discovery against constant.

---

## 2. Implementation Steps

1. Update `exodus_hypothesis_evaluator.py`:
   - Set `CURRENT_GOVERNING_REVIEW = "P2_R8_REMEDIATION"`.
   - Implement numeric-round sorting in `discover_governing_review_round()`.
   - Add strict span and grid validation to `compute_3d_patent_face_h1_quadrature()`.
   - Refactor `evaluate_physical_scale_discrimination_gate()` to require qualified axial evidence, eliminate `NaN` generation, and return `None` for missing uncertainty totals.
   - Update `Finite3DModelResult` dataclass typing (`Optional[float] = None`).
   - Update `solve_exodus_electrostatics_3d()` to pass `None` without NaN fallback.
   - Expand `compare_fig21_surrogate_to_declared_article()` to 3 lengths and fit linear model.
   - Update `run_3d_mesh_convergence_study()` to compute multi-body discretization error across all bodies.
   - Update `generate_exodus_patent_manifest()` and demo scripts to use `allow_nan=False`.
2. Update `tests/test_p2_exodus_patent.py`:
   - Test empty and invalid spans in `compute_3d_patent_face_h1_quadrature()` raising `ValueError`.
   - Test adversarial omission of axial discretization evidence failing closed.
   - Test 3-length transfer scaling regression ($R^2 > 0.99$) and multi-body tracking.
   - Test multi-clearance sweep monotonic decay in `test_calibrate_domain_clearance_uncertainty_3d`.
   - Test strict JSON parse, schema conformance, and finite numeric invariants.
   - Test governing review discovery matching `P2_R8_REMEDIATION`.
3. Update `.github/workflows/physics-baseline.yml` manifest gate to enforce `allow_nan=False` and strict finiteness assertions.
4. Run full unit test suite (126+ tests).
5. Verify P0 baseline hash `97f65dfa25db7730323edd5e52c98b17371fdeaa`.
6. Regenerate artifacts (`exodus_patent_manifest.json`, `exodus_patent_comparison.png`).
7. Update documentation: `docs/PR_DESCRIPTION.md`, `README.md`, `docs/ROADMAP.md`, and author `docs/handoffs/2026-11-01-P2-CHATGPT-R9-READY.md`.
8. Commit, push, monitor CI, and post timestamped R9 handoff comment.
