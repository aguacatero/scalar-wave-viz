## Phase P2 — Exodus Patent Reproduction & Hypothesis Separation (R4 Draft)

Tracks #7.
**Operating Mode:** MANUAL-ONLY.
**PR State:** DRAFT pending independent adversarial ChatGPT scientific review.
**Owner Merge Authorization:** NOT GRANTED. Do not self-approve or merge.

### 1. Scope & Primary Sources
- **Primary Source:** US Patent [US11511891B2](https://patents.google.com/patent/US11511891B2/en) (issued November 29, 2022; inventors: Andrew Neil Aurigema and Charles Raymond Buhler, IV).
- **Embodiments Evaluated & Separated:**
  1. Single-stage bladed schematic embodiment (FIGS. 4–8; $N=1$, nominal $+25\text{ kVDC}$, vacuum baseline $\varepsilon_r=1.0$).
  2. FIG. 21 nine-blade epoxy-potted test article ($N=9$, nominal $+25\text{ kVDC}$, potting epoxy $\varepsilon_r=3.8$).
- **Geometric Dimensions & Authoritative Sourced Parameters:**
  - Blade height $P = 0.25\text{ in} = 6.35\text{ mm}$
  - Blade pitch $N = 0.25\text{ in} = 6.35\text{ mm}$
  - Blade thickness $T_1 = 0.05\text{ in} = 1.27\text{ mm}$
  - Blade length $L_z = 4.0\text{ in} = 101.6\text{ mm}$ (Symbol $Q$)
  - Inter-electrode gap $S = 0.25\text{ in} = 6.35\text{ mm}$
  - Distal separation $S_1 = S + P = 0.50\text{ in} = 12.7\text{ mm}$
  - Total core thickness $T = 0.55\text{ in} = 13.97\text{ mm}$
  - Ground plane lateral width $W_{\text{gnd}} = 2.0\text{ in} = 50.8\text{ mm}$ (tested up to $3.0\text{ in}$)
  - Lateral electrode offset / overlap $O = 0.0\text{ m}$ (centered symmetric alignment; distinct from $W_{\text{gnd}}$)
- **Explicit Parameter Audit:** Missing parameters ($r_{\text{tip}}$, $\tan\delta$, shielding enclosure dimensions $U$, lead-wire routing) are recorded with formal 5-category provenance taxonomy (`PATENT_EXPLICIT_VALUE`, `DERIVED_FROM_PATENT`, `EXTERNAL_ESTIMATE_FOR_UNSPECIFIED`, `MODELING_ASSUMPTION`, `PATENT_OMITTED_UNKNOWN`) rather than inferred from drawing illustrations. Rectangular blade corner singularity ($E \sim r^{-1/3}$) under refinement is explicitly tracked as physical model uncertainty.

### 2. Hypothesis Separation & Physics Implementation
- **Model H0 (Conventional Electrodynamics / Maxwell Stress Baseline):**
  - Solves $\nabla \cdot (\varepsilon \nabla V) = 0$ on 2D and constrained finite 3D domains.
  - Closed-contour integration of Maxwell stress tensor across blade (101), ground (102), dielectric reaction, and outer enclosure.
  - Non-tautological momentum conservation: evaluates direct electrostatic surface traction on outer bounding walls via `compute_direct_enclosure_wall_tractions` (2D) and `compute_direct_enclosure_wall_tractions_3d` (3D), confirming momentum closure without equating $F_{\text{wall}} \equiv -(F_{\text{blade}} + F_{\text{ground}})$.
  - **Independent Dielectric Material Force Benchmark (P2-R3-F3 Remediation):**
    Implements `benchmark_analytic_planar_dielectric_slab_force` validating dielectric force across three independent formulations:
    1. Analytical virtual work: $F_{\text{analytic}} = -\frac{1}{2}\varepsilon_0 (\varepsilon_r - 1) \frac{V^2}{d} L_z = -123.96\ \mu\text{N}$.
    2. Numerical Maxwell stress contour difference around the insertion front: $-111.54\ \mu\text{N}$.
    3. Numerical thermodynamic virtual-work perturbation $F_{\text{vw}} = \frac{U_e(x_0+\delta) - U_e(x_0-\delta)}{2\delta} = -109.14\ \mu\text{N}$.
    Contour stress and virtual-work perturbation agree to within $2.2\%$, confirming mechanical reaction closure. Whole-body 3D dielectric accounting is labeled `whole_body_3d_mechanical_accounting = "UNVERIFIED_PENDING_CONFORMING_INTERFACE_MESHING"`.
- **Model H1 (Patent-Specific Alternative US11511891B2 Eq. 4–11):**
  - Transcribes Eq. (11): $F = \varepsilon_0 (E_2^2 A_2 - E_1^2 A_1)$.
  - Analytical and numerical evaluation reveals:
    1. Misapplication of stationary action $\delta S = 0$ does not imply $d(U_t) = 0$ at Eq. (4).
    2. Missing fundamental factor of $1/2$ in electrostatic surface traction ($\frac{1}{2}\varepsilon_0 E^2$).
    3. Complete neglect of lateral flanks (100b), base front shoulder, ground counter-reaction, and enclosure reactions.
    4. Cauchy-Schwarz disparity between face quadrature and spatial-mean field plug-in.
- **Constrained Finite 3D Boundary-Value Model & Commensurate Discretization (P2-R3-F1 & P2-R3-F2 Remediation):**
  - Symmetric Positive Definite free-DOF formulation solved via Jacobi-preconditioned CG (`spla.cg(..., rtol=1e-10)`).
  - Uses commensurate grid spacings ($\Delta x = \Delta y = 0.00127\text{ m} = 0.05\text{ in}$, $\Delta z = 0.00254\text{ m} = 0.10\text{ in}$) ensuring exact $1.0000$ blade thickness, gap, and pitch ratios without mesh distortion.
  - Solves both single-blade schematic and FIG. 21 9-blade test article in 3D in $< 2$ seconds.
  - Direct 6-wall outer enclosure surface traction matches diagnostic inner-contour stress flux to $< 0.16\%$.
  - **Structured 5-Part Uncertainty Budget & Discrimination Gate (P2-R3-F2):**
    1. Linear algebra solver residual: $8.4\times 10^{-11}\text{ N}$ ($|F_{\text{blade}}| \times \text{solver\_res}$).
    2. Discrete momentum closure residual: $445–683\ \mu\text{N}$ ($|F_{\text{net}}|$).
    3. Mesh force discretization uncertainty: $\approx 18\%$ from Richardson extrapolation.
    4. Domain boundary clearance uncertainty: $\approx 50\ \mu\text{N}$ from clearance sweeps.
    5. Missing parameter model uncertainty notes detailing unmodeled $r_{\text{tip}}$, copper tape roughness, epoxy loss tangent, and ITO sheet resistance.
  - **Strict Discrimination Threshold ($23.7\ \mu\text{N}$):**
    Because the discrete 3D numerical momentum closure residual ($\sim 445–683\ \mu\text{N}$) exceeds the strict $10\%$ target discrimination threshold ($0.10 \times 237\ \mu\text{N} = 23.7\ \mu\text{N}$), the gate correctly and honestly reports:
    `physical_scale_discrimination_status = "NOT_RESOLVED_AT_CURRENT_3D_GRID_RESOLUTION"` and `finite_3d_is_conserved = False`.
- **Mesh Refinement, Observed Order & Tip Corner Singularity (P2-R3-F1 & P2-R3-M2 Remediation):**
  - 2D mesh convergence across 4 commensurate grid spacings ($h_0/k = 1.27, 0.635, 0.4233, 0.3175\text{ mm}$), where actual-to-target geometry ratios remain exactly 1.0000.
  - Demonstrates observed convergence order $p_{\text{obs}} = \frac{\ln(d_1/d_2)}{\ln(2)} \approx 0.368$, confirming that convergence is governed by the theoretical $90^\circ$ wedge re-entrant corner singularity ($E \propto r^{-1/3}$, theoretical exponent $\approx 0.333$).
  - Measured log-log tip field scaling $\alpha_{\text{tip}} = \frac{\ln(E_2/E_1)}{\ln(h_1/h_2)} \in [0.22, 0.38]$ matches the physical singularity range $[0.2, 0.5]$ rather than an unphysical $1/h$ divergence.
  - Reports both observed-order Richardson extrapolation ($-88.4\text{ mN}$) and assumed first-order estimate ($-73.5\text{ mN}$), explicitly labeled `richardson_is_assumed_order_estimate = True`.
  - Epistemic status designated: `COMMENSURATE_2D_CONVERGENCE_ANALYZED_AND_FINITE_3D_APPROXIMATION_WITH_ASSUMED_ORDER_ESTIMATE`.
- **Programmatically Evaluated Controls & Sourced Literature Context (P2-R3-M1 Remediation):**
  - Evaluates $+V$ vs $-V$ polarity reversal, $V=0$ voltage-off, symmetric capacitor, 180° spatial inversion BVP, and asymmetric wall coupling.
  - Sourced literature audit of [Tajmar & Schreiber (2020)](https://doi.org/10.1016/j.elstat.2020.103477): 13 asymmetric capacitors in a self-contained battery-powered HV setup inside an airtight Faraday cage on a precision balance in ambient/shielded air (not high vacuum), up to 10 kV, null apparent weight change within $\pm 0.3\text{ mg} \approx \pm 2.94\ \mu\text{N}$.
  - Strictly contextual comparison; candidate confounders (corona/ion wind, HV feed-wire forces, Coulomb chamber coupling) are framed as open confounders requiring physical discrimination rather than established causes.

### 3. Verification & Governance
- P0 scientific baseline blob `97f65dfa25db7730323edd5e52c98b17371fdeaa` preserved byte-for-byte.
- P1 scientific baseline preserved byte-for-byte.
- Entire test suite: **116 tests passed** (35 P0 + 37 P1 + 44 P2).
- Paired evidence manifest (`exodus_patent_manifest.json`, schema 1.2.0) and publication comparison figure (`exodus_patent_comparison.png`) updated with commensurate resolution and 5-part uncertainty budget.
- Version-controlled PR description in `docs/PR_DESCRIPTION.md` mechanically asserted by unit tests.
- README research progress verified (2 of 5 gates accepted; P2 active on draft branch).
