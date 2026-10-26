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

This handoff remediates all findings from ChatGPT's independent scientific review of Phase P2 R1 ([issuecomment-6415952244](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6415952244)), which concluded `CHANGES REQUIRED — P2 R1 NOT ACCEPTED` across 6 High and 2 Medium findings.

Phase P2 reproduces the Exodus Propulsion Technologies patent [US11511891B2](https://patents.google.com/patent/US11511891B2/en) (issued November 29, 2022) embodiment depicted in FIGS. 4–8 and the multi-blade test article in FIG. 21, establishing rigorous physical and numerical separation between:
1. **Model H0 (Conventional Electrodynamics & Maxwell Stress Baseline):** Conservative finite-difference solution of $\nabla \cdot (\epsilon \nabla V) = 0$, direct electrostatic surface wall tractions $T_n = \frac{1}{2} \epsilon_0 E_n^2$ on the outer grounded enclosure, closed-contour Maxwell stress integration, and a constrained 3D boundary-value model capturing finite blade length ($L_z = 101.6\text{ mm}$) and 3D end fringing. Momentum is rigorously conserved ($F_{\text{net}} \equiv 0$).
2. **Model H1 (Patent-Specific Hypothesis US11511891B2 Eq. 4–11):** Strict material-side boundary face quadrature of patent Eq. (11) $F = \epsilon_0 (E_2^2 A_2 - E_1^2 A_1)$ evaluated strictly outside conductors, utilizing corresponding face widths (proximal tip $w_2 \approx T_1 = 1.27\text{ mm}$; distal base $w_1 = 30\text{ mm}$), side-by-side unblended force reporting, missing $\frac{1}{2}$ factor detection, and a formal proof-obligation refutation of the Eq. (4) stationary action claim.
3. **Model H2 / Evaluated Controls & Contextual Literature Audit:** Programmatically executed controls (polarity reversal $V \to -V$, voltage-off $V = 0$, and symmetric electrode control with anti-phase excitation yielding zero net force), explicit `NOT_EVALUATED_NUMERICAL_SIMULATION_ONLY` status for unperformed physical laboratory tests, and an audited contextual comparison with the independent high-vacuum null balance measurements of [Tajmar & Schreiber (2020)](https://doi.org/10.1016/j.elstat.2020.103477).

---

## 2. P2 R1 Review Finding Remediation Matrix

| Finding ID | Severity | Canonical Finding Description | Implemented Remediation & Physical Resolution |
| :--- | :--- | :--- | :--- |
| **P2-R1-F1** | **HIGH** | Literature benchmark mischaracterizes Tajmar & Schreiber (2020) and fabricates false ratio | Audited primary paper: Tajmar & Schreiber (2020) tested symmetric/asymmetric capacitors up to 10 kV (not 40 kV) on a double-shielded torsion balance with resolution/accuracy $\pm 0.3\text{ mg} \approx \pm 2.94\ \mu\text{N}$ (not $\le 0.4\ \mu\text{N}$). Removed the hardcoded $592.5\times$ ratio; reframed Panel C and manifest as a contextual literature comparison distinguishing high-vacuum balance limits from unshielded atmospheric/air pendulum tests. |
| **P2-R1-F2** | **HIGH** | Material-side boundary fields, areas, and face sampling in H1 are incorrect | Replaced bulk mask interior sampling with explicit `ConductorBoundaryFace` quadrature sampled strictly on the dielectric/vacuum side outside conductors. Fixed face areas: proximal tip face uses blade thickness $T_1 = 1.27\text{ mm}$ (not ground plane width $50.8\text{ mm}$); distal base face uses backing plate width ($30\text{ mm}$). Accommodates discrete grid rasterization tolerance ($3\text{ cells} \times 0.6\text{ mm} = 1.8\text{ mm}$). |
| **P2-R1-F3** | **HIGH** | Discretization, missing parameters, and parameter ledger inconsistencies | Sourced parameter ledger audited for all 12 patent symbols from Col. 11 and FIGS. 2–8 ($T, T_1, T_2, M, N, O, P, Q, S, S_1, U, V$) with typed `ParameterStatus` (`PATENT_EXPLICIT_VALUE`, `PATENT_UNSPECIFIED_ESTIMATE`, `MODELING_ASSUMPTION`, `PATENT_OMITTED_UNKNOWN`). `ground_plane_thickness_m` directly controls geometry rather than hardcoded 1-cell defaults. |
| **P2-R1-F4** | **HIGH** | Whole-apparatus force accounting, enclosure boundaries, and clearance are unstable | Added direct wall electrostatic traction integration `compute_direct_enclosure_wall_tractions()`. Verified direct wall traction matches inner contour reaction to $< 0.01\%$. Added contour offset invariance regression confirming stress flux independence. Resolved signed force conventions in both numerical ledger and visualization. |
| **P2-R1-F5** | **HIGH** | 2D vs. 3D force dimensions and fringing conflation | Implemented `solve_exodus_electrostatics_3d()` in `exodus_hypothesis_evaluator.py`, solving 3D finite-difference electrostatics with finite blade length $L_z = 101.6\text{ mm}$ and 3D enclosure walls. Strictly distinguishes 2D force per length ($\text{N/m}$), extruded 2D force ($\text{N}$), and true 3D force ($\text{N}$). |
| **P2-R1-F6** | **HIGH** | Controls are hard-coded assertions rather than programmatic checks | Replaced static booleans with real programmatic execution in `evaluate_experimental_controls()`: polarity reversal ($V \to -V$, verifying $|F(+V)| = |F(-V)|$ to machine precision), voltage-off ($V = 0$, verifying $F \equiv 0$), and symmetric electrode control (verifying $F_{\text{net}} \equiv 0$). Unperformed laboratory controls tagged `NOT_EVALUATED_NUMERICAL_SIMULATION_ONLY`. |
| **P2-R1-M1** | **MED** | Regression suite lacks falsifying tests | Expanded test suite from 17 to 22 tests. Added adversarial regressions for boundary face coordinates, face width consistency, contour offset invariance, direct wall traction vs. contour reaction, symmetric electrode control, and literature citation accuracy. |
| **P2-R1-M2** | **MED** | Evidence figure and manifest overstate achieved verification | Manifest replaces `anomalous_thrust_detected: false` with explicit epistemic status fields distinguishing theoretical, computational, and experimental evidence. Comparison figure reframes Panel C as contextual literature comparison; Panel B clearly labels "H0: Enclosure Reaction"; Panel D presents mesh convergence $h \to 0$. |

---

## 3. Changed Scope & File Inventory

- [`exodus_patent_geometry.py`](file:///Users/chrisrodriguez/Documents/scalar-wave/exodus_patent_geometry.py):
  - Added `ParameterStatus` literal type.
  - Sourced parameter ledger auditing all 12 patent symbols ($T, T_1, T_2, M, N, O, P, Q, S, S_1, U, V$).
  - Added `ConductorBoundaryFace` dataclass and material-side boundary face generator outside conductors.
  - Implemented `build_symmetric_control_grid()` with anti-phase $\pm V/2$ excitation and mirror-symmetric electrode placement.
- [`exodus_hypothesis_evaluator.py`](file:///Users/chrisrodriguez/Documents/scalar-wave/exodus_hypothesis_evaluator.py):
  - Implemented `compute_direct_enclosure_wall_tractions()` integrating electrostatic surface tractions $T_n = \frac{1}{2} \epsilon_0 E_n^2$ directly at enclosure walls.
  - Implemented `solve_exodus_electrostatics_3d()` computing true 3D Maxwell stress in Newtons (N) capturing finite blade length $L_z$ and 3D end fringing.
  - Refactored `compute_h1_patent_prediction()` to evaluate strict material-side boundary face quadrature with proper corresponding face areas ($w_{\text{proximal}} \approx 1.27\text{ mm}$, $w_{\text{distal}} = 30\text{ mm}$).
  - Refactored `evaluate_experimental_controls()` to execute real programmatic solves for polarity reversal, voltage-off, and symmetric electrode controls.
  - Updated manifest generator with honest epistemic status fields and schema 1.2.0 conformance.
- [`examples/exodus_patent_demo.py`](file:///Users/chrisrodriguez/Documents/scalar-wave/examples/exodus_patent_demo.py):
  - Reframed Panel C as contextual literature and model comparison (Tajmar & Schreiber 2020 vs. Exodus patent claim).
  - Clarified Panel B force accounting with "H0: Enclosure Reaction" demonstrating zero net force.
  - Panel D illustrates mesh refinement convergence $h \to 0$.
- [`tests/test_p2_exodus_patent.py`](file:///Users/chrisrodriguez/Documents/scalar-wave/tests/test_p2_exodus_patent.py):
  - Expanded from 17 to 22 tests with targeted regressions for all R1 findings.
- **Documentation Progress Synchronization:**
  - [`README.md`](file:///Users/chrisrodriguez/Documents/scalar-wave/README.md): Synchronized research progress narrative to reflect P2 R2 remediation completed; milestone count verified at 2 of 5 accepted.
  - [`docs/ROADMAP.md`](file:///Users/chrisrodriguez/Documents/scalar-wave/docs/ROADMAP.md): Recorded P2 R1 review disposition and R2 remediation status.

---

## 4. Preservation of Prior Accepted Baselines

- **P0 Baseline Preservation:** Git blob `97f65dfa25db7730323edd5e52c98b17371fdeaa` verified byte-identical.
- **P1 Baseline Preservation:** All P1 numerical validation files and tests preserved unchanged.

---

## 5. Reviewer Acceptance Criteria (P2 R2)

1. **Accurate Literature Grounding (F1):** Does the literature comparison accurately reflect Tajmar & Schreiber (2020) without fabricated bounds, inflated test voltages, or arbitrary force ratios?
2. **Strict Boundary Face Quadrature (F2):** Does Model H1 evaluate fields strictly on the dielectric/vacuum side outside conductors using corresponding face widths ($w_2 \approx 1.27\text{ mm}$, $w_1 = 30\text{ mm}$)?
3. **Parameter Discretization Audit (F3):** Are all 12 patent symbols explicitly audited with appropriate `ParameterStatus` tags and physical geometric backing?
4. **Direct Wall Tractions & Momentum Conservation (F4):** Do direct wall tractions match the inner contour reaction, and does the closed static system conserve momentum ($F_{\text{net}} \equiv 0$)?
5. **Dimensional Consistency (F5):** Are 2D forces ($\text{N/m}$) and 3D forces ($\text{N}$) clearly distinguished, with an explicit 3D finite-difference model accounting for finite blade length and end fringing?
6. **Programmatic Controls (F6):** Are polarity reversal, voltage-off, and symmetric electrode controls programmatically solved rather than hardcoded booleans?
7. **Adversarial Regression Suite (M1):** Does the 22-test P2 suite rigorously probe edge cases, face coordinates, contour invariance, and literature citations?
8. **Honest Manifest & Visualization (M2):** Does the evidence package avoid unjustified claims of thrust detection or anomalous propulsion while separating theoretical, computational, and experimental evidence?

**ANNOUNCEMENT: READY FOR CHATGPT INDEPENDENT RE-REVIEW — P2 R2**
