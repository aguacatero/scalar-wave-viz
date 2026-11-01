# SCALAR WAVE VIZ — P2 R9 INDEPENDENT SCIENTIFIC RE-REVIEW HANDOFF

**Repository:** https://github.com/aguacatero/scalar-wave-viz  
**Pull Request:** https://github.com/aguacatero/scalar-wave-viz/pull/11  
**Issue:** https://github.com/aguacatero/scalar-wave-viz/issues/7  
**Branch:** `p2-patent-geometry-exodus-2026-10-25`  
**Milestone:** Phase P2 — Exodus patent US11511891B2 FIGS. 4–8 reproduction & hypothesis separation  
**Review Round:** P2 R9  
**Governing Review:** Independent scientific review P2 R8 ([issuecomment-6564571034](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6564571034))  
**Operating Mode:** MANUAL-ONLY  
**Merge Authorization:** NOT GRANTED (PR remains DRAFT pending independent review; no auto-merge, no P3 kickoff)  

---

## 1. Executive Summary

This handoff remediates all findings from ChatGPT's independent scientific review of Phase P2 R8 ([issuecomment-6564571034](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6564571034)), which concluded `CHANGES REQUIRED — P2 R8 SCIENTIFIC BASELINE NOT ACCEPTED` across 5 High, 1 Medium, and 1 Low findings (`P2-R8-F1`, `P2-R8-F2`, `P2-R8-F3`, `P2-R8-F4`, `P2-R8-F5`, `P2-R8-M1`, and `P2-R8-M2`).

