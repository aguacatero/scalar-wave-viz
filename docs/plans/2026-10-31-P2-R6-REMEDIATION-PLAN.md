# SCALAR WAVE VIZ — Phase P2 R6 Remediation Plan

**Repository:** `aguacatero/scalar-wave-viz`  
**Draft PR:** [#11](https://github.com/aguacatero/scalar-wave-viz/pull/11)  
**Branch:** `p2-patent-geometry-exodus-2026-10-25`  
**Governing Review:** [ChatGPT Independent Scientific Review P2 R5 (CHANGES REQUIRED)](docs/reviews/2026-10-31-P2-CHATGPT-R5-REVIEW.md)  
**Governance:** MANUAL-ONLY. Merge authorization NOT GRANTED. No P3 kickoff.

---

## 1. Executive Summary & Objective

In Phase P2 R5, ChatGPT's independent scientific review identified 4 High findings and 1 Medium finding requiring remediation before the scientific baseline can be considered for acceptance:

1. **`P2-R5-F1` (HIGH) — Fixed-geometry *lateral* refinement is not validated full 3D patent-article force convergence:**
   - The $z$-grid was held at $dz = 2.54\text{ mm}$, testing only lateral $x/y$ resolution, not 3D longitudinal/end-fringing convergence.
   - Ground electrode thickness $T_2$ ($0.25\text{ mm}$ modeled) was discretized into 1 cell ($1.27, 0.635, 0.423\text{ mm}$ at $k=1, 2, 3$). This unsourced dimension was not explicitly tracked or swept.
   - Multi-resolution study defaulted to single blade, omitting multi-level convergence on the actual FIG. 21 nine-blade potted article.
   - Tests asserted sign and extrapolate existence rather than tolerance-bounded changes in each body.

2. **`P2-R5-F2` (HIGH) — Uncertainty numbers remain uncalibrated; refinement does not recompute real acceptance predicate:**
   - In initial solve, $u_{\text{mesh}}$ was a 2D/3D fringing proxy, $u_{\text{domain}}$ was an ad hoc formula rather than clearance sweep data, and $u_{\text{model}} = 50\ \mu\text{N}$ was hardcoded without parameter sensitivity sweeps.
   - In `run_3d_mesh_convergence_study`, when $u_{\text{mesh}}$ was updated with $|F_{\text{extrap}} - F_{\text{fine}}|$, the `is_resolved` acceptance predicate was NOT re-evaluated, leaving `physical_scale_discrimination_status` stale.
   - Test `test_adversarial_uncertainty_budget_injection_fails_closed` re-implemented `_evaluate_gate` locally instead of calling the production gate function.

3. **`P2-R5-F3` (HIGH) — A partially agreeing 3D benchmark does not validate the nine-blade dielectric mechanical reaction:**
   - In 3D benchmark, interface traction differed from contour by 23.5%, yet was hard-labeled `INDEPENDENT_3D_DIELECTRIC_BENCHMARK_VALIDATED`.
   - In the actual FIG. 21 solver, `finite_3d_dielectric_virtual_work_x_n` was set to `0.0` (falsely implying zero force rather than uncomputed).
   - Dielectric interface-to-contour agreement was not quantitatively audited on FIG. 21.

4. **`P2-R5-F4` (HIGH) — The new “3D H1” surface prediction is not the patent's Eq. (11) face quantity:**
   - `h1_surface_integral_e2_v2_m` summed $E^2$ over all 6 faces of the solver's blade-enclosing integration box, not the patent's prescribed proximal tip 100a and distal base 101a electrode faces.
   - `h1_surface_force_prediction_n = 0.5 * eps0 * (e2_bx_r - e2_bx_l)` inserted the 1/2 factor, whereas patent Eq. (11) is $\varepsilon_0 (E_2^2 A_2 - E_1^2 A_1)$ with NO 1/2 factor.

5. **`P2-R5-M1` (MED) — Regression does not exercise actual plotting implementation:**
   - `test_demo_plot_dynamic_parameter_label_updating` reconstructed format strings locally instead of calling the plotting code.

---

## 2. Invariants & Guardrails

- **P0 Baseline Preservation:** `electrostatics_baseline.py` blob must remain byte-for-byte identical to `97f65dfa25db7730323edd5e52c98b17371fdeaa`.
- **P1 Baseline Preservation:** All 37 P1 tests must pass without modification.
- **Fail-Closed Governance:** PR #11 remains strictly DRAFT / OPEN / UNMERGED. Never auto-merge; never begin P3 without separate explicit owner authorization.
- **Hypothesis Separation:** Maintain strict separation between conventional electrostatics (H0, momentum conserved) and patent predictions (H1, reactionless surface claims).

---

## 3. Detailed Technical Remediation Plan

### Step 1: True 3D Patent-Face H1 Quadrature (`P2-R5-F4`)
- In `exodus_hypothesis_evaluator.py`:
  - Identify exact material-side boundary cells for proximal tip 100a ($x = x_{\text{blade\_tip}} - 1$, across each blade tip in $y$ and full length in $z$) and distal base rear 101a ($x = x_{\text{blade\_back}} + 1$, across base plate in $y$ and full length in $z$).
  - Calculate:
    - Proximal tip face area: $A_{\text{prox}} = \sum (b_{\text{max}} - b_{\text{min}} + 1) \Delta y \times n_{lz} \Delta z$.
    - Distal base rear face area: $A_{\text{dist}} = (iy_{\text{base\_max}} - iy_{\text{base\_min}} + 1) \Delta y \times n_{lz} \Delta z$.
    - Quadrature of $E^2$ on 100a: $\iint_{100a} E^2 dA = \sum_{tips, k} E^2(k, j, i_{\text{prox}}) \Delta y \Delta z$.
    - Quadrature of $E^2$ on 101a: $\iint_{101a} E^2 dA = \sum_{base, k} E^2(k, j, i_{\text{dist}}) \Delta y \Delta z$.
    - Spatial mean fields $\langle |E| \rangle_{100a}$ and $\langle |E| \rangle_{101a}$.
  - Return:
    1. Literal Patent Eq. (11) force (NO 1/2 factor): $F_{H1, 3D, \text{literal}} = -\varepsilon_0 \left( \iint_{100a} E^2 dA - \iint_{101a} E^2 dA \right)$.
    2. Corrected 1/2 factor Maxwell traction: $F_{H1, 3D, \text{half\_factor}} = -\frac{1}{2}\varepsilon_0 \left( \iint_{100a} E^2 dA - \iint_{101a} E^2 dA \right)$.
    3. Spatial-mean plug-in: $F_{H1, 3D, \text{spatial\_mean}} = -\varepsilon_0 \left( \langle |E| \rangle_{100a}^2 A_{\text{prox}} - \langle |E| \rangle_{101a}^2 A_{\text{dist}} \right)$.
  - Add analytical regressions in `tests/test_p2_exodus_patent.py`:
    - Uniform field regression verifying literal quadrature == spatial mean plug-in on parallel plates.
    - Nonuniform field regression verifying Cauchy-Schwarz inequality ($\iint E^2 dA > \langle |E| \rangle^2 A$).

### Step 2: Centralized Production Discrimination Gate (`P2-R5-F2`)
- In `exodus_hypothesis_evaluator.py`:
  - Implement pure production function `evaluate_physical_scale_discrimination_gate(...)`.
  - Check all 5 budget components against the $23.7\ \mu\text{N}$ threshold (discrete momentum, mesh discretization, domain clearance, model parameter sensitivity, and combined RSS), relative residual $< 0.5\%$, verified model parameters (`missing_parameter_model_is_bounded is True`), and verified whole-body status.
  - Call `evaluate_physical_scale_discrimination_gate` in `solve_exodus_electrostatics_3d`.
  - Re-call `evaluate_physical_scale_discrimination_gate` inside `run_3d_mesh_convergence_study` after computing 3D mesh discretization uncertainty, updating `physical_scale_discrimination_status`, `finite_3d_is_conserved`, and `finite_3d_conservation_status`.
  - In `tests/test_p2_exodus_patent.py`: update `test_adversarial_uncertainty_budget_injection_fails_closed` to directly test the production function.
  - Calibrate $u_{\text{domain}}$ from paired clearance sweep differences, $u_{\text{mesh}}$ from 3D convergence study, and track model bounds.

### Step 3: Full 3D Refinement, Ground Thickness & FIG. 21 Multilevel Study (`P2-R5-F1`)
- In `exodus_hypothesis_evaluator.py`:
  - Allow commensurate refinement of both lateral ($dx, dy$) and longitudinal ($dz$) grids ($h_k = h_0 / k, dz_k = dz_0 / k$).
  - Provide `run_3d_z_mesh_convergence_study` to isolate and bound $z$-discretization error separately.
  - Explicitly track `actual_ground_thickness_m` and `ground_thickness_discretization_ratio` in `Finite3DModelResult`.
  - Enable multi-level study for FIG. 21 nine-blade potted article (`params = ExodusPatentParameters.fig_21_nine_blade_article()`).
  - Report multi-body force tables for all bodies and H1 face quantities with tolerance assertions in tests.

### Step 4: Provisional 3D Dielectric Status & Optional Virtual Work (`P2-R5-F3`)
- In `exodus_hypothesis_evaluator.py`:
  - Rename benchmark status in `benchmark_analytic_planar_dielectric_slab_force_3d` to `"PROVISIONAL_3D_DIELECTRIC_BENCHMARK_APPROXIMATE_AGREEMENT"`.
  - In `Finite3DModelResult`: change `finite_3d_dielectric_virtual_work_x_n: Optional[float] = None` (default `None`).
  - Compute and record `finite_3d_dielectric_interface_to_contour_agreement_rel`.
  - Retain `whole_body_3d_mechanical_accounting = "UNVERIFIED_PENDING_CONFORMING_INTERFACE_MESHING"` and fail closed.

### Step 5: Shared Bar Chart Label Formatter (`P2-R5-M1`)
- In `examples/exodus_patent_demo.py`: extract `format_demo_bar_chart_labels(result: ExodusEvaluationResult) -> List[str]`.
- Use this helper in `examples/exodus_patent_demo.py` panel B.
- In `tests/test_p2_exodus_patent.py`: update `test_demo_plot_dynamic_parameter_label_updating` to directly call `format_demo_bar_chart_labels(result)`.

### Step 6: Regeneration & Verification
- Run full test suite: assert 100% pass across P0, P1, and expanded P2 tests.
- Verify P0 blob hash == `97f65dfa25db7730323edd5e52c98b17371fdeaa`.
- Regenerate visualizer and manifest: `python3 examples/exodus_patent_demo.py`.
- Update `README.md`, `docs/ROADMAP.md`, `docs/PR_DESCRIPTION.md`, and write `docs/handoffs/2026-10-31-P2-CHATGPT-R6-READY.md`.
- Commit, push, verify CI run and artifact ID.
- Generate real-clock timestamps and post readiness comment to PR #11.
