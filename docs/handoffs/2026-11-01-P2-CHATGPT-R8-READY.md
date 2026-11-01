# SCALAR WAVE VIZ — P2 R8 INDEPENDENT SCIENTIFIC RE-REVIEW HANDOFF

**Repository:** https://github.com/aguacatero/scalar-wave-viz  
**Pull Request:** https://github.com/aguacatero/scalar-wave-viz/pull/11  
**Issue:** https://github.com/aguacatero/scalar-wave-viz/issues/7  
**Branch:** `p2-patent-geometry-exodus-2026-10-25`  
**Milestone:** Phase P2 — Exodus patent US11511891B2 FIGS. 4–8 reproduction & hypothesis separation  
**Review Round:** P2 R8  
**Governing Review:** Independent scientific review P2 R7 ([issuecomment-6559262041](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6559262041))  
**Operating Mode:** MANUAL-ONLY  
**Merge Authorization:** NOT GRANTED (PR remains DRAFT pending independent review; no auto-merge, no P3 kickoff)  

---

## 1. Executive Summary

This handoff remediates all findings from ChatGPT's independent scientific review of Phase P2 R7 ([issuecomment-6559262041](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6559262041)), which concluded `CHANGES REQUIRED — P2 R7 SCIENTIFIC BASELINE NOT ACCEPTED` across 4 High, 1 Medium, and 1 Low findings (`P2-R7-F1`, `P2-R7-F2`, `P2-R7-F3`, `P2-R7-F4`, `P2-R7-M1`, and `P2-R7-M2`).

