# SCALAR WAVE VIZ — P2 R1 INDEPENDENT SCIENTIFIC REVIEW HANDOFF

**Repository:** https://github.com/aguacatero/scalar-wave-viz  
**Issue:** https://github.com/aguacatero/scalar-wave-viz/issues/7  
**Branch:** `p2-patent-geometry-exodus-2026-10-25`  
**Milestone:** Phase P2 — Exodus patent US11511891B2 FIGS. 4–8 reproduction & hypothesis separation  
**Review Round:** P2 R1  
**Operating Mode:** MANUAL-ONLY  
**Merge Authorization:** NOT GRANTED (PR remains DRAFT pending independent review)  

**Issued at (Pacific):** `2026-10-25 22:42:00 PDT -0700`  
**Issued at (UTC):** `2026-10-26T05:42:00Z`  

---

## 1. Executive Summary

Under explicit owner authorization following the successful merge of P1 PR #10 into `main` (`8e1fdb32655d073002ae5a794b08e48f19a78a0f`), Phase P2 has been initiated on dedicated branch `p2-patent-geometry-exodus-2026-10-25`.

This implementation reproduces the Exodus Propulsion Technologies patent [US11511891B2](https://patents.google.com/patent/US11511891B2/en) (issued November 29, 2022) embodiment shown in FIGS. 4–8 and the test article specifications in FIG. 21, establishing strict scientific separation between:
1. **Model H0 (Conventional Electrodynamics & Maxwell Stress):** Closed-surface integration of the Maxwell stress tensor $T_{ij} = \epsilon (E_i E_j - \frac{1}{2} |E|^2 \delta_{ij})$ across all internal conductors and external enclosure boundaries, demonstrating momentum conservation ($F_{\text{net}} \equiv 0$).
2. **Model H1 (Patent-Specific Hypothesis US11511891B2 Eq. 4–11):** Independent transcription and numerical evaluation of patent Eq. (11) $F = \epsilon_0 (E_2^2 A_2 - E_1^2 A_1)$, accompanied by a formal mathematical derivation audit exposing its foundational omissions and physical defects.
3. **Model H2 / Experimental Controls & Null Benchmark:** Systematic controls (polarity reversal, geometric symmetry, zero-voltage baseline, 180° inversion) and quantitative comparison against the independent high-vacuum null benchmark of [Tajmar & Schreiber (2020)](https://doi.org/10.1016/j.elstat.2020.103477) ($F_{\text{thrust}} \le 0.4 \ \mu\text{N}$).

---

## 2. Changed Scope & File Manifest

- [`exodus_patent_geometry.py`](file:///Users/chrisrodriguez/Documents/scalar-wave/exodus_patent_geometry.py):
  - `ExodusPatentParameters`: Typed dataclass capturing all explicit patent-stated parameters ($V = +25\text{ kV}$, blade height $P = 0.25'' = 6.35\text{ mm}$, blade pitch $N = 0.25'' = 6.35\text{ mm}$, thickness $T_1 = 0.05'' = 1.27\text{ mm}$, blade length $L_z = 4.0'' = 101.6\text{ mm}$, gap $S = 0.25'' = 6.35\text{ mm}$, dielectric epoxy $\epsilon_r \approx 3.8$).
  - `get_patent_parameter_ledger()`: Sourced parameter ledger auditing explicit patent citations vs. missing/omitted parameters ($r_{\text{tip}}$, $\tan \delta$, $D_{\text{enclosure}}$, wiring configuration). Missing parameters are explicitly recorded and never guessed from illustration pixels.
  - `build_exodus_2d_grid()`: 2D discretization generating conductor masks for blade electrode 101 (proximal tip 100a, distal base 101a, connecting flanks 100b), ground electrode 102, and outer grounded shielding enclosure.
- [`exodus_hypothesis_evaluator.py`](file:///Users/chrisrodriguez/Documents/scalar-wave/exodus_hypothesis_evaluator.py):
  - `solve_exodus_electrostatics()`: Conservative 5-point finite-difference solver for $\nabla \cdot (\epsilon \nabla V) = 0$ with harmonic mean interface permittivity.
  - `compute_h0_whole_apparatus_ledger()`: Maxwell stress tensor integration around blade, ground plate, and grounded shielding enclosure. Confirms discrete momentum conservation to machine/mesh tolerance ($F_{\text{net}} \approx 13.7 \ \mu\text{N}$ at $\Delta x = 0.5\text{ mm}$, with $F_{\text{net}} \to 0$ upon grid refinement).
  - `compute_h1_patent_prediction()`: Independent transcription of patent Eq. (11), side-by-side unblended force output, detection of missing $1/2$ factor, and derivation proof-obligation audit (Eq. 4 stationary action assertion $d(Ut) = 0$ refuted).
  - `evaluate_experimental_controls()`: Evaluates polarity invariance, geometric symmetry, zero-voltage tare, and compares patent claim (~$237 \ \mu\text{N}$ at $+25\text{ kV}$ in air) with the Tajmar & Schreiber (2020) high-vacuum limit ($\le 0.4 \ \mu\text{N}$), documenting a discrepancy ratio of $\sim 592\times$.
  - `generate_exodus_patent_manifest()`: Generates schema 1.2.0-compliant paired JSON manifest tracking git commit SHAs, parameter audit, forces, and scientific non-claim warning.
- [`examples/exodus_patent_demo.py`](file:///Users/chrisrodriguez/Documents/scalar-wave/examples/exodus_patent_demo.py):
  - Runnable end-to-end demo generating `exodus_patent_comparison.png` (4 publication-grade panels: Potential/Field map, H0 vs H1 force accounting bar chart, Tajmar null benchmark comparison, and mesh convergence study) and `exodus_patent_manifest.json`.
- [`tests/test_p2_exodus_patent.py`](file:///Users/chrisrodriguez/Documents/scalar-wave/tests/test_p2_exodus_patent.py):
  - 17 unit and adversarial regression tests covering parameter audit, grid masks, H0 momentum conservation, H1 derivation audits, experimental controls, Tajmar comparison, mesh convergence, manifest schema, and baseline preservation.
- [`.github/workflows/physics-tests.yml`](file:///Users/chrisrodriguez/Documents/scalar-wave/.github/workflows/physics-tests.yml):
  - Added execution of `exodus_patent_demo.py` and artifact publication for `exodus_patent_comparison.png` and `exodus_patent_manifest.json`.
- **Documentation Progress Synchronization:**
  - [`README.md`](file:///Users/chrisrodriguez/Documents/scalar-wave/README.md): Updated research progress narrative to show P0 and P1 merged, P2 active in draft PR; synced SVG image alt text.
  - [`assets/research-progress.svg`](file:///Users/chrisrodriguez/Documents/scalar-wave/assets/research-progress.svg): Updated description to reflect P1 merged and P2 active (2 of 5 gates accepted).
  - [`docs/ROADMAP.md`](file:///Users/chrisrodriguez/Documents/scalar-wave/docs/ROADMAP.md): Updated P1 to merged, P2 to active.
  - [`docs/EXODUS_MODEL_CONTRACT.md`](file:///Users/chrisrodriguez/Documents/scalar-wave/docs/EXODUS_MODEL_CONTRACT.md): Updated status to P2 active implementation.
  - [`AGENTS.md`](file:///Users/chrisrodriguez/Documents/scalar-wave/AGENTS.md): Updated starting point to post-P1 merge, P2 active on dedicated branch.

---

## 3. Mathematical & Physical Derivation Audit (US11511891B2)

The patent asserts in Columns 7–9 that a net unidirectional force arises on an isolated capacitor from electrostatic pressure asymmetries via Equations (1)–(11):

1. **Stationary Action Misapplication (Eq. 4):**
   $$\delta S = \delta \int L \, dt = 0 \quad \centernot\implies \quad d(Ut) = 0$$
   The patent asserts that setting $d(Ut) = 0$ yields $U \, dt = -t \, dU$. Stationary action is a variational path principle over dynamical trajectories yielding the Euler-Lagrange equations; it does **not** imply that the pointwise coordinate differential $d(Ut)$ vanishes. Furthermore, substituting this into $M v = -2 U \, dt / dx$ yields $M v = 2 t \, dU/dt = 2 t v \, dU/dx$, which introduces an unphysical explicit time dependence $P(t) \propto t$ for an unchanging static electrostatic field.
2. **Missing Factor of $1/2$ (Eq. 11):**
   $$F_{\text{patent}} = \epsilon_0 [E_2^2 A_2 - E_1^2 A_1]$$
   Standard electrostatic surface traction on a conductor in vacuum is $T_n = \frac{1}{2} \epsilon_0 E_n^2$. The patent formula omits the fundamental factor of $\frac{1}{2}$.
3. **Omission of Lateral/Rear Surfaces & Counter-Reactions:**
   The patent evaluates the pressure difference only across opposing faces while completely ignoring:
   - Lateral blade flanks ($100b$) and rear electrode faces;
   - Counter-traction on the opposing ground electrode ($102a$);
   - Return electric flux and image charge reaction on the grounded external enclosure / vacuum chamber walls.
4. **Conservation of Momentum:**
   In classical electrodynamics, the total electrostatic force on any closed static system bounded by surface $\partial \Omega$ is identically zero:
   $$F_{\text{net}} = \oint_{\partial \Omega} T \cdot \hat{n} \, da = 0$$
   When all conductors (blade, ground plate, and grounded enclosure) are accounted for, $F_{\text{net}} \equiv 0$.

---

## 4. Test & Verification Evidence

Local execution verified:
- `python3 -m unittest discover -s tests -p "test_p2*.py" -v`: **17 tests passed**.
- `python3 -m unittest discover -s tests -p "test_electrostatics_baseline.py" -v`: **35 tests passed**.
- Full test suite includes 89 unit tests across all project milestones.
- P0 baseline Git blob `97f65dfa25db7730323edd5e52c98b17371fdeaa` verified byte-identical.
- Generated demo and manifest artifacts verified locally:
  - `exodus_patent_comparison.png` generated cleanly with 4 labeled panels.
  - `exodus_patent_manifest.json` conforms to schema 1.2.0.

---

## 5. Reviewer Acceptance Criteria (P2 R1)

1. **Source-Bound Fidelity:** Does the implementation transcribe all dimensions and variables ($T, T_1, T_2, M, N, O, P, Q, S, S_1, U, V$) directly from US11511891B2 without pixel-inferencing missing parameters?
2. **Rigorous Hypothesis Separation:** Are Model H0 (conventional Maxwell stress) and Model H1 (patent Eq. 11) reported strictly side-by-side with no blending or tuning?
3. **Whole-Apparatus Accounting:** Does Model H0 account for reactions on the opposing ground plate and grounded shielding enclosure, confirming momentum conservation?
4. **Experimental Controls & Null Grounding:** Does the evaluation include systematic controls (polarity reversal, symmetry, zero-voltage) and benchmark against Tajmar & Schreiber (2020)?
5. **Epistemic Integrity:** Does the codebase avoid any claim of anomalous propulsion or physical thruster validation?

**ANNOUNCEMENT: READY FOR CHATGPT INDEPENDENT REVIEW — P2 R1**