Phase P2 reproduces the Exodus Propulsion Technologies patent [US11511891B2](https://patents.google.com/patent/US11511891B2/en) (issued November 29, 2022) embodiment depicted in FIGS. 4–8 (single-stage schematic) and separates it from the FIG. 21 nine-blade epoxy-potted test article.

Key physical and numerical advancements in R9:
1. **Surrogate vs Declared Article Multi-Length Transfer Regression & Inter-Level Discretization Tracking (P2-R8-F1):**
   - Expanded `compare_fig21_surrogate_to_declared_article` across $\ge 3$ axial lengths ($L_z \in [0.0254, 0.0508, 0.1016\text{ m}]$, 1, 2, 4 inches) on matched commensurate grids ($dx=1.27\text{ mm}, dz=2.54\text{ mm}$).
   - Performed linear regression $F_{\text{blade}}(L_z) = L_z \cdot f_{\text{interior}} + F_{\text{end\_caps}}$, demonstrating $R^2 = 1.000000 > 0.99$ and max fit residual $< 25\ \mu\text{N}$, with core slope $f_{\text{interior}} = -6.957\text{ N/m}$ and constant end-cap relief $+7.22\text{ mN}$ ($1.03\%$ of declared article force) designated as a single-grid empirical fit observation (`SINGLE_GRID_EMPIRICAL_LINEAR_FIT_OBSERVATION`).
   - Tracked per-body forces (blade, ground, dielectric, wall, net) and H1 predictions across all lengths.
   - In `test_fig21_nine_blade_multilevel_mesh_convergence`, tracked inter-level per-body differences $\Delta F_k = |F_{k+1} - F_k|$, asserting $\Delta F_k > 23.7\ \mu\text{N}$ (observed $\Delta F_{\text{blade}} \approx 40\text{ mN} \gg 23.7\ \mu\text{N}$), confirming that coarse grids fail closed against the physical discrimination budget.
2. **Domain Boundary Placement Sensitivity Calibration across $\ge 3$ Multipliers (P2-R8-F2):**
   - Expanded `calibrate_domain_clearance_uncertainty_3d` across 3 clearance multipliers ($1.0\times, 1.5\times, 2.0\times$).
   - Verified monotonic decay of finite-difference boundary coupling across successive expansion steps ($|F(1.5)-F(1.0)| = 7.054\text{ mN} > |F(2.0)-F(1.5)| = 2.326\text{ mN}$).
   - Standardized nomenclature as `domain_boundary_placement_sensitivity_n`, explicitly disclaiming a proven upper bound relative to infinity (`FINITE_DIFFERENCE_PLACEMENT_SENSITIVITY_ESTIMATE_NOT_PROVEN_INFINITE_BOUND`).
3. **Potting Dielectric Non-Zero Intercept & Multi-Level Closure Ledger (P2-R8-F3):**
   - Evaluated permittivity sweep across $\varepsilon_r \in [1.5, 2.5, 3.8, 5.0]$ on FIG. 21, verifying monotonic susceptibility scaling ($R^2 = 0.9846 > 0.98$).
   - Documented non-zero relative intercept ($|b|/\max(|F|) \approx 0.1915$) arising from 3D electric field redistribution across the dielectric interface.
   - Recorded component closure table across mesh levels for FIG. 21, confirming that net residual fails closed ($|F_{\text{net}}| \approx 25\text{ mN} \gg 23.7\ \mu\text{N}$).
   - Maintained strict unverified mechanical accounting: `finite_3d_dielectric_virtual_work_x_n = None`, `whole_body_3d_mechanical_accounting = "UNVERIFIED_PENDING_CONFORMING_INTERFACE_MESHING"`, and `finite_3d_is_conserved = False`.
4. **Mandatory Axial Convergence Evidence & Multi-Body Discretization Uncertainty in Production Gate (P2-R8-F4):**
   - Centralized production gate `evaluate_physical_scale_discrimination_gate` strictly requires qualified axial discretization evidence (`z_mesh_discretization_uncertainty_n`); verified states with missing axial evidence are rejected with `"NOT_RESOLVED_MISSING_AXIAL_GRID_DISCRETIZATION_EVIDENCE"`.
   - In `run_3d_mesh_convergence_study`, evaluated multi-body discretization uncertainty across all bodies (`max(body_discretization_errors)`), rather than relying on blade force alone.
   - Preserves `None/null` for uncalibrated components (never substituting 0.0 or returning non-standard NaNs).
5. **Strict JSON Finiteness & Semantic Consistency for Exported Manifests (P2-R8-F5):**
   - Serialized all manifests using `json.dump(..., allow_nan=False)`, eliminating non-standard `NaN` and `Infinity` tokens and guaranteeing RFC 8259 compliance.
   - In uncalibrated full-length FIG. 21 model, preserved `None/null` in `domain_boundary_clearance_uncertainty_n`, `domain_boundary_placement_sensitivity_n`, `combined_uncertainty_rss_n`, and `conservative_uncertainty_linear_n`.
   - Added strict JSON parse, recursive finiteness, and semantic consistency assertions in both unit tests and CI workflow against actual generated manifests.
6. **Strict Bounds Checking for True 3D Patent-Face H1 Quadrature (P2-R8-M1):**
   - Added strict input validation to `compute_3d_patent_face_h1_quadrature`, raising `ValueError` on empty spans (`blade_tip_spans=[]`), reversed spans ($b_{\min} > b_{\max}$), and non-positive/non-finite grid steps ($dx, dy, dz \le 0$ or non-finite).
7. **Numeric Round Discovery & Metadata Consistency (P2-R8-M2):**
   - Updated `discover_governing_review_round()` with integer round extraction and sorting (`max(..., key=lambda x: x[0])`).
   - Set `CURRENT_GOVERNING_REVIEW = "P2_R8_REMEDIATION"`. Added strict match validation (`require_match=True`).

---

## 2. Review Disposition Tracking

| Finding | Severity | Status | Remediation Summary |
|---|---|---|---|
| **P2-R8-F1** | High | **RESOLVED** | Expanded `compare_fig21_surrogate_to_declared_article` across 3 lengths ($L_z \in [0.0254, 0.0508, 0.1016\text{ m}]$), fit linear regression ($R^2 = 1.000000$, max residual $< 25\ \mu\text{N}$, $f_{\text{interior}} = -6.957\text{ N/m}$, $+7.22\text{ mN}$ end relief), labeled as single-grid empirical fit observation; tracked inter-level per-body differences $\Delta F_k > 23.7\ \mu\text{N}$ in 3-level convergence test. |
| **P2-R8-F2** | High | **RESOLVED** | Expanded `calibrate_domain_clearance_uncertainty_3d` across 3 clearance multipliers ($1.0\times, 1.5\times, 2.0\times$), verified monotonic coupling decay ($7.05\text{ mN} \to 2.33\text{ mN}$), standardized nomenclature as boundary placement sensitivity estimate (`FINITE_DIFFERENCE_PLACEMENT_SENSITIVITY_ESTIMATE_NOT_PROVEN_INFINITE_BOUND`). |
| **P2-R8-F3** | High | **RESOLVED** | Tested permittivity sweep ($\varepsilon_r \in [1.5, 2.5, 3.8, 5.0]$) verifying susceptibility monotonicity ($R^2 > 0.98$); documented non-zero intercept ($|b|/\max(|F|) \approx 0.19$) from 3D field redistribution; recorded component closure table across mesh levels; maintained fail-closed mechanical accounting (`UNVERIFIED_PENDING_CONFORMING_INTERFACE_MESHING`). |
| **P2-R8-F4** | High | **RESOLVED** | Made physical acceptance contingent upon present and qualified axial convergence evidence (`z_mesh_discretization_uncertainty_n`), failing closed with `"NOT_RESOLVED_MISSING_AXIAL_GRID_DISCRETIZATION_EVIDENCE"` on omission; evaluated multi-body discretization error across all bodies (`max(body_errors)`) in mesh convergence study. |
| **P2-R8-F5** | High | **RESOLVED** | Preserved `None/null` for uncalibrated domain uncertainty (never 0.0 or NaN); serialized all JSON with `allow_nan=False`; added strict recursive finiteness and semantic consistency assertions in both unit tests and CI workflow against actual generated manifests. |
| **P2-R8-M1** | Medium | **RESOLVED** | Added strict validation in `compute_3d_patent_face_h1_quadrature` raising `ValueError` on empty `blade_tip_spans=[]`, reversed spans ($b_{\min} > b_{\max}$), and non-positive/non-finite $dx, dy, dz$. |
| **P2-R8-M2** | Low | **RESOLVED** | Implemented integer-sorted review discovery in `discover_governing_review_round()`; updated constant `CURRENT_GOVERNING_REVIEW = "P2_R8_REMEDIATION"`; added consistency regression test with `require_match=True`. |

---

## 3. Test Suite & Baseline Integrity

- **P0 Baseline Preservation:** `git hash-object electrostatics_baseline.py` = `97f65dfa25db7730323edd5e52c98b17371fdeaa` (byte-for-byte identical).
- **P1 Baseline Preservation:** All P1 source and test files preserved byte-for-byte.
- **Full Test Suite:** **126 tests passed** (35 P0 + 37 P1 + 54 P2):
  - `tests/test_electrostatics_baseline.py`: 35 tests passed
  - `tests/test_p1_wave_3d.py` & `tests/test_p1_numerics.py`: 37 tests passed
  - `tests/test_p2_exodus_patent.py`: 54 tests passed
- **Artifacts:**
  - `electrostatics_baseline.png` & `electrostatics_manifest.json` (P0)
  - `exodus_patent_comparison.png` & `exodus_patent_manifest.json` (P2)
- **Governance:** PR remains DRAFT. Merge authorization NOT GRANTED. No auto-merge, no P3 kickoff.