Phase P2 reproduces the Exodus Propulsion Technologies patent [US11511891B2](https://patents.google.com/patent/US11511891B2/en) (issued November 29, 2022) embodiment depicted in FIGS. 4–8 (single-stage schematic) and separates it from the FIG. 21 nine-blade epoxy-potted test article.

Key physical and numerical advancements in R8:
1. **Surrogate vs Declared Article Transfer Scaling & Multi-Level Bounds (P2-R7-F1):**
   - Formally distinguished shortened surrogate (`FIG21_MODEL_VARIANT_SHORTENED_AXIAL_SURROGATE_25MM`, $L_z = 25.4\text{ mm} = 1.0\text{ in}$) from the declared full test article (`FIG21_MODEL_VARIANT_DECLARED_ARTICLE_101MM`, $L_z = 101.6\text{ mm} = 4.0\text{ in}$).
   - Implemented `compare_fig21_surrogate_to_declared_article`: solved both geometries on matched commensurate grids ($dx=1.27\text{ mm}, dz=2.54\text{ mm}$), demonstrating $4.000\times$ length scaling, interior force density $f_{\text{interior}} = -6.957\text{ N/m}$, and isolating constant end-cap fringing relief ($+7.22\text{ mN}$, $1.03\%$ of total force).
   - In `test_fig21_nine_blade_multilevel_mesh_convergence`, recorded level-by-level per-body table and asserted predeclared numerical bounds across all 3 levels for blade, ground, dielectric, wall, net residual, H1 proximal, and H1 distal.
   - Documented ground sheet non-asymptotic coarse-grid thinning ($5.08, 2.54, 1.693$), explaining fractional order $p_{\text{obs}} \approx 0.80$.
2. **Domain Clearance Sensitivity Calibration in 3D & Ledger Separation (P2-R7-F2):**
   - Expanded `calibrate_domain_clearance_uncertainty_3d` across all 3 dimensions ($x, y, z$).
   - Integrated boundary placement sensitivity directly into `solve_exodus_electrostatics_3d` and propagated through `Finite3DModelResult`, manifest, and the production discrimination gate.
   - Strictly separated direct electrostatic surface traction on outer bounding walls (`direct_wall_reaction_x_n`) from numerical boundary placement sensitivity (`domain_boundary_placement_sensitivity_n`).
   - Unit tests verify that altering domain placement sensitivity directly alters the production gate RSS and linear uncertainty bounds.
3. **FIG. 21 Potting Dielectric Linearity & Multi-Resolution Tracking (P2-R7-F3):**
   - Evaluated permittivity sweep across $\varepsilon_r \in [1.5, 2.5, 3.8, 5.0]$ on FIG. 21, verifying linear proportionality of interface traction to $(\varepsilon_r - 1)$ with $R^2 = 0.9846 > 0.98$.
   - Evaluated multi-resolution interface-to-contour agreement sequence at nominal $\varepsilon_r = 3.8$ across 2 mesh levels.
   - Documented Korteweg-Helmholtz limiting field conventions.
   - Maintained strict fail-closed status: `whole_body_3d_mechanical_accounting = "UNVERIFIED_PENDING_CONFORMING_INTERFACE_MESHING"`, `finite_3d_dielectric_virtual_work_x_n = None`, and production gate fails closed.
4. **Discretization Uncertainty Distinction & Quadrature Combination in Production Gate (P2-R7-F4):**
   - Distinguished observed finite difference estimates from proven bounds (`axial_grid_sensitivity_estimate_n` with assumed $p=1$).
   - Combined lateral and axial discretization uncertainties in quadrature ($u_{\text{mesh,total}} = \sqrt{u_{\text{mesh},xy}^2 + u_{\text{mesh},z}^2}$) within `evaluate_physical_scale_discrimination_gate`.
   - Tracked component-by-component convergence metrics in budget summary.
5. **Strict Bounds Checking & Non-Uniform Offset Sensitivity for True 3D H1 Quadrature (P2-R7-M1):**
   - Added strict input validation to `compute_3d_patent_face_h1_quadrature`, raising `ValueError` on offsets $< 1$ or out-of-bounds indices.
   - Tested offset sensitivity on a 3D field with non-zero gradient along $x$, asserting $F(\text{offset}=1) \ne F(\text{offset}=2)$ and quantifying $\Delta F > 1.0\times 10^{-7}\text{ N}$.
   - Bounded precision assertions to $< 10^{-9}$ (9 decimal places).
6. **Automated Governing Review Metadata Discovery (P2-R7-M2):**
   - Implemented `discover_governing_review_round()` dynamically scanning `docs/reviews/` and extracting governing review round.
   - Set `CURRENT_GOVERNING_REVIEW = "P2_R7_REMEDIATION"`.
   - Added unit test asserting consistency across discovery, constant, and manifest serialization.

---

## 2. Review Disposition Tracking

| Finding | Severity | Status | Remediation Summary |
|---|---|---|---|
| **P2-R7-F1** | High | **RESOLVED** | Differentiated surrogate vs declared article variants; implemented `compare_fig21_surrogate_to_declared_article` ($4.000\times$ length ratio, $1.03\%$ end relief); recorded level-by-level per-body numerical values with predeclared bounds; documented ground thinning ratios ($5.08, 2.54, 1.693$). |
| **P2-R7-F2** | High | **RESOLVED** | Expanded domain clearance calibration to full 3D ($x, y, z$); integrated into production solve and manifest; strictly separated wall reaction from boundary placement sensitivity; tested production gate RSS response. |
| **P2-R7-F3** | High | **RESOLVED** | Tested permittivity sweep ($\varepsilon_r \in [1.5, 2.5, 3.8, 5.0]$) verifying linear proportionality to $(\varepsilon_r - 1)$ ($R^2 = 0.9846 > 0.98$); evaluated multi-resolution interface-to-contour agreement; documented limiting conventions; maintained unverified fail-closed gate. |
| **P2-R7-F4** | High | **RESOLVED** | Distinguished observed finite differences from proven bounds; combined lateral and axial discretization uncertainties in quadrature ($u_{\text{mesh,total}} = \sqrt{u_{xy}^2 + u_z^2}$) in gate; tracked component-by-component metrics. |
| **P2-R7-M1** | Medium | **RESOLVED** | Added strict bounds checking in `compute_3d_patent_face_h1_quadrature` raising `ValueError`; tested offset sensitivity on non-uniform $x$-gradient field; bounded precision claims to $< 10^{-9}$. |
| **P2-R7-M2** | Low | **RESOLVED** | Implemented `discover_governing_review_round()` dynamically scanning `docs/reviews/`; set `CURRENT_GOVERNING_REVIEW = "P2_R7_REMEDIATION"`; added consistency regression test. |

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
