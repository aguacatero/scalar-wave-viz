# SCALAR WAVE VIZ — P2 R2 INDEPENDENT SCIENTIFIC RE-REVIEW HANDOFF

**Repository:** https://github.com/aguacatero/scalar-wave-viz  
**Pull Request:** https://github.com/aguacatero/scalar-wave-viz/pull/11  
**Issue:** https://github.com/aguacatero/scalar-wave-viz/issues/7  
**Branch:** `p2-patent-geometry-exodus-2026-10-25`  
**Milestone:** Phase P2 — Exodus patent US11511891B2 FIGS. 4–8 reproduction & hypothesis separation  
**Review Round:** P2 R2  
**Governing Review:** Independent scientific review P2 R1 ([issuecomment-6415952244](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6415952244))  
**Operating Mode:** MANUAL-ONLY  
**Merge Authorization:** NOT GRANTED (PR remains DRAFT pending independent review)  

---

## 1. Executive Summary

This handoff remediates all findings from ChatGPT's independent scientific review of Phase P2 R1 ([issuecomment-6415952244](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6415952244)), which concluded `CHANGES REQUIRED — P2 R1 NOT ACCEPTED` across 6 High and 2 Medium findings (`P2-R1-F1` through `P2-R1-F6`, `P2-R1-M1`, and `P2-R1-M2`).

