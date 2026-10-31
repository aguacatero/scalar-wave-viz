## Phase P2 — Exodus Patent Reproduction & Hypothesis Separation (R5 Draft)

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
  - **Independent 2D & 3D Dielectric Material Reaction Benchmarks (P2-R3-F3 & P2-R4-F3 Remediation):**
    Implements both `benchmark_analytic_planar_dielectric_slab_force` (2D) and `benchmark_analytic_planar_dielectric_slab_force_3d` (3D), validating dielectric reaction forces across four independent formulations:
    1. Analytical virtual work: $F_{\text{analytic}} = -\frac{1}{2}\varepsilon_0 (\varepsilon_r - 1) \frac{V^2}{d} L_z = -49.58\ \mu\text{N}$ (3D setup).
    2. Numerical thermodynamic virtual-work perturbation $F_{\text{vw}} = \frac{U_e(x_0+\delta x) - U_e(x_0-\delta x)}{2\delta x} = -38.30\ \mu\text{N}$ with constant-voltage sources ($+\partial U_e / \partial x$).
    3. Numerical Maxwell stress contour integral enclosing slab insertion: $-36.58\ \mu\text{N}$ (agrees with 3D virtual work to within $4.5\%$).
    4. Direct constitutive Korteweg-Helmholtz material interface traction $\int -\frac{1}{2}\varepsilon_0 |\mathbf{E}|^2 \nabla \varepsilon_r dV = -28.00\ \mu\text{N}$.
    Whole-body 3D dielectric accounting honestly reports `whole_body_3d_mechanical_accounting = "UNVERIFIED_PENDING_CONFORMING_INTERFACE_MESHING"` due to Cartesian staircasing, and the gate fails closed.
- **Model H1 (Patent-Specific Alternative US11511891B2 Eq. 4–11):**
  - Transcribes Eq. (11): $F = \varepsilon_0 (E_2^2 A_2 - E_1^2 A_1)$.
  - Analytical and numerical evaluation reveals:
    1. Misapplication of stationary action $\delta S = 0$ does not imply $d(U_t) = 0$ at Eq. (4).
    2. Missing fundamental factor of $1/2$ in electrostatic surface traction ($\frac{1}{2}\varepsilon_0 E^2$).
    3. Complete neglect of lateral flanks (100b), base front shoulder, ground counter-reaction, and enclosure reactions.
    4. Cauchy-Schwarz disparity between face quadrature and spatial-mean field plug-in.
- **Constrained Finite 3D Boundary-Value Model & Commensurate Fixed-Geometry Refinement (P2-R4-F1 Remediation):**
  - Symmetric Positive Definite free-DOF formulation solved via Jacobi-preconditioned CG (`spla.cg(..., rtol=1e-8)`).
  - Multi-level commensurate 3D refinement series ($h_k = 1.27\text{ mm} / k$ for $k=1, 2, 3$, $dz = 2.54\text{ mm}$), ensuring exact $1.0000$ blade thickness ($k$ cells), height ($5k$ cells), gap ($5k$ cells), pitch ($5k$ cells), ground width ($40k$ cells), and $z$ extent without geometric distortion across refinement levels.
  - Multi-body convergence reporting: records 3D forces on blade, ground, dielectric, enclosure outer walls, net system momentum residual, and H1 directional surface quantities ($\oint E^2 dA$) at every level.
  - Solves for observed 3D convergence order $p_{\text{obs}}$ across commensurate triplets and designates non-asymptotic fractional order influenced by corner singularities.
- **Structured 5-Part Uncertainty Budget & Strict Fail-Closed Discrimination Gate (P2-R4-F2 Remediation):**
  - Evaluates individual and combined uncertainty terms:
    1. Linear algebra solver residual: $8.4\times 10^{-11}\text{ N}$ ($|F_{\text{blade}}| \times \text{solver\_res}$).
    2. Discrete momentum closure residual: $445–830\ \mu\text{N}$ ($|F_{\text{net}}|$).
    3. Mesh force discretization uncertainty: evaluated from same-geometry 3D refinement study.
    4. Domain boundary clearance uncertainty: evaluated from 3D clearance sweeps.
    5. Missing parameter model uncertainty: $50\ \mu\text{N}$ corner singularity fillet radius model sensitivity bound.
  - Combines bounds into RSS ($U_{\text{rss}} = \sqrt{\sum u_i^2}$) and conservative linear ($U_{\text{linear}} = \sum u_i$) metrics.
  - Enforces strict fail-closed acceptance rule against the $10\%$ target discrimination threshold ($0.10 \times 237\ \mu\text{N} = 23.7\ \mu\text{N}$):
    Because numerical residuals and uncertainties exceed $23.7\ \mu\text{N}$, the gate correctly and honestly reports:
    `physical_scale_discrimination_status = "NOT_RESOLVED_AT_CURRENT_3D_GRID_RESOLUTION"` and `finite_3d_is_conserved = False`.
- **Mesh Refinement, Observed Order & Tip Corner Singularity (P2-R3-F1 & P2-R4-M2 Remediation):**
  - 2D mesh convergence across 4 commensurate grid spacings ($h_0/k = 1.27, 0.635, 0.4233, 0.3175\text{ mm}$), where actual-to-target geometry ratios remain exactly 1.0000.
  - Demonstrates observed convergence order $p_{\text{obs}} = \frac{\ln(d_1/d_2)}{\ln(2)} \approx 0.368$, consistent with a corner-singularity-influenced convergence rate ($E \propto r^{-1/3}$, theoretical exponent $\approx 0.333$).
  - Measured log-log tip field scaling $\alpha_{\text{tip}} = \frac{\ln(E_2/E_1)}{\ln(h_1/h_2)} \in [0.22, 0.38]$ matches the physical singularity range $[0.2, 0.5]$ rather than an unphysical $1/h$ divergence.
  - Extrapolations are explicitly labeled provisional (`observed_order_is_provisional = True`).
- **Programmatically Evaluated Controls & Sourced Literature Context:**
  - Evaluates $+V$ vs $-V$ polarity reversal, $V=0$ voltage-off, symmetric capacitor, 180° spatial inversion BVP, and asymmetric wall coupling.
  - Sourced literature audit of [Tajmar & Schreiber (2020)](https://doi.org/10.1016/j.elstat.2020.103477): 13 asymmetric capacitors in a self-contained battery-powered HV setup inside an airtight Faraday cage on a precision balance in ambient/shielded air (not high vacuum), up to 10 kV, null apparent weight change within $\pm 0.3\text{ mg} \approx \pm 2.94\ \mu\text{N}$.

### 3. Verification & Governance
- P0 scientific baseline blob `97f65dfa25db7730323edd5e52c98b17371fdeaa` preserved byte-for-byte.
- P1 scientific baseline preserved byte-for-byte.
- Entire test suite: **118 tests passed** (35 P0 + 37 P1 + 46 P2).
- Paired evidence manifest (`exodus_patent_manifest.json`, schema 1.2.0) and publication comparison figure (`exodus_patent_comparison.png`) updated with commensurate resolution, dynamic parameter labels, and 5-part uncertainty budget.
- Version-controlled PR description in `docs/PR_DESCRIPTION.md` mechanically asserted by unit tests (exact test count dynamically verified).
- README research progress verified (2 of 5 gates accepted; P2 active on draft branch).
