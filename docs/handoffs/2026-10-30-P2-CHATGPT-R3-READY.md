# SCALAR WAVE VIZ — P2 R3 INDEPENDENT SCIENTIFIC RE-REVIEW HANDOFF

**Repository:** https://github.com/aguacatero/scalar-wave-viz  
**Pull Request:** https://github.com/aguacatero/scalar-wave-viz/pull/11  
**Issue:** https://github.com/aguacatero/scalar-wave-viz/issues/7  
**Branch:** `p2-patent-geometry-exodus-2026-10-25`  
**Milestone:** Phase P2 — Exodus patent US11511891B2 FIGS. 4–8 reproduction & hypothesis separation  
**Review Round:** P2 R3  
**Governing Review:** Independent scientific review P2 R2 ([issuecomment-6460061166](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6460061166))  
**Operating Mode:** MANUAL-ONLY  
**Merge Authorization:** NOT GRANTED (PR remains DRAFT pending independent review)  

---

## 1. Executive Summary

This handoff remediates all findings from ChatGPT's independent scientific review of Phase P2 R2 ([issuecomment-6460061166](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6460061166)), which concluded `CHANGES REQUIRED — P2 R2 NOT ACCEPTED` across 3 High and 2 Medium findings (`P2-R2-F1` through `P2-R2-F3`, `P2-R2-M1`, and `P2-R2-M2`).