Phase P2 reproduces the Exodus Propulsion Technologies patent [US11511891B2](https://patents.google.com/patent/US11511891B2/en) (issued November 29, 2022) embodiment depicted in FIGS. 4–8 (single-stage schematic) and separates it from the FIG. 21 nine-blade epoxy-potted test article, establishing strict physical and numerical separation between:
1. **Model H0 (Conventional Electrodynamics & Maxwell Stress Baseline):** Conservative finite-difference solution of $\nabla \cdot (\varepsilon \nabla V) = 0$, analytic parallel-plate Maxwell-stress benchmark (`benchmark_analytic_parallel_plate_maxwell_stress`), direct electrostatic surface wall tractions $T_n = \frac{1}{2} \varepsilon_0 \varepsilon_r E_n^2$ on the outer grounded enclosure, non-tautological whole-system force summation ($F_{\text{net}} = F_{\text{blade}} + F_{\text{ground}} + F_{\text{dielectric}} + F_{\text{wall}}$), non-overlapping gap-clamped contour-offset and enclosure-clearance sweeps, Korteweg-Helmholtz dielectric reaction accounting, and a constrained 3D SPD CG finite-difference solver with 6-face Maxwell stress integration capturing finite blade length ($L_z = 101.6\text{ mm}$) and 3D end fringing.
2. **Model H1 (Patent-Specific Hypothesis US11511891B2 Eq. 4–11):** Strict material-side boundary face quadrature of patent Eq. (11) $F = \varepsilon_0 (E_2^2 A_2 - E_1^2 A_1)$ evaluated strictly outside conductors on 1-cell-thick exterior boundary masks (`mask_proximal_100a`, `mask_distal_101a`, `mask_connecting_100b`), fencepost-free face widths ($w_2 = 1.5\text{ mm}$, $w_1 = 30.0\text{ mm}$ at $\Delta y = 0.5\text{ mm}$), side-by-side comparison of exact face quadrature vs. spatial-mean plug-in (demonstrating Cauchy-Schwarz discrepancy $\int E^2\,dA > \langle E\rangle^2 A$), missing $\frac{1}{2}$ factor detection, and a formal proof-obligation refutation of the Eq. (4) stationary-action claim.
3. **Programmatically Evaluated Numerical Controls & Contextual Literature Audit:** Solver-executed numerical controls (`+V` vs. `-V` polarity reversal on both $|\mathbf{E}|$ and $F_x$, $V = 0$ zero-voltage control, symmetric parallel-plate control with opposing internal forces and zero net force, $180^\circ$ spatial inversion BVP solve verifying exact sign reversal $F_{x,\text{inv}} = -F_{x,\text{base}}$, and asymmetric enclosure wall proximity control) enforced by a fail-closed programmatic gate (`verify_control_assertions`), alongside an accurate contextual audit of [Tajmar & Schreiber (2020)](https://doi.org/10.1016/j.elstat.2020.103477).

---

## 2. P2 R1 Review Finding Remediation Matrix

| Finding ID | Severity | Canonical Finding Description | Implemented Remediation & Physical Resolution |
| :--- | :--- | :--- | :--- |
| **P2-R1-F1** | **HIGH** | Literature benchmark mischaracterizes Tajmar & Schreiber (2020) and fabricates false ratio | Audited primary paper (`10.1016/j.elstat.2020.103477`): Tajmar & Schreiber (2020) tested 13 asymmetric capacitors in a self-contained battery-powered HV setup inside a double-walled Faraday cage on a precision balance (measuring apparent weight changes without external HV lead wires) up to $10\text{ kV}$, finding null results within $\pm 0.3\text{ mg}$ ($\approx \pm 2.94\ \mu\text{N}$). Removed all "vacuum torsion balance" and fabricated $592.5\times$ ratio claims; separated non-identical apparatuses in `LiteratureBenchmarkAudit` and Panel C; framed corona/ion wind, HV lead-wire forces, and chamber Coulomb attraction as candidate confounders requiring experimental discrimination rather than established causes. |
| **P2-R1-F2** | **HIGH** | Material-side boundary fields, areas, and face sampling in H1 are incorrect | Redesigned `mask_proximal_100a`, `mask_distal_101a`, and `mask_connecting_100b` as strictly 1-cell-thick exterior boundary layers of the conductor. Removed `+1` fencepost inflation so discrete widths equal $n \cdot \Delta y$ ($w_2 = 1.5\text{ mm}$, $w_1 = 30.0\text{ mm}$ at $\Delta y = 0.5\text{ mm}$). Implemented both exact material-side face quadrature $\varepsilon_0 \int |\mathbf{E}|^2\,dl$ and spatial-mean plug-in $\varepsilon_0 \langle |\mathbf{E}|\rangle^2 w$, backed by analytical uniform-field and nonuniform-field regression tests. |
| **P2-R1-F3** | **HIGH** | Discretization, missing parameters, and parameter ledger inconsistencies | Implemented 5-category `ParameterStatus` taxonomy (`PATENT_EXPLICIT_VALUE` for `V, P, N, T1, Q, S`; `DERIVED_FROM_PATENT` for `S1, T, M`; `EXTERNAL_ESTIMATE_FOR_UNSPECIFIED` for `epsilon_r, T2`; `MODELING_ASSUMPTION` for `O, U`; `PATENT_OMITTED_UNKNOWN` for `r_tip, tan_delta, D_enclosure, wiring_geometry`). Synchronized `consumed_value_si` dynamically with the active `ExodusPatentParameters` instance. Added factory presets `figs_4_to_8_schematic()` (1 blade, $\varepsilon_r = 1.0$) and `fig_21_nine_blade_article()` (9 blades, $\varepsilon_r = 3.8$). `ground_plane_thickness_m` directly controls ground electrode mask thickness. |
| **P2-R1-F4** | **HIGH** | Whole-apparatus force accounting, enclosure boundaries, and clearance are unstable | Eliminated tautological `f_box_reaction = -f_enclosure_inner` subtraction: `net_system_force_x` now sums `blade_force_x + ground_force_x + dielectric_force_x + enclosure_direct_wall_force_x` (`-27.4 µN` residual at $\Delta x = 0.5\text{ mm}$, $0.037\%$ of blade force). Clamped inter-electrode contour offsets to prevent gap overlap (`ground.ix_max < blade.ix_min`). Added Korteweg-Helmholtz dielectric reaction accounting for $\varepsilon_r \neq 1$, `benchmark_analytic_parallel_plate_maxwell_stress()`, `run_contour_offset_sweep()`, and `run_enclosure_clearance_sweep()`. |
| **P2-R1-F5** | **HIGH** | 2D vs. 3D force dimensions and fringing conflation | Replaced unpreconditioned 3D `bicgstab` with a strictly SPD free-DOF system solved via Jacobi-preconditioned Conjugate Gradient (`spla.cg(..., rtol=1e-10)`, achieving residual $8.43\times 10^{-11}$). Implemented full 6-face 3D Maxwell stress integration (`integrate_3d_maxwell_stress_box_x`) including $-0.5\varepsilon_0(E_y^2+E_z^2)$ and shear terms $T_{xy}, T_{xz}$, yielding opposing 3D forces ($F_{\text{blade},3D} = -50.31\text{ mN}$, $F_{\text{ground},3D} = +58.62\text{ mN}$), independent 3D enclosure reaction ($-7.74\text{ mN}$), computed fringing ratio ($0.9427$ at $\Delta x = 2\text{ mm}$, converging to $0.9792$ at $\Delta x = 1.2\text{ mm}$), and `run_3d_mesh_convergence_study()`. Unchecked premature P2 `[x]` items in `docs/ROADMAP.md`. |
| **P2-R1-F6** | **HIGH** | Controls are hard-coded assertions rather than programmatic checks | Fixed `emag_neg - emag_neg` bug to `base_e_mag - emag_neg` (`diff_emag_rel < 1e-10`). Implemented `build_inverted_180_grid(params)` and solved the mirrored BVP, verifying $F_{\text{blade,inv}} = +0.57496\text{ N/m} = -F_{\text{blade,base}}$. Fixed symmetric capacitor control so internal plate forces are equal and opposite ($\mp 0.2586\text{ N/m}$) while net force is zero ($< 10^{-14}\text{ N}$). Added asymmetric enclosure wall proximity control and `verify_control_assertions()` gate. |
| **P2-R1-M1** | **MED** | Regression suite lacks falsifying tests | Expanded `tests/test_p2_exodus_patent.py` to 34 tests (total repository test count: 106 tests). Added adversarial false-positive control rejection tests, analytical uniform/nonuniform H1 regressions, analytic parallel-plate H0 benchmark, dielectric Korteweg-Helmholtz closure test, 3D mesh convergence test, and 1-cell exterior surface mask geometry tests. |
| **P2-R1-M2** | **MED** | Evidence figure and manifest overstate achieved verification | Updated `examples/exodus_patent_demo.py`: Panel B reports 2D extruded H0, True 3D H0, and H1 quadrature forces; Panel C plots the 6 programmatically evaluated numerical controls and separates the non-identical experimental literature comparison in an accurate contextual note; Panel D plots smooth monotone convergence on patent-unit-commensurate grids ($1.27\text{ mm}, 0.635\text{ mm}, 0.423\text{ mm}$) plus the enclosure clearance sweep. Updated manifest disposition to `NOT_MEASURED_AND_NOT_EVALUATED_NUMERICAL_SIMULATION_ONLY`. |

---

## 3. Changed Scope & File Inventory

- [`exodus_patent_geometry.py`](file:///Users/chrisrodriguez/Documents/scalar-wave/exodus_patent_geometry.py):
  - 5-category `ParameterStatus` taxonomy and `consumed_value_si` synchronization in `get_patent_parameter_ledger(params)`.
  - Embodiment factory presets `figs_4_to_8_schematic()` and `fig_21_nine_blade_article()`.
  - Fencepost-free discretization, 1-cell-thick exterior surface masks (`mask_proximal_100a`, `mask_distal_101a`, `mask_connecting_100b`), and material-side `ConductorBoundaryFace` descriptors.
  - `build_symmetric_control_grid()` and `build_inverted_180_grid()`.
- [`exodus_hypothesis_evaluator.py`](file:///Users/chrisrodriguez/Documents/scalar-wave/exodus_hypothesis_evaluator.py):
  - Vectorized 2D and 3D finite-difference Laplace solvers (3D SPD free-DOF CG solver converging to $< 10^{-10}$).
  - Non-tautological H0 whole-apparatus force ledger summing direct enclosure wall tractions (`compute_direct_enclosure_wall_tractions`) and Korteweg-Helmholtz dielectric reaction forces.
  - `benchmark_analytic_parallel_plate_maxwell_stress()`, `run_contour_offset_sweep()`, `run_enclosure_clearance_sweep()`, `run_mesh_convergence_study()`, and `run_3d_mesh_convergence_study()`.
  - Full 6-face 3D Maxwell stress box integration (`integrate_3d_maxwell_stress_box_x`) and computed 3D-to-2D fringing ratio.
  - H1 material-side face quadrature alongside spatial-mean plug-in comparison (`compute_h1_patent_prediction`).
  - Programmatically evaluated controls (`evaluate_experimental_controls`) and fail-closed assertion gate (`verify_control_assertions`).
- [`examples/exodus_patent_demo.py`](file:///Users/chrisrodriguez/Documents/scalar-wave/examples/exodus_patent_demo.py):
  - Regenerates `exodus_patent_comparison.png` and `exodus_patent_manifest.json` with updated Panels A–D.
- [`tests/test_p2_exodus_patent.py`](file:///Users/chrisrodriguez/Documents/scalar-wave/tests/test_p2_exodus_patent.py):
  - 34 unit and adversarial regression tests covering all R1 findings (106 total tests across P0, P1, and P2).
- **Documentation & Roadmap Synchronization:**
  - [`README.md`](file:///Users/chrisrodriguez/Documents/scalar-wave/README.md): Synchronized research progress narrative (2 of 5 review gates accepted; P2 active in Draft PR #11 awaiting R2 re-review).
  - [`docs/ROADMAP.md`](file:///Users/chrisrodriguez/Documents/scalar-wave/docs/ROADMAP.md): Unchecked premature P2 `[x]` boxes back to `[ ]` pending independent acceptance and updated P2 status note.

---

## 4. Preservation of Prior Accepted Baselines

- **P0 Baseline Preservation:** `electrostatics_baseline.py` Git blob `97f65dfa25db7730323edd5e52c98b17371fdeaa` verified byte-identical.
- **P1 Baseline Preservation:** All P1 numerical validation files (`scalar_wave_3d.py`, `electrostatics_numerics.py`) and 72 P0/P1 tests preserved unchanged.

---

## 5. Reviewer Acceptance Criteria (P2 R2)

1. **Accurate Literature Grounding (F1):** Does `LiteratureBenchmarkAudit`, Panel C, and the manifest accurately characterize Tajmar & Schreiber (2020) as a self-contained battery-powered HV setup inside a Faraday cage on a precision balance ($10\text{ kV}$, $\pm 0.3\text{ mg} \approx \pm 2.94\ \mu\text{N}$) and frame ion-wind/wire/wall couplings as candidate confounders rather than established causes?
2. **Strict Boundary Face Quadrature & Exterior Masks (F2):** Are `100a`, `101a`, and `100b` 1-cell-thick exterior boundary masks, are face widths fencepost-free ($w_2 = 1.5\text{ mm}, w_1 = 30.0\text{ mm}$ at $\Delta y = 0.5\text{ mm}$), and do analytical uniform/nonuniform field regressions validate `compute_h1_patent_prediction()`?
3. **5-Category Parameter Taxonomy & Embodiment Separation (F3):** Does `get_patent_parameter_ledger(params)` synchronize `consumed_value_si` with `params`, classify all symbols across the 5-category taxonomy, and separate FIGS. 4–8 from FIG. 21?
4. **Non-Tautological H0 Accounting & Analytic Benchmark (F4):** Does `net_system_force_x` genuinely sum `blade + ground + dielectric + direct_wall` without tautological subtraction, keep contours disjoint in the gap, close Korteweg-Helmholtz dielectric forces, and pass the analytic parallel-plate Maxwell-stress benchmark?
5. **Converged 3D SPD CG Solver & 6-Face Maxwell Stress (F5):** Does `solve_exodus_electrostatics_3d()` converge to $< 10^{-8}$, integrate all 6 stress box faces, yield opposing 3D blade/ground forces, evaluate the 3D enclosure reaction independently, compute the fringing ratio directly, and demonstrate 3D mesh convergence?
6. **Programmatic Controls & Adversarial Gate (F6, M1):** Are `+V` vs `-V`, `V=0`, symmetric capacitor, $180^\circ$ spatial inversion BVP, and asymmetric wall proximity controls genuinely solved, and does `verify_control_assertions()` reject corrupted false-positive control states?
7. **Honest Manifest & Visualization (M2):** Do `exodus_patent_comparison.png`, `exodus_patent_manifest.json`, `README.md`, and `docs/ROADMAP.md` avoid premature completion checkmarks or overclaims?

**ANNOUNCEMENT: READY FOR CHATGPT INDEPENDENT RE-REVIEW — P2 R2**
