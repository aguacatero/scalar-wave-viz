## Phase P2 — Exodus Patent Reproduction & Hypothesis Separation (R9 Draft)

Tracks #7.
**Operating Mode:** MANUAL-ONLY.
**PR State:** DRAFT pending independent adversarial ChatGPT scientific review.
**Owner Merge Authorization:** NOT GRANTED. Do not self-approve or merge.

### 1. Scope & Primary Sources
- **Primary Source:** US Patent [US11511891B2](https://patents.google.com/patent/US11511891B2/en) (issued November 29, 2022; inventors: Andrew Neil Aurigema and Charles Raymond Buhler, IV).
- **Embodiments Evaluated & Separated:**
  1. Single-stage bladed schematic embodiment (FIGS. 4–8; $N=1$, nominal $+25\text{ kVDC}$, vacuum baseline $\varepsilon_r=1.0$).
  2. FIG. 21 nine-blade epoxy-potted test article: explicitly differentiated between declared full-length test article ($L_z = 4.0\text{ in} = 101.6\text{ mm}$, `FIG21_MODEL_VARIANT_DECLARED_ARTICLE_101MM`) and shortened axial surrogate ($L_z = 1.0\text{ in} = 25.4\text{ mm}$, `FIG21_MODEL_VARIANT_SHORTENED_AXIAL_SURROGATE_25MM`), with transfer scaling validated across $\ge 3$ axial lengths via `compare_fig21_surrogate_to_declared_article` ($L_z \in [25.4, 50.8, 101.6\text{ mm}]$, $R^2 = 1.000000 > 0.99$, max residual $< 25\ \mu\text{N}$, isolating $+7.22\text{ mN}$ end-cap relief as a single-grid empirical fit observation) (P2-R7-F1 & P2-R8-F1).
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
  - Ground electrode thickness tracking (P2-R6-F1 & P2-R7-F1): reconciles copper tape backing estimate $T_2 = 0.25\text{ mm}$ (`EXTERNAL_ESTIMATE_FOR_UNSPECIFIED`) with 1-cell grid discretization ($n_{\text{gnd}} = \max(1, \text{round}(T_2/dx))$). Across coarse grids ($dx > T_2$), 1-cell representation yields thickness $dx$ with physical ratios $5.08, 2.54, 1.693$, thinning monotonically toward physical $0.25\text{ mm}$ without false claims of 1.0000 on coarse grids.
- **Explicit Parameter Audit:** Missing parameters ($r_{\text{tip}}$, $\tan\delta$, shielding enclosure dimensions $U$, lead-wire routing) are recorded with formal 5-category provenance taxonomy (`PATENT_EXPLICIT_VALUE`, `DERIVED_FROM_PATENT`, `EXTERNAL_ESTIMATE_FOR_UNSPECIFIED`, `MODELING_ASSUMPTION`, `PATENT_OMITTED_UNKNOWN`) rather than inferred from drawing illustrations. Rectangular blade corner singularity ($E \sim r^{-1/3}$) under refinement is explicitly tracked as physical model uncertainty.

### 2. Hypothesis Separation & Physics Implementation
- **Model H0 (Conventional Electrodynamics / Maxwell Stress Baseline):**
  - Solves $\nabla \cdot (\varepsilon \nabla V) = 0$ on 2D and constrained finite 3D domains.
  - Closed-contour integration of Maxwell stress tensor across blade (101), ground (102), dielectric reaction, and outer enclosure.
  - Non-tautological momentum conservation: evaluates direct electrostatic surface traction on outer bounding walls via `compute_direct_enclosure_wall_tractions` (2D) and `compute_direct_enclosure_wall_tractions_3d` (3D), confirming momentum closure without equating $F_{\text{wall}} \equiv -(F_{\text{blade}} + F_{\text{ground}})$.
  - **Independent 2D & 3D Dielectric Material Reaction Benchmarks (P2-R3-F3, P2-R4-F3, P2-R5-F3, P2-R7-F3 & P2-R8-F3 Remediation):**
    Implements both `benchmark_analytic_planar_dielectric_slab_force` (2D) and `benchmark_analytic_planar_dielectric_slab_force_3d` (3D), validating dielectric reaction forces across four independent formulations:
    1. Analytical virtual work: $F_{\text{analytic}} = -\frac{1}{2}\varepsilon_0 (\varepsilon_r - 1) \frac{V^2}{d} L_z = -49.58\ \mu\text{N}$ (3D setup).
    2. Numerical thermodynamic virtual-work perturbation $F_{\text{vw}} = \frac{U_e(x_0+\delta x) - U_e(x_0-\delta x)}{2\delta x} = -38.30\ \mu\text{N}$ with constant-voltage sources ($+\partial U_e / \partial x$).
    3. Numerical Maxwell stress contour integral enclosing slab insertion: $-36.58\ \mu\text{N}$ (agrees with 3D virtual work to within $4.5\%$).
    4. Direct constitutive Korteweg-Helmholtz material interface traction $\int -\frac{1}{2}\varepsilon_0 |\mathbf{E}|^2 \nabla \varepsilon_r dV = -28.00\ \mu\text{N}$.
    5. Permittivity sweep across $\varepsilon_r \in [1.5, 2.5, 3.8, 5.0]$ verifying susceptibility monotonicity with $R^2 = 0.9846 > 0.98$; relative intercept $|b|/\max(|F|) \approx 0.19$ is documented as reflection of non-trivial 3D field redistribution (P2-R8-F3).
    6. Component-by-component closure table recorded across mesh levels for FIG. 21 potted article, demonstrating non-zero dielectric force and verifying that coarse-grid residuals fail closed ($|F_{\text{net}}| \approx 25\text{ mN} \gg 23.7\ \mu\text{N}$) (P2-R8-F3).
    3D dielectric benchmark is explicitly designated `PROVISIONAL_3D_DIELECTRIC_BENCHMARK_APPROXIMATE_AGREEMENT`. Whole-body 3D dielectric accounting honestly reports `whole_body_3d_mechanical_accounting = "UNVERIFIED_PENDING_CONFORMING_INTERFACE_MESHING"` due to Cartesian staircasing, uncomputed virtual work fields adopt strict `Optional[float] = None` semantics, and the gate enforces an explicit allowlist (`VERIFIED_WHOLE_BODY_STATES`) that strictly rejects all unverified states and fails closed.
- **Model H1 (Patent-Specific Alternative US11511891B2 Eq. 4–11, P2-R5-F4, P2-R6-M1, P2-R7-M1 & P2-R8-M1 Remediation):**
  - Transcribes Eq. (11): $F = \varepsilon_0 (E_2^2 A_2 - E_1^2 A_1)$.
  - Implements pure function `compute_3d_patent_face_h1_quadrature` evaluating true 3D patent-face H1 quadrature across proximal tip (100a) and distal base (101a):
    1. Evaluates literal Patent Eq. (11): $F_{\text{literal}} = \varepsilon_0 (\iint_{101a} E^2 dA - \iint_{100a} E^2 dA)$. Note that because distal base area ($30.97\text{ cm}^2$) is $24\times$ larger than proximal tip area ($1.29\text{ cm}^2$), literal Eq. (11) yields positive force ($+0.0650\text{ N}$) on the single blade, directly opposing claimed forward thrust! On FIG. 21, 9 tips reverse this to negative force ($-0.0833\text{ N}$).
    2. Evaluates corrected 0.5x Maxwell traction force: $F_{\text{corrected}} = \frac{1}{2}\varepsilon_0 (\iint_{101a} E^2 dA - \iint_{100a} E^2 dA)$.
    3. Evaluates spatial-mean plug-in approximation: $F_{\text{mean}} = \varepsilon_0 (\langle E_{\text{dist}} \rangle^2 A_{\text{dist}} - \langle E_{\text{prox}} \rangle^2 A_{\text{prox}})$.
    4. Confirms Cauchy-Schwarz inequality holds across all faces: $\iint E^2 dA \ge \langle E \rangle^2 A$.
    5. Directly benchmarked on true 3D uniform and non-uniform field arrays to $< 10^{-9}$ error. Validates non-empty spans, reversed spans ($b_{\min} \le b_{\max}$), and strictly positive, finite grid steps $dx, dy, dz > 0$, raising `ValueError` on violations (P2-R8-M1). Labeled provisional (`h1_3d_quadrature_status = "PROVISIONAL_NEAR_FACE_QUADRATURE_SUBJECT_TO_OFFSET_SENSITIVITY"`).
  - Analytical and numerical evaluation confirms:
    1. Misapplication of stationary action $\delta S = 0$ does not imply $d(U_t) = 0$ at Eq. (4).
    2. Missing fundamental factor of $1/2$ in electrostatic surface traction ($\frac{1}{2}\varepsilon_0 E^2$).
    3. Complete neglect of lateral flanks (100b), base front shoulder, ground counter-reaction, and enclosure reactions.
- **Constrained Finite 3D Boundary-Value Model & Full 3D Commensurate Refinement (P2-R4-F1, P2-R5-F1, P2-R6-F1, P2-R7-F1, P2-R7-F4, P2-R8-F1 & P2-R8-F4 Remediation):**
  - Symmetric Positive Definite free-DOF formulation solved via Jacobi-preconditioned CG (`spla.cg(..., rtol=1e-8)`).
  - Multi-level commensurate full 3D refinement series ($h_k = 1.27\text{ mm} / k$ laterally, $dz_k = 2.54\text{ mm} / k$; `refine_z=True` default), ensuring exact $1.0000$ blade thickness ($k$ cells), height ($5k$ cells), gap ($5k$ cells), pitch ($5k$ cells), ground width ($40k$ cells), and $z$ extent without geometric distortion across refinement levels.
  - Inter-level per-body differences $\Delta F_k = |F_{k+1} - F_k| > 23.7\ \mu\text{N}$ are tracked across all bodies (blade, ground, net), demonstrating that coarse-grid discretization uncertainty substantially exceeds the discrimination threshold and failing closed against false acceptance (P2-R8-F1).
  - Multi-body discretization error in `run_3d_mesh_convergence_study` is evaluated across all bodies (`max(body_discretization_errors)`), rather than relying on blade force alone (P2-R8-F4).
  - Validated surrogate-to-article transfer scaling across $\ge 3$ axial lengths ($L_z \in [0.0254, 0.0508, 0.1016\text{ m}]$, 1, 2, 4 inches): linear regression yields $R^2 = 1.000000 > 0.99$ and max fit residual $< 25\ \mu\text{N}$, with $f_{\text{interior}} = -6.957\text{ N/m}$ and constant $+7.22\text{ mN}$ end-cap relief labeled as a single-grid empirical fit observation (P2-R8-F1).
- **Structured 5-Part Uncertainty Budget & Robust Allowlisted Production Discrimination Gate (P2-R4-F2, P2-R5-F2, P2-R6-F2, P2-R6-F3, P2-R7-F2, P2-R8-F4 & P2-R8-F5 Remediation):**
  - Evaluates individual and combined uncertainty terms via centralized production gate `evaluate_physical_scale_discrimination_gate`:
    1. Linear algebra solver residual: $8.4\times 10^{-11}\text{ N}$ ($|F_{\text{blade}}| \times \text{solver\_res}$).
    2. Discrete momentum closure residual: $445–830\ \mu\text{N}$ ($|F_{\text{net}}|$).
    3. Mesh force discretization uncertainty: multi-body discretization uncertainty across all bodies (`max(body_errors)`).
    4. Axial grid discretization uncertainty: requires qualified axial discretization evidence (`z_mesh_discretization_uncertainty_n`); verified states with missing axial evidence are strictly rejected with `"NOT_RESOLVED_MISSING_AXIAL_GRID_DISCRETIZATION_EVIDENCE"` (P2-R8-F4).
    5. Domain boundary clearance placement sensitivity: calibrated across $\ge 3$ clearance multipliers ($1.0\times, 1.5\times, 2.0\times$) in `calibrate_domain_clearance_uncertainty_3d`, confirming monotonic decay of boundary coupling ($|F(1.5)-F(1.0)| = 7.05\text{ mN} > |F(2.0)-F(1.5)| = 2.33\text{ mN}$), labeled as placement sensitivity estimate rather than a proven upper bound relative to infinity (P2-R8-F2). Uncalibrated clearance preserves `None/null` (never substituted with 0.0 or NaN) (P2-R8-F5).
    6. Missing parameter model uncertainty: honestly reported as unquantified/unbounded (`missing_parameter_model_uncertainty_n = None`, `missing_parameter_model_is_bounded = False`) in baseline solves rather than a pseudo-quantified $50\ \mu\text{N}$.
  - Strict allowlist predicate (`VERIFIED_WHOLE_BODY_STATES`) requiring verified mechanical accounting, qualified axial convergence data, and qualified domain clearance calibration, failing closed on all unverified or missing states.
  - Serialization uses `allow_nan=False`, eliminating non-standard NaN tokens and guaranteeing RFC 8259 compliance across all exported manifests (P2-R8-F5).
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
- Entire test suite: **126 tests passed** (35 P0 + 37 P1 + 54 P2).
- Manifest governing review dynamically derived from numerical metadata discovery: `CURRENT_GOVERNING_REVIEW = "P2_R8_REMEDIATION"` (P2-R8-M2 Remediation).
- Paired evidence manifest (`exodus_patent_manifest.json`, schema 1.2.0) and publication comparison figure (`exodus_patent_comparison.png`) updated with strict JSON finiteness (`allow_nan=False`), semantic consistency for uncalibrated clearance (`null`), 3-length transfer regression, 3-point placement sensitivity calibration, and multi-body discretization bounds.
- Version-controlled PR description in `docs/PR_DESCRIPTION.md` mechanically asserted by unit tests (exact test count dynamically verified).
- README research progress verified (2 of 5 gates accepted; P2 active on draft branch).