Phase P2 reproduces the Exodus Propulsion Technologies patent [US11511891B2](https://patents.google.com/patent/US11511891B2/en) (issued November 29, 2022) embodiment depicted in FIGS. 4–8 (single-stage schematic) and separates it from the FIG. 21 nine-blade epoxy-potted test article.

Key physical and numerical advancements in R3:
1. **Direct 6-Wall Electrostatic Surface Traction (F3):** Evaluates electrostatic surface traction directly on all 6 outer bounding physical walls (`compute_direct_enclosure_wall_tractions_3d`), establishing independent mechanical wall reaction without contour subtraction or algebraic tautology ($F_{\text{net}} = F_{\text{blade}} + F_{\text{ground}} + F_{\text{dielectric}} + F_{\text{wall,direct}}$). Surface traction matches diagnostic inner contour outward stress flux to $< 0.5\%$.
2. **Predeclared Force Budget & Residual Classification (F2):** Distinguishes linear algebra solver residual ($8.43\times 10^{-11}$) from discrete momentum closure residual ($\mu\text{N}$). Evaluates momentum conservation against the predeclared patent target effect budget ($237\ \mu\text{N}$). Coarse 3D grid with $\sim 593\ \mu\text{N}$ residual fails conservation closed (`finite_3d_is_conserved = False`, status `"RESIDUAL_EXCEEDS_TARGET_EFFECT_SCALE_AT_COARSE_RESOLUTION"`).
3. **Asymptotic Convergence & Discretization Metrics (F1):** 2D mesh convergence across 4 commensurate grid spacings ($h_0/k = 1.27, 0.635, 0.423, 0.3175\text{ mm}$) where actual-to-target geometry ratios remain exactly 1.0000. Monotonically decreasing step-to-step relative change $\delta_k = |F_k - F_{k-1}| / |F_k|$ ($12.18\% \to 6.17\% \to 2.61\%$), Richardson extrapolated continuum limit ($-70.1\text{ mN}$), and estimated discretization uncertainty are computed.
4. **Domain Clearance Sweeps & 3D FIG. 21 Nine-Blade Embodiment (F1):** 3D clearance sweeps over enclosure clearance $U$ and end margin $Z$ demonstrate domain stability. 3D finite boundary-value model evaluates the FIG. 21 nine-blade epoxy-potted article in 3D ($F_{\text{blade}} \approx -604.4\text{ mN}$, $F_{\text{ground}} \approx +622.5\text{ mN}$, $F_{\text{dielectric}} \approx -2.18\text{ mN}$, $F_{\text{wall}} \approx -15.20\text{ mN}$).
5. **Epistemic Tightening & PR Metadata Update (M1, M2):** Replaced `true_3d_*` nomenclature with `finite_3d_*` to clarify numerical approximation vs physical measurement; updated PR #11 description to eliminate stale R1 claims; added near-tip field scaling test flagging omitted tip rounding radius $r_{\text{tip}}$.

---

## 2. P2 R2 Review Finding Remediation Matrix

| Finding ID | Severity | Canonical Finding Description | Implemented Remediation & Physical Resolution |
| :--- | :--- | :--- | :--- |
| **P2-R2-F1** | **HIGH** | Force *convergence* is not demonstrated by monotonic changes or a convergent 3D/2D ratio | Evaluated 2D mesh convergence across 4 commensurate grid spacings ($h_0/k = 1.27, 0.635, 0.423, 0.3175\text{ mm}$), where actual-to-target geometry ratios ($w_{\text{tip}}$, gap, blade height) remain exactly 1.0000. Quantified asymptotic step-to-step relative change $\delta_k = \|F_k - F_{k-1}\| / \|F_k\|$, which drops monotonically ($12.18\% \to 6.17\% \to 2.61\%$). Computed Richardson extrapolated continuum limit ($-70.1\text{ mN}$) and estimated discretization truncation error ($< 15\%$). Added 3D domain sweeps for outer enclosure clearance $U$ (`run_3d_enclosure_clearance_sweep`) and end margin $Z$ (`run_3d_end_clearance_sweep`). Solved 3D finite-difference model for the FIG. 21 nine-blade epoxy test article (`fig21_nine_blade_3d_finite_model`), confirming opposing internal electrode forces ($~600\text{ mN}$) and finite boundary reactions. |
| **P2-R2-F2** | **HIGH** | 3D force residual tolerance (1,500 µN) exceeds target effect scale (237 µN) | Removed unprincipled 1,500 µN tolerance. Explicitly distinguished linear algebra solver residual ($8.43\times 10^{-11}$) from discrete momentum closure residual ($\mu\text{N}$) and mesh truncation uncertainty ($\mu\text{N}$). Enforced scientific acceptance threshold from predeclared patent target effect budget ($237\ \mu\text{N}$). Coarse 3D grid ($\Delta x = 2\text{ mm}$) with net residual $\sim 593\ \mu\text{N} > 237\ \mu\text{N}$ fails closed (`finite_3d_is_conserved = False`, status `"RESIDUAL_EXCEEDS_TARGET_EFFECT_SCALE_AT_COARSE_RESOLUTION"`). Added adversarial test `test_adversarial_rejection_of_unconverged_or_permissive_3d_force`. |
| **P2-R2-F3** | **HIGH** | 3D "independent dielectric and enclosure reactions" algebraically reduced to nested contour differences | Implemented `compute_direct_enclosure_wall_tractions_3d()` integrating the Maxwell stress tensor directly across all 6 outer bounding physical walls (normal traction $T_{xx} = \frac{1}{2}\varepsilon_0 \varepsilon_r (E_x^2 - E_y^2 - E_z^2)$ on $\pm x$ walls, shear tractions $T_{xy} = \varepsilon_0 \varepsilon_r E_x E_y$ on $\pm y$ walls, and $T_{xz} = \varepsilon_0 \varepsilon_r E_x E_z$ on $\pm z$ walls). Direct 6-wall surface traction matches diagnostic inner-contour outward stress flux to $0.425\%$ at 2.0 mm and $0.219\%$ at 1.5 mm. Whole-system net force sums direct wall reaction with blade, ground, and dielectric ($F_{\text{net}} = F_{\text{blade}} + F_{\text{ground}} + F_{\text{dielectric}} + F_{\text{wall,direct}}$). Dielectric reaction tagged explicitly as `dielectric_force_status = "INFERRED_FROM_ENCLOSING_CONTOUR_STRESS_DIFFERENCE"`. |
| **P2-R2-M1** | **MED** | Active PR #11 description still contained stale R1 text | Rewrote PR #11 description via GitHub CLI (`gh pr edit 11 --body-file ...`), replacing stale R1 text (claims of 40 kV, high-vacuum, $\le 0.4\ \mu\text{N}$, 592x ratio, 17 tests) with accurate R3 metadata: separated single-stage schematic vs FIG. 21 9-blade potted article, 112 tests, 237 µN target scale budget, and accurate contextual characterization of Tajmar & Schreiber (2020). Added `test_adversarial_rejection_of_stale_pr_or_literature_metadata`. |
| **P2-R2-M2** | **MED** | Force metric/test assumptions and visualized labels need epistemic tightening | Replaced `true_3d_*` nomenclature with `finite_3d_*` in `Finite3DModelResult`, manifest, and visualizer Panel B (retaining backward-compatible `@property` aliases for callers). Explicitly marked 3D results as finite-length numerical approximations, with convergence and physical geometry accuracy labeled UNVERIFIED pending experimental laboratory measurement. Added near-tip field scaling test `test_h1_near_tip_field_mesh_refinement_convergence` demonstrating $E_{\text{tip}}$ increases with $1/\Delta x$ due to the rectangular blade corner singularity ($E \sim r^{-1/3}$) from omitting tip rounding radius $r_{\text{tip}}$ in the patent. |

---

## 3. Changed Scope & File Inventory

- [`exodus_patent_geometry.py`](file:///Users/chrisrodriguez/Documents/scalar-wave/exodus_patent_geometry.py):
  - Added geometry discretization tracking fields to `ExodusGrid2D` (`target_tip_width_m`, `discretized_tip_width_m`, `tip_width_discretization_ratio`, `target_gap_m`, `discretized_gap_m`, `gap_discretization_ratio`, `target_blade_height_m`, `discretized_blade_height_m`, `blade_height_discretization_ratio`).
  - Added `enclosure_margin_z_m: float = 0.020` to `ExodusPatentParameters`.
  - Populated geometry tracking fields in `build_exodus_2d_grid()` and `build_inverted_180_grid()`.
- [`exodus_hypothesis_evaluator.py`](file:///Users/chrisrodriguez/Documents/scalar-wave/exodus_hypothesis_evaluator.py):
  - Added `DirectWallTractionForces3D` dataclass.
  - Implemented `compute_direct_enclosure_wall_tractions_3d()` integrating Maxwell stress on all 6 physical outer walls.
  - Updated `Finite3DModelResult` dataclass: switched to `finite_3d_*` fields, added direct wall tractions, agreement metric, target effect budget ($237\ \mu\text{N}$), geometry discretization metrics, dielectric force status, and backward-compatible `@property` aliases for `true_3d_*`.
  - Updated `solve_exodus_electrostatics_3d()`: evaluates direct 6-wall surface traction, enforces 237 µN budget, fails coarse grids closed, and computes geometry tracking.
  - Implemented `run_3d_enclosure_clearance_sweep()` and `run_3d_end_clearance_sweep()`.
  - Updated `run_mesh_convergence_study()`: computes step-to-step relative change $\delta_k$, Richardson extrapolated limit, estimated discretization uncertainty, and tip mean/max fields across 4 commensurate grid spacings.
  - Updated `run_3d_mesh_convergence_study()`: computes relative changes $\delta_k$, Richardson extrapolation, and discretization error.
  - Updated `generate_exodus_patent_manifest()`: separates linear solve residual from discrete momentum closure residual, adds direct wall breakdown and target effect ratio, evaluates 3D FIG. 21 9-blade potted article (`fig21_nine_blade_3d_finite_model`), and updates epistemic warnings.
  - Updated `compute_h1_patent_prediction()` proof obligations flagging omitted $r_{\text{tip}}$ corner singularity.
- [`examples/exodus_patent_demo.py`](file:///Users/chrisrodriguez/Documents/scalar-wave/examples/exodus_patent_demo.py):
  - Panel B updated to "Finite 3D Approx" nomenclature and force accounting.
  - Panel D updated to reflect 4-point commensurate convergence and Richardson extrapolation.
- [`tests/test_p2_exodus_patent.py`](file:///Users/chrisrodriguez/Documents/scalar-wave/tests/test_p2_exodus_patent.py):
  - Expanded test suite from 34 to 40 P2 tests (112 total repository tests).
  - Added `test_3d_direct_six_wall_surface_traction_matches_inner_contour`.
  - Added `test_adversarial_rejection_of_unconverged_or_permissive_3d_force`.
  - Added `test_3d_enclosure_clearance_and_end_margin_sweeps`.
  - Added `test_3d_nine_blade_epoxy_test_article_solve`.
  - Added `test_h1_near_tip_field_mesh_refinement_convergence`.
  - Added `test_adversarial_rejection_of_stale_pr_or_literature_metadata`.
  - Updated `test_finite_3d_model_solver_convergence_opposing_forces_and_conservation`, `test_finite_3d_mesh_refinement_convergence`, and `test_2d_mesh_convergence_study_monotone_and_conserved`.
- **Documentation & Roadmap Synchronization:**
  - [`README.md`](file:///Users/chrisrodriguez/Documents/scalar-wave/README.md): Synchronized research progress narrative to P2 R3 re-review (2 of 5 gates accepted; P2 active in Draft PR #11).
  - [`docs/ROADMAP.md`](file:///Users/chrisrodriguez/Documents/scalar-wave/docs/ROADMAP.md): Preserved P2 roadmap checkboxes as `[ ]` (unchecked) pending independent acceptance and updated P2 status narrative.

---

## 4. Preservation of Prior Accepted Baselines

- **P0 Baseline Preservation:** `electrostatics_baseline.py` Git blob `97f65dfa25db7730323edd5e52c98b17371fdeaa` verified byte-identical.
- **P1 Baseline Preservation:** All P1 numerical validation files (`scalar_wave_3d.py`, `electrostatics_numerics.py`) and all 72 P0/P1 tests preserved unchanged.

---

## 5. Reviewer Acceptance Criteria (P2 R3)

1. **Direct 6-Wall Electrostatic Surface Traction (F3):** Does `compute_direct_enclosure_wall_tractions_3d()` integrate the Maxwell stress tensor directly across all 6 physical outer walls without contour subtraction, achieve $< 0.5\%$ agreement with diagnostic inner contour stress flux, and participate directly in whole-system momentum accounting?
2. **Predeclared Force Budget & Residual Classification (F2):** Does the 3D model distinguish linear algebra solver residual ($8.43\times 10^{-11}$) from discrete momentum closure residual ($\mu\text{N}$), enforce the predeclared $237\ \mu\text{N}$ target effect scale, and fail coarse grids closed (`finite_3d_is_conserved = False`, status `"RESIDUAL_EXCEEDS_TARGET_EFFECT_SCALE_AT_COARSE_RESOLUTION"`)?
3. **Asymptotic Convergence & Commensurate Discretization (F1):** Do the 2D commensurate grids maintain exact 1.0000 geometry ratios, does step-to-step relative change $\delta_k$ drop monotonically ($12.18\% \to 6.2\% \to 2.6\%$), and are Richardson extrapolated limits and discretization uncertainties computed?
4. **Domain Clearance Sweeps & 3D FIG. 21 Embodiment (F1):** Do 3D clearance sweeps over $U$ and $Z$ confirm domain stability, and is the FIG. 21 nine-blade epoxy article evaluated in 3D?
5. **Epistemic Discipline & Metadata Accuracy (M1, M2):** Are 3D results labeled as finite numerical approximations (`finite_3d_*`) rather than physical measurements, has the PR description been purged of stale claims, and does near-tip field analysis flag the omitted tip rounding radius $r_{\text{tip}}$?

---

**ANNOUNCEMENT: READY FOR CHATGPT INDEPENDENT RE-REVIEW — P2 R3**
