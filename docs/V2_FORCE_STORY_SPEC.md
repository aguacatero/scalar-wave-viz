# V2 Design Specification — Whole-Device Force Story (Revision R1 — Draft for Independent Review)

**Status:** **IN PROGRESS — DRAFT R1 SPECIFICATION FOR INDEPENDENT REVIEW (NOT YET INDEPENDENTLY ACCEPTED, NOT IMPLEMENTED, NOT MERGED).**  
**Tracking Issue:** [Issue #30](https://github.com/aguacatero/scalar-wave-viz/issues/30) (`V2 — Whole-Device Force Story`)  
**Specification Branch:** `feat/v2-whole-device-force-story-spec`  
**Verified `main` Baseline:** `3519e409e60c126ca724f9b2bf2bf360a0855592` (post-V1-B3 Polish R2 closeout [PR #29](https://github.com/aguacatero/scalar-wave-viz/pull/29), `main` CI [Run 45547040079](https://github.com/aguacatero/scalar-wave-viz/actions/runs/45547040079) `success`, `229` tests passing)  
**Governing Contracts:** [Scientific Charter](SCIENCE_CHARTER.md), [Exodus Model Contract](EXODUS_MODEL_CONTRACT.md), [Visual Product Vision](PROPULSION_EXPLORER_VISION.md), [Accepted V1 Solver Integration Spec R5](V1_SOLVER_INTEGRATION_SPEC.md) (git blob `3ccf8ae0e8caa4d367d93eddd173dda98a13f00a`, unchanged)  
**Implementation Gate:** **Do NOT begin V2-A or V2-B code implementation until this specification receives independent ChatGPT acceptance (`0 HIGH, 0 MEDIUM`) AND separate explicit owner kickoff authorization.**

---

## 1. Purpose, User Goal & Mandatory Scientific Boundaries

V1 connected interactive Propulsion Explorer controls to validated conventional P0/P1 electrostatic calculations (`parallel_plate_1d` and `grounded_box_2d`) alongside the provisional 3D Exodus schematic and isolated Chapter 5 mathematical scalar-wave contrast view. **V2 — Whole-Device Force Story** bridges the next conceptual gap for curious learners, engineers, and physicists:

> *"If a sharp electrode experiences a strong local electrostatic force, why doesn't the whole device automatically move — where do the opposing forces and momentum go, what ordinary laboratory artifacts can imitate thrust, and what discriminating experiment could tell the difference?"*

Every V2 screen must directly answer the four north-star questions (**What am I seeing? Why does it happen? What changes it? How could we test it?**) while enforcing eight non-negotiable scientific constraints:

1. **Strict Unit & Dimensionality Segregation:** Never mix 1D parallel-plate forces in **`N`**, 2D grounded-box forces per unit depth in **`N/m`**, or conditional H2 comparator estimates in **`N`**, and never multiply a 2D `N/m` result by an assumed length $L_z$ to fabricate a 3D Exodus Newton (`N`) force prediction.
2. **Numerical Residual ≠ Physical Thrust:** Never portray a discrete Maxwell stress closure residual (`|F_net|` in `N/m`, whether balanced `< 1e-4 N/m` or unbalanced `>= 1e-4 N/m`) as measured or predicted propellantless thrust.
3. **Never Coerce Unknowns to Zero:** Never substitute `0.0` for unmodeled, uncalibrated, unbounded, out-of-validity-regime, or pending-acceptance force terms. Unknown terms must carry `value: null` and an explicit typed status code.
4. **Epistemic Distinctness:** Keep **H0** (established conventional electrostatics), **H1** (published Exodus patent hypothesis), **H2** (competing ordinary mechanisms), **mathematical scalar-wave toys** (Chapter 5), and **experimental measurements** (cited literature with apparatus and uncertainty) visually, structurally, and programmatically distinct.
5. **Conditional Ion-Drift Model & No Unjustified Vacuum Extrapolation:** Treat $F_{\text{ion}} \approx I d / \mu$ strictly as a conditional atmospheric-pressure collisional drift-regime estimate with explicitly stated assumptions. **Do not** extrapolate $F_{\text{ion}}$ into rarefied or high-vacuum pressure regimes without a justified kinetic/rarefied-gas model.
6. **Preservation of Frozen Baselines & Zero P2 Leakage:** Preserve frozen P0 (`electrostatics_baseline.py`, blob `97f65dfa25db7730323edd5e52c98b17371fdeaa`), frozen P1 (`electrostatics_numerics.py`, blob `a29f1f3a55946f33760179677dd3dbeb6a2ebde2`), accepted V1 Spec R5 (blob `3ccf8ae0e8caa4d367d93eddd173dda98a13f00a`), accepted V1-A/B1/B2/B3/Polish runtime contracts, and committed B2 snapshots (`explorer/v1_reference_snapshots.js` / `.json`) completely unchanged. Zero imports, copied equations, meshes, or outputs from unaccepted Track B P2 ([Draft PR #11](https://github.com/aguacatero/scalar-wave-viz/pull/11)) may enter V2.
7. **Explicit P2 Pending Gate for 3D Exodus Whole-Device Forces:** The quantitative 3D Exodus whole-device electrostatic force result remains explicitly marked `status: "PENDING_SCIENTIFIC_ACCEPTANCE"` (`value: null`, `blocking_gate: "TRACK_B_P2"`) until a separately reviewed and accepted P2 baseline exists.
8. **No Anomalous Propulsion Claims:** Do not infer or imply demonstrated propellantless propulsion from simulations, patent grants, schematic arrows, or incomplete force accounting. `WHOLE-BODY THRUST: NOT MEASURED / NOT ESTABLISHED` remains invariant across all V2 surfaces.

---

## 2. Epistemic Taxonomy & Hypothesis Architecture (`H0`, `H1`, `H2`)

Every V2 panel, ledger row, comparator readout, and visualization layer must declare one exhaustive `epistemic_class` matching [docs/SCIENCE_CHARTER.md](SCIENCE_CHARTER.md):

| `epistemic_class` | Public Badge Label | Permitted Use in V2 | Prohibited Use |
| --- | --- | --- | --- |
| `"ESTABLISHED_MODEL"` | `ESTABLISHED MODEL` | Outputs of frozen accepted P0/P1 solvers (`parallel_plate_1d`, `grounded_box_2d`) and exact textbook conservation laws / reference comparators (photon momentum, ideal exhaust momentum) | Claiming experimental validation or 3D Exodus thrust |
| `"PUBLISHED_HYPOTHESIS"` | `PUBLISHED HYPOTHESIS` | Cited Exodus patent claims/equations (`US11511891B2`, `US20230121805A1`, `US20240011469A1`) with explicit contested-derivation proof obligations | Implying physical validation or displaying unaccepted P2 numeric outputs |
| `"CONDITIONAL_CONFOUNDER_MODEL"` | `CONDITIONAL CONFOUNDER MODEL` | Parametric textbook order-of-magnitude H2 comparators (atmospheric corona ion-drift $F \approx Id/\mu$, straight-wire geomagnetic Lorentz bound $I L B$) inside declared validity regimes | Presenting as calibrated apparatus measurement or extrapolating outside validity domain |
| `"EXPERIMENTAL_MEASUREMENT"` | `EXPERIMENTAL MEASUREMENT` | Peer-reviewed published experimental bounds with apparatus, units, uncertainty, and controls (e.g., Tajmar & Schreiber 2020 `±0.3 mg ≈ ±3 µN` null limits under studied configurations) | Synthetic/simulated data or uncited thrust claims |
| `"PROVISIONAL_ILLUSTRATIVE_SCENE"` | `PROVISIONAL ILLUSTRATIVE SCENE` | 3D Exodus schematic geometry, schematic field/force directions, Boundary A/B/C visual cut-shells, `#slider-eps` visual opacity proxy | Attaching 1D `N` or 2D `N/m` computed values as 3D blade forces |
| `"TOY_MATHEMATICAL_ILLUSTRATION"` | `MATHEMATICAL TOY (ISOLATED)` | Chapter 5 isolated 3D scalar-wave contrast (`scalarWaveGroup`) | Coupling to capacitor force ledgers or propulsion claims |
| `"UNVERIFIED_PENDING_P2"` | `PENDING SCIENTIFIC ACCEPTANCE (P2)` | 3D Exodus whole-device electrostatic/dielectric force accounting slots (`value: null`) | Substituting `0.0` or importing unaccepted Draft PR #11 outputs |

### 2.1 Hypothesis `H0` — Conventional Electrostatics & Closed-Boundary Momentum Accounting

- **Physical Basis:** Homogeneous vacuum Laplace equation $\nabla^2 \Phi = 0$, $\mathbf{E} = -\nabla \Phi$, and vacuum Maxwell stress tensor
  $$T_{ij} = \varepsilon_0 \left(E_i E_j - \frac{1}{2}|\mathbf{E}|^2 \delta_{ij}\right), \qquad \varepsilon_0 = 8.8541878188 \times 10^{-12}\ \text{F/m}.$$
  Force on any isolated body $k$ enclosed by a vacuum contour/surface $\partial V_k$ is $\mathbf{F}_k = \oint_{\partial V_k} \mathbf{T}\cdot\hat{\mathbf{n}}\,dA$.
- **Exact Quantitative Sources Permitted in V2 (`H0`):**
  1. **`parallel_plate_1d` (`electrostatics_baseline.parallel_plate_benchmark`, unit: `N`):** Opposing plate forces $F_+ = +\frac{1}{2}\varepsilon_0 E^2 A$ and $F_- = -\frac{1}{2}\varepsilon_0 E^2 A$, exact net pair force $F_{\text{net}} = 0.0\ \text{N}$, cross-checked via fixed-$V$ and fixed-$Q$ virtual work; fringing warning when $\sqrt{A}/d < 5$.
  2. **`grounded_box_2d` (`electrostatics_baseline.electrode_pair_in_grounded_box` + `electrostatics_numerics.evaluate_whole_apparatus_force_budget`, unit: `N/m`):** Full 6-component force budget (`left_electrode`, `right_electrode`, `enclosure_reaction` in $F_x, F_y$) plus discrete closure norm $|\mathbf{F}_{\text{net}}| = \|\mathbf{F}_L + \mathbf{F}_R + \mathbf{F}_{\text{enc}}\|$ evaluated strictly against `tolerance_n_per_m = 1e-4 N/m` (`<` balanced vs `>=` `UNBALANCED_EXCEEDS_TOLERANCE`), using V1's exact Section 3.1/3.3 topology and multi-grid gates.
  3. **3D Exodus Whole-Device `H0` Evaluation:** Explicitly `status: "PENDING_SCIENTIFIC_ACCEPTANCE"` (`value: null`, `blocking_gate: "TRACK_B_P2"`). Qualitative continuum momentum conservation ($\sum \mathbf{F}_{\text{internal}} = \mathbf{0}$; $\mathbf{F}_{\text{DUT,net}} = \oint_{\partial V_A} \mathbf{T}\cdot\hat{\mathbf{n}}\,dA = \mathbf{F}_{\text{external}}$) is explained without fabricating 3D Newton numbers.
- **Core Physical Lesson:** Asymmetric local electrode forces do not imply isolated net propulsion. In `asymmetric_hv_80mm_bench` (`-20 kV / 0 V`), the left electrode and right electrode forces do **not** cancel pairwise (`F_L + F_R ≠ 0`) because unbalanced electric flux terminates on the grounded `0 V` outer box — the missing reaction force appears directly on the enclosure (`F_enc`), restoring whole-system conservation `F_L + F_R + F_enc → 0` as $h \to 0$. In contrast, `bipolar_hv_80mm_bench` (`-10 kV / +10 kV`) suppresses enclosure coupling by symmetry.

### 2.2 Hypothesis `H1` — Published Exodus Patent Proposition (Cited & Unvalidated)

- **Primary Citations:**
  - [US11511891B2](https://patents.google.com/patent/US11511891B2/en) (issued November 29, 2022) — FIGS. 4–8 (single-stage asymmetric blade schematic), FIGS. 6B/21/23A (dielectric potting medium 600 / nine-blade epoxy test article), and derivation Eqs. (4)–(11).
  - Continuation & related applications: [US20230121805A1](https://patents.google.com/patent/US20230121805A1/en), [US20240011469A1](https://patents.google.com/patent/US20240011469A1/en), [Exodus patent list](https://ept.space/patents/).
- **Mandatory Contested-Derivation Audit Ledger (from [docs/EXODUS_MODEL_CONTRACT.md](EXODUS_MODEL_CONTRACT.md)):**
  1. **Eq. (4) — Claimed $d(U_t) = 0$ from stationary action ($\delta S = 0$):**
     - *Audit note:* Stationary action $\delta \int L\,dt = 0$ yields dynamical equations of motion along time trajectories; it does not establish pointwise spatial energy invariance $d(U_t) = 0$ across configuration displacements and omits power-supply electrical work ($dW = V\,dQ$) and structural reaction forces.
     - *Disposition:* `CONTESTED_DERIVATION_PROOF_OBLIGATION`.
  2. **Eq. (11) — Claimed net force $F = \varepsilon_0 (E_2^2 A_2 - E_1^2 A_1)$:**
     - *Audit note:* (a) Omits the standard Maxwell stress factor of $\frac{1}{2}$ in $T_n = \frac{1}{2}\varepsilon_0 E_n^2$; (b) evaluates only two opposed electrode faces while omitting lateral/rear electrode surfaces, feedthroughs, solid dielectric polarization stress, structural mount reactions, and return flux to external grounded boundaries.
     - *Disposition:* `PUBLISHED_HYPOTHESIS` (`numerical_evaluation_status: "PENDING_SCIENTIFIC_ACCEPTANCE"`).
- **Strict Non-Implication Rule:** V2 never computes or displays a 3D Exodus `H1` Newton prediction from unaccepted Draft PR #11, never equates USPTO patent grant with experimental or mathematical validation, and always pairs H1 cards with the explicit proof-obligation audit above.

### 2.3 Hypothesis `H2` — Competing Ordinary Laboratory Mechanisms (Confounders)

V2 models four competing ordinary mechanisms capable of producing apparent micro-Newton to milli-Newton forces on high-voltage laboratory apparatuses:

| ID | Competing Mechanism | V2 Quantitative / Qualitative Representation | Explicit Assumptions & Validity Limits |
| --- | --- | --- | --- |
| **`H2-ION`** | **Corona Discharge / Ion Wind (Atmospheric Air)** | Conditional 1D collisional drift-regime comparator: $F_{\text{ion}} \approx \dfrac{I \cdot d}{\mu}$ (`N`).<br>*Dimensional check:* $\text{A}\cdot\text{m} / (\text{m}^2\cdot\text{V}^{-1}\cdot\text{s}^{-1}) = \text{A}\cdot\text{V}\cdot\text{s}/\text{m} = \text{J}/\text{m} = \text{N}$.<br>*Inputs:* $I \in [0, 500]\ \mu\text{A}$, $d \in [5, 100]\ \text{mm}$, $\mu \in [1.2, 2.5] \times 10^{-4}\ \text{m}^2/(\text{V}\cdot\text{s})$ (default $2.0 \times 10^{-4}$ literature range for air ions at `1 atm`). | **Strict Validity Gate (`ATMOSPHERIC_COLLISIONAL_AIR_ONLY`):** Valid **only** as an order-of-magnitude upper-scale estimate in steady, unipolar, space-charge-limited collisional ion drift at ~`1 atm` (`760 Torr`) where Knudsen number $Kn = \lambda/d \ll 1$, ion drift speed dominates bulk airflow, and neutral collisions transfer 100% of ion momentum to gas. **Prohibition:** Must **never** extrapolate $F_{\text{ion}}(P)$ into vacuum/rarefied pressures via $\mu \propto 1/P$ or ad-hoc pressure scaling. Selecting rarefied/high-vacuum inspection (`P < 10^-5 Torr`) returns `value: null`, `status: "OUT_OF_MODEL_VALIDITY_REGIME"` with qualitative density-drop explanation (~7.88 orders of magnitude from `760` to `10^-5 Torr`) and Tajmar & Schreiber (2020) citation. |
| **`H2-WALL`** | **Chamber Wall / Enclosure Image-Charge Coupling** | **Accepted P0/P1 `grounded_box_2d` evidence (`N/m`):** Side-by-side comparison of asymmetric single-ended HV (`asymmetric_hv_80mm_bench`, `-20 kV / 0 V`) vs symmetric bipolar HV (`bipolar_hv_80mm_bench`, `-10 kV / +10 kV`), plus (in live `run_v1_solver.py` mode only) an optional serialized 3-point box-width clearance sweep (`W ∈ {0.080, 0.120, 0.160} m` at fixed electrode geometry, each validated through V1 Section 3.1/3.2 gates). | Strictly **2D vacuum circular electrodes (`N/m`)** demonstrating how external grounded boundary proximity changes wall reaction force $F_{\text{enc}}$. Never converted to 3D `N` or presented as a calibrated 3D vacuum-chamber correction. Offline mode locks live sweep and compares bundled B2 snapshots only. |
| **`H2-WIRE`** | **Power-Lead Lorentz Force, Electrostatic Lead Pull & Support Reactions** | Conditional straight-wire geomagnetic Lorentz upper-bound comparator: $F_{\text{Lorentz,max}} = I_{\text{lead}} \cdot L_{\text{lead}} \cdot B_{\text{ambient}}$ (`N`).<br>*Dimensional check:* $\text{A}\cdot\text{m}\cdot\text{T} = \text{N}$.<br>*Inputs:* $I_{\text{lead}} \in [0, 100]\ \text{mA}$, $L_{\text{lead}} \in [0.05, 1.0]\ \text{m}$, $B_{\text{ambient}} \in [25, 65]\ \mu\text{T}$ (default $50\ \mu\text{T}$).<br>**Electrostatic lead attraction, cable stiffness hysteresis, and support reaction magnitude:** explicitly `value: null`, `status: "UNKNOWN_UNMODELED"`. | Assumes a single unshielded straight current segment perpendicular to uniform $B_{\text{ambient}}$ (ignores twisted-pair/coaxial cancellation). Provides an order-of-magnitude upper bound on magnetic lead artifacts only; does not model AC EMI, electrostatic wire sag, or mechanical feedthrough creep. |
| **`H2-DRIFT`** | **Thermal Drift, Outgassing & Instrument / Balance Systematics** | Quantitative magnitude for an uncalibrated apparatus is strictly **`value: null`, `status: "UNKNOWN_UNMODELED"`** (zero fabricated drift equations). Paired with cited peer-reviewed experimental noise/null benchmark: **Tajmar & Schreiber (2020)** (*J. Electrostat.* 107, 103477, DOI `10.1016/j.elstat.2020.103477`) reporting null force bounds down to `±0.3 mg ≈ ±3 µN` under studied high-vacuum balance configurations. | Experimental resolution and thermal-drift rates depend strictly on specific torsion/precision balance hardware, thermal shielding, pump vibration isolation, and vacuum outgassing history. Never generalized as a universal instrument floor. |

---

## 3. System-Boundary Force & Momentum-Accounting Ledgers (`Boundary A`, `B`, `C`)

V2 replaces static prose-only ledger tables with a synchronized, provenance-aware **Three-Boundary Momentum Ledger** covering three selectable physical contexts: (1) **Active 2D P0/P1 Benchmark (`N/m`)**, (2) **Active 1D P0 Ideal Parallel-Plate (`N`)**, and (3) **Provisional 3D Exodus Schematic (`PENDING_SCIENTIFIC_ACCEPTANCE`)**. Contexts are **never mixed** in one table.

### 3.1 Boundary Definitions & Momentum-Transfer Paths

| Boundary | Physical Control Volume | Governing Conservation Statement | Momentum-Transfer Paths |
| --- | --- | --- | --- |
| **Boundary A — Device Under Test (`boundary_a_dut`)** | Suspended test assembly: high-voltage electrode(s), counter-electrode, dielectric potting (3D schematic only), and internal structural mount. | $\sum \mathbf{F}_{\text{internal}} \equiv \mathbf{0}$ (Newton III pairwise cancellation).<br>$\mathbf{F}_{\text{DUT,net}} = \oint_{\partial V_A} \mathbf{T}\cdot\hat{\mathbf{n}}\,dA + \mathbf{F}_{\text{mech,ext}} + \mathbf{F}_{\text{gas/ion}} = \mathbf{F}_{\text{external}}$. | 1. Internal electrode $\leftrightarrow$ electrode traction transmitted through structural mount (closed internally).<br>2. Internal dielectric polarization stress balanced by electrodes/mount (closed internally; 3D quantitative value `PENDING_SCIENTIFIC_ACCEPTANCE`).<br>3. External electric flux crossing $\partial V_A$ to Boundary B chamber walls.<br>4. External leads/feedthroughs or ambient gas ions crossing $\partial V_A$. |
| **Boundary B — Chamber & External Environment (`boundary_b_environment`)** | Grounded conductive vacuum chamber / enclosure walls, laboratory ground, external power leads/feedthroughs, and ambient gas (if not in high vacuum). | $\mathbf{F}_{\text{B}} = \mathbf{F}_{\text{wall,image}} + \mathbf{F}_{\text{leads,ext}} + \mathbf{F}_{\text{gas,reaction}}$. | Receives equal and opposite momentum from any unbalanced external electric flux (`enclosure_reaction` in `grounded_box_2d`), HV cable forces, or atmospheric ion-wind momentum transferred to surrounding air and chamber walls. |
| **Boundary C — Total Closed System (`boundary_c_closed`)** | Complete isolated system enclosing Boundary A + Boundary B + electromagnetic fields ($\mathbf{E}, \mathbf{B} \to \mathbf{0}$ at $\partial V_C$). | $\dfrac{d}{dt}\left(\mathbf{P}_{\text{DUT}} + \mathbf{P}_{\text{env}} + \mathbf{P}_{\text{EM,field}}\right) = \mathbf{0}$.<br>In static electrostatics ($\mathbf{B} = \mathbf{0} \implies \mathbf{P}_{\text{EM}} = \mathbf{0}$): $\mathbf{F}_{\text{A}} + \mathbf{F}_{\text{B}} = \mathbf{0}$ identically in the continuum limit. | Zero net momentum creation. Any non-zero $\mathbf{F}_{\text{net}}$ in a finite-grid 2D simulation is a **numerical discretization closure residual**, never a violation of momentum conservation. |

### 3.2 Exact Per-Context Ledger Contract (No Zero-Coercion of Unknowns)

| Ledger Row | 1D Parallel Plate (`N`) | 2D Grounded Box (`N/m`) | 3D Exodus Schematic (`PENDING_SCIENTIFIC_ACCEPTANCE`) |
| --- | --- | --- | --- |
| **Active / Left Electrode** | `COMPUTED`: `force_on_positive_plate_n` (`+N`) | `COMPUTED`: `(left_electrode_fx_n_per_m, left_electrode_fy_n_per_m)` (`N/m`) *(or `WITHHELD_INELIGIBLE` if topology fails)* | `PENDING_SCIENTIFIC_ACCEPTANCE` (`value: null`; qualitative direction `+X`) |
| **Counter / Right Electrode** | `COMPUTED`: `force_on_negative_plate_n` (`-N`) | `COMPUTED`: `(right_electrode_fx_n_per_m, right_electrode_fy_n_per_m)` (`N/m`) | `PENDING_SCIENTIFIC_ACCEPTANCE` (`value: null`; qualitative direction `-X`) |
| **Dielectric Potting** | `NOT_APPLICABLE_VACUUM_MODEL` (`value: null`, $\varepsilon_r = 1$) | `NOT_APPLICABLE_VACUUM_MODEL` (`value: null`, $\varepsilon_r = 1$) | `PENDING_SCIENTIFIC_ACCEPTANCE` (`value: null`; `#slider-eps` is visual proxy only) |
| **Internal Support Mount** | `UNKNOWN_UNMODELED` (`value: null`; equal & opposite static strut load required to maintain gap $d$) | `UNKNOWN_UNMODELED` (`value: null`; mechanical standoffs not in 2D Laplace model) | `UNKNOWN_UNMODELED` (`value: null`; qualitative constraint reaction) |
| **Boundary A DUT Net Electrostatic Flux** | `COMPUTED`: `net_pair_force_n = 0.0 N` (ideal infinite plates; fringing neglected) | `COMPUTED`: `F_L + F_R` (`N/m`) — explicitly labeled **external wall-coupled DUT flux**, NOT isolated thrust | `PENDING_SCIENTIFIC_ACCEPTANCE` (`value: null`; unknown pending P2 calibrated geometry) |
| **Boundary B Enclosure / Wall Reaction** | `NOT_APPLICABLE_OPEN_1D_LIMIT` (`value: null`) | `COMPUTED`: `(enclosure_reaction_fx_n_per_m, enclosure_reaction_fy_n_per_m)` (`N/m`) | `PENDING_SCIENTIFIC_ACCEPTANCE` (`value: null`) |
| **Boundary B Power Leads & Gas/Ion Coupling** | `UNKNOWN_UNMODELED` (`value: null`) | `UNKNOWN_UNMODELED` (`value: null`) | `UNKNOWN_UNMODELED` (`value: null`; see H2 comparators) |
| **Boundary C Numerical Closure Residual** | `COMPUTED`: `0.0 N` (exact analytic cancellation) | `COMPUTED`: `net_electrostatic_force_norm_n_per_m` (`N/m`) + `force_closure_status` (`BALANCED_WITHIN_TOLERANCE` strictly `< 1e-4 N/m` vs `UNBALANCED_EXCEEDS_TOLERANCE` `>= 1e-4 N/m`) — explicitly labeled **DISCRETIZATION RESIDUAL, NOT THRUST** | `PENDING_SCIENTIFIC_ACCEPTANCE` (`value: null`) |
| **Whole-Body Propellantless Thrust** | `NOT MEASURED / NOT ESTABLISHED` | `NOT MEASURED / NOT ESTABLISHED` | `NOT MEASURED / NOT ESTABLISHED` |

---

## 4. Established-Physics Reference Comparators (Validity-Bounded)

To help beginners calibrate intuition about force magnitudes without fabricating unverified propulsion claims, V2-B includes two strictly textbook **Reference Comparators** (`epistemic_class: "ESTABLISHED_MODEL"`), kept visually distinct from H0 electrostatic stress and H1 patent claims:

1. **Collimated Electromagnetic Radiation Pressure (Photon Recoil):**
   $$F_{\text{photon}} = \frac{P_{\text{em}}}{c}, \qquad c = 299\,792\,458\ \text{m/s (exact SI)}.$$
   - *Dimensional check:* $\text{W} / (\text{m}\cdot\text{s}^{-1}) = \text{J}\cdot\text{s}^{-1}\cdot\text{s}\cdot\text{m}^{-1} = \text{N}$.
   - *Validity regime:* Unidirectional collimated electromagnetic beam in vacuum ($P_{\text{em}} \in [0, 1000]\ \text{W}$; e.g., $1\ \text{W} \to 3.336\ \text{nN}$; $100\ \text{W} \to 0.334\ \mu\text{N}$).
   - *Educational lesson:* Real propellantless EM momentum transfer exists in established Maxwell theory, but requires radiated energy carrying momentum $p = E/c$ at `~3.34 nN/W` — orders of magnitude smaller than typical milli-Newton atmospheric ion wind (`H2-ION`).
2. **Ideal Propellant-Expelling Ion Thruster Exhaust Momentum Rate:**
   $$F_{\text{ion,thruster}} = I_{\text{beam}} \sqrt{\frac{2 m_i V_{\text{acc}}}{q_i}}.$$
   - *Dimensional check:* $\text{A} \cdot \sqrt{\text{kg}\cdot\text{V}/\text{C}} = \text{C}\cdot\text{s}^{-1}\cdot\sqrt{\text{kg}\cdot\text{J}\cdot\text{C}^{-2}} = \sqrt{\text{kg}^2\cdot\text{m}^2/\text{s}^4} = \text{N}$.
   - *Validity regime:* Monoenergetic, collimated, singly ionized ($q_i = e = 1.602176634 \times 10^{-19}\ \text{C}$) propellant exhaust beam (e.g., Xenon $m_{\text{Xe}} = 131.293\ \text{u} = 2.18017 \times 10^{-25}\ \text{kg}$; $I_{\text{beam}} \in [0, 100]\ \text{mA}$, $V_{\text{acc}} \in [100, 5000]\ \text{V}$; ignores beam divergence and doubly charged ions).
   - *Educational lesson:* Conventional electric propulsion achieves milli-Newton thrust by **expelling physical propellant mass** ($\Delta p_{\text{craft}} = -\Delta p_{\text{exhaust}}$), contrasting sharply with claimed closed-system propellantless thrust.

---

## 5. Discriminating Null-Control Matrix

V2-B presents an interactive **Null-Control Laboratory** covering six mandatory experimental controls, each with explicit predictions, observables, assumptions, and limitations:

| Control ID | Experimental Manipulation | Observable & SI Unit | `H0` Conventional Prediction | `H1` Patent Hypothesis Prediction | `H2` Confounder Signature | Key Assumptions & Limitations |
| --- | --- | --- | --- | --- | --- | --- |
| **`NC-VAC`** | **Vacuum Pressure Sweep** (`760 Torr` $\to$ `< 10^-5 Torr`) | Balance force $F_x(P)$ (`µN`), leakage current $I(P)$ (`µA`), pressure $P$ (`Torr` / `Pa`) | $F_{\text{propellantless}} = 0$; air/ion-wind artifacts vanish as gas density drops `~7.9` orders of magnitude; residual wall/lead forces persist if unshielded. | Purported vacuum electrostatic effect should persist at `< 10^-5 Torr` (exact $P$-dependence not derived in US11511891B2). | Corona ion wind & air convection collapse sharply below Paschen / rarefied transition; outgassing jets may spike transiently during pumpdown. | High vacuum suppresses gas collisions but does **not** eliminate chamber image charges, HV cable forces, thermal radiation recoil, or outgassing bursts. |
| **`NC-POL`** | **Voltage Polarity Inversion** (`+V` vs `-V` and `0 V` null) | Force asymmetry $\Delta F = F(+V) - F(-V)$ (`µN`) and $F(V)$ vs $V^2$ fit | Pure Maxwell electrostatic traction is strictly even in voltage ($F \propto V^2$, $\Delta F = 0$); `0 V` yields $0$. | Eq. (11) scales with $E^2 \propto V^2$ (even in $V$, $\Delta F = 0$); polarity-dependent net shift would contradict pure $E^2$ scaling. | Unipolar corona onset asymmetry (negative vs positive Trichel/streamer thresholds), trapped dielectric charge, and DC Lorentz lead force ($F \propto I \times B$) change sign or magnitude under polarity flip. | Requires matched $|+V| = |-V|$ supply stability and full dielectric discharge/rest period between runs to avoid trapped-charge hysteresis. |
| **`NC-FLIP`** | **180° Physical Orientation Flip** on Torsion Balance Arm | Lab-frame force $F_{\text{lab}}(\theta = 0^\circ)$ vs $F_{\text{lab}}(\theta = 180^\circ)$ (`µN`) | Zero true device-fixed thrust ($F_{\text{device}} = 0$); lab-fixed environmental drifts remain invariant. | Genuine device-fixed thrust must invert cleanly in lab coordinates: $F_{\text{lab}}(180^\circ) = -F_{\text{lab}}(0^\circ)$. | Thermal room gradients, floor tilt, pump vibration, and fixed feedthrough drag do **not** invert cleanly; chamber-wall asymmetry may change if device is off-center. | Must maintain identical center-of-mass position, cable routing, and wall clearances before and after the 180° flip. |
| **`NC-WALL`** | **Chamber Wall Clearance Sweep** (increase distance to grounded shield) | Force $F_x(d_{\text{wall}})$ (`µN`) vs enclosure margin $d_{\text{wall}}$ (`m`) | Image-charge coupling to Boundary B decays monotonically toward `0` as $d_{\text{wall}} \to \infty$ (demonstrated in 2D via accepted P1 `grounded_box_2d` box-width sweep in `N/m`). | Internal-only claimed thrust should remain invariant to distant grounded enclosure walls once wall clearance is large. | Strong monotonic decay of measured force as grounded chamber walls move farther away identifies Boundary A $\leftrightarrow$ B electrostatic wall coupling. | Moving walls can alter radiative thermal view factors and vacuum pumping conductance; requires constant vacuum pressure and temperature stabilization. |
| **`NC-DUMMY`** | **Symmetrical / Zero-Asymmetry Dummy Load Control** (same mass, $V$, power dissipation, capacitance, and leads) | Force difference $F_{\text{asym}} - F_{\text{dummy}}$ (`µN`) | Both symmetric dummy and isolated asymmetric DUT produce zero propellantless thrust; any residual matches shared thermal/wire/EMI systematics. | Symmetric dummy has $E_1^2 A_1 = E_2^2 A_2 \implies F_{\text{H1,dummy}} = 0$, whereas asymmetric DUT should depart above combined uncertainty. | Nonzero force on symmetric dummy exposes Joule heating thermal convection/outgassing, HV lead pull, balance EMI pickup, or power-supply recoil. | Dummy must match heat dissipation spatial profile, total HV capacitance, and surface area to avoid differential outgassing. |
| **`NC-ISO`** | **Self-Contained Battery & Wireless Telemetry Isolation** (zero external HV/power leads crossing Boundary A) | Net force $F_{\text{isolated}}$ (`µN`) with on-board HV multiplier and optical/RF telemetry | Eliminates external wire Lorentz/electrostatic forces crossing Boundary A; isolated DUT net force equals remaining chamber/radiation/outgassing coupling only. | True propellantless thrust must persist without external power leads crossing Boundary A. | Force disappearance when external HV feedthroughs are removed identifies lead-wire Lorentz/electrostatic artifacts. | On-board battery/inverter adds mass (reducing torsion-balance sensitivity) and internal heat dissipation (requiring thermal-drift monitoring). |

---

## 6. Beginner-Friendly 3D Visualization Behavior & Progressive Disclosure

V2 preserves the accepted V0.2 nonblocking 3-panel Iceberg architecture and V1 Solver tab, adding a dedicated **Force Story (V2)** experience without visual clutter or regressions:

1. **Progressive Disclosure (Iceberg Depth):**
   - *Surface (Default):* Plain-English cards answering *"Which parts pull on each other, what pulls on the outer chamber, and why does the total stay balanced?"* with color-coded Boundary A (cyan dashed control-volume shell), Boundary B (amber chamber-wall ring/highlight), and Boundary C (closed-system badge).
   - *Shallow:* Side-by-side **H0 vs H1 vs H2** plain-English comparison cards showing what each hypothesis predicts for the exact same apparatus.
   - *Deeper (`<details>`):* Accessible semantic HTML equations (zero raw LaTeX delimiters `\frac`, `\nabla`, `\varepsilon`, `\propto`), dimensional checks, US11511891B2 Eq. (4)/Eq. (11) audit ledger, and H2 validity assumptions.
   - *Research (`<details>`):* Full 6-control Null-Control Matrix, Tajmar & Schreiber (2020) reference bounds, and P2 blocking status (`PENDING_SCIENTIFIC_ACCEPTANCE`).
2. **Strict Visual Separation Rules:**
   - **3D Schematic Mode (`PROVISIONAL_ILLUSTRATIVE_SCENE`):** Optional Boundary A / Boundary B visual highlight toggle outlines the suspended DUT vs grounded chamber walls in the existing Three.js viewport. **Zero** 2D `N/m` or 1D `N` numerical vectors are ever attached to the 3D Exodus knife-edge mesh.
   - **2D Computed Benchmark Mode (`ESTABLISHED_MODEL`):** Reuses the dedicated `#v1-2d-viewport` cross-section canvas (with 3D `forceGroup` hidden) and adds an optional **Boundary A / B / C contour overlay** visually tracing the exact accepted P1 `c_left`, `c_right`, and `c_enclosure_inner` closed integration paths alongside the 6-component `N/m` ledger.
   - **Chapter 5 Scalar-Wave Contrast (`MATHEMATICAL TOY (ISOLATED)`):** Strictly inherits PR #28's `V1-B3-POLISH-R1-M1` isolation invariant — whenever Chapter 5 scalar-wave contrast is active, all V2 Force Story live solver/sweep triggers and V1 1D/2D panels are hidden/disabled, zero `/api/v1/solve` or `/api/v1/study` traffic can fire, and explicit mode transitions silently exit wave contrast via `{ silentV1Notify: true }`.

---

## 7. Implementation Design Contracts (`V2-A` & `V2-B`)

V2 implementation will proceed only **after** independent V2-Spec acceptance and separate owner authorization, split into two reviewable slices:

### 7.1 Slice `V2-A` — H0/H1/H2 Comparison & System-Boundary Momentum Visualization
- **Scope:**
  - Read-only V2 data/contract module (`explorer/v2_force_story_data.js` + `explorer/v2_force_story_ui.js`, plus optional static provenance JSON fixture if needed) consuming **only** accepted V1 solver responses (`window.__v1SolverUI`) and bundled B2 snapshots (`window.V1_REFERENCE_SNAPSHOTS`).
  - Interactive **H0 / H1 / H2 / Compare All** switcher (`role="tablist"` / `role="radiogroup"`), synchronized Three-Boundary Force & Momentum Ledger (`Boundary A / B / C`) across 1D (`N`), 2D (`N/m`), and 3D Schematic (`PENDING_SCIENTIFIC_ACCEPTANCE`) contexts, and 3D Boundary A/B highlight overlay + 2D P1 contour-path overlay.
  - Zero new backend HTTP endpoints; zero changes to `electrostatics_baseline.py`, `electrostatics_numerics.py`, `v1_worker_bridge.py`, `v1_solver_adapter.py`, `run_explorer.py`, `run_v1_solver.py`, or B2 snapshots.

### 7.2 Slice `V2-B` — Competing-Mechanism Comparators & Discriminating Null-Control Laboratory
- **Scope:**
  - Pure-JS + Python parity-tested H2 conditional comparator module (`v2_comparators.py` + JS mirror inside `explorer/v2_force_story_ui.js`):
    - `evaluate_h2_ion_wind_atmospheric(current_a, gap_m, mobility_m2_per_vs, pressure_regime)` -> returns `CONDITIONAL_ESTIMATE` (`N`) ONLY when `pressure_regime == "atmospheric_1atm_collisional"` and inputs are finite & in range; returns `OUT_OF_MODEL_VALIDITY_REGIME` (`value: null`) for `"rarefied_or_high_vacuum"`.
    - `evaluate_h2_lorentz_lead_bound(current_a, length_m, b_field_t)` -> returns `CONDITIONAL_ESTIMATE` (`N`).
    - `evaluate_ref_photon_recoil(power_w)` & `evaluate_ref_ion_exhaust(beam_current_a, accel_voltage_v, ion_mass_kg)` -> returns `ESTABLISHED_MODEL` (`N`).
  - Live `H2-WALL` 3-point chamber-clearance sweep (`W ∈ {0.080, 0.120, 0.160} m` on `asymmetric_hv_80mm_bench` geometry, fixed electrodes `cx = ±0.015 m`, `r = 0.007 m`, `-20 kV / 0 V`, pinned strictly to `n = 101` — empirically verified against accepted `v1_solver_adapter.py` to pass V1 Section 3.1/3.2 gates with `BALANCED_WITHIN_TOLERANCE` `< 1e-4 N/m` at all three widths and monotonic ~10× enclosure reaction decay from `8.38e-2` to `8.43e-3 N/m`; `n = 41` is ineligible at `W = 0.160 m` because `r < 3h`, and `n = 81` at `W = 0.160 m` yields `UNBALANCED_EXCEEDS_TOLERANCE` `8.01e-4 N/m`, which is always reported truthfully if manually queried):
    - **Serialized Single-Slot Execution Contract:** Because V1 enforces `max_concurrent_computes = 1` (HTTP `429` on overlap), the V2-B live clearance sweep dispatches the 3 `/api/v1/solve` calls **strictly sequentially** (awaiting each response before issuing the next), increments `clientStateGeneration` synchronously on start/cancel/mode-change/chapter-change/wave-entry, aborts in-flight `fetch` via `AbortController`, and checks the shared staleness tuple `(gen, reqId, mode, view)` BEFORE rendering or issuing the next step so stale sweeps never overwrite newer state or leak `429` bursts.
    - **Offline Parity Contract (`file://` and static `http.server`):** Disables the arbitrary live 3-point `W` sweep (`SOLVER BRIDGE OFFLINE`), renders truthful bundled B2 snapshot comparison (`asymmetric_hv_80mm_bench` vs `bipolar_hv_80mm_bench` vs `p0_p1_canonical_40mm` with exact frozen snapshot provenance), while keeping purely analytic/conditional H2 & reference comparators (`H2-ION`, `H2-WIRE`, photon recoil, ideal ion exhaust) and the 6-control Null-Control Matrix 100% functional offline.

### 7.3 Typed Schema Contracts (Exhaustive Discriminated Unions)

```ts
type EpistemicClass =
  | "ESTABLISHED_MODEL"
  | "PUBLISHED_HYPOTHESIS"
  | "CONDITIONAL_CONFOUNDER_MODEL"
  | "EXPERIMENTAL_MEASUREMENT"
  | "PROVISIONAL_ILLUSTRATIVE_SCENE"
  | "TOY_MATHEMATICAL_ILLUSTRATION"
  | "UNVERIFIED_PENDING_P2";

type UnitDomain = "N" | "N/m" | "NONE";

type NullableUncertainty = {
  status: "BOUNDED" | "NUMERICAL_RESIDUAL_ONLY" | "NOT_ASSESSED" | "UNBOUNDED_UNKNOWN";
  value: number | null;
  unit: UnitDomain;
  note: string;
};

type LedgerRowValue =
  | {
      status: "COMPUTED";
      value: number;                 // finite IEEE-754 float64
      unit: "N" | "N/m";
      uncertainty: NullableUncertainty;
    }
  | {
      status: "CONDITIONAL_ESTIMATE";
      value: number;                 // finite IEEE-754 float64
      unit: "N";
      validity_regime: string;
      assumptions: string[];
    }
  | {
      status: "UNKNOWN_UNMODELED" | "WITHHELD_INELIGIBLE" | "OUT_OF_MODEL_VALIDITY_REGIME" | "NOT_APPLICABLE_VACUUM_MODEL" | "NOT_APPLICABLE_OPEN_1D_LIMIT";
      value: null;                   // NEVER 0.0
      reason_code: string;
      note: string;
    }
  | {
      status: "PENDING_SCIENTIFIC_ACCEPTANCE";
      value: null;                   // NEVER 0.0
      blocking_gate: "TRACK_B_P2";
      note: string;
    };

interface ForceLedgerRow {
  row_id: string;
  boundary: "boundary_a_dut" | "boundary_b_environment" | "boundary_c_closed";
  component_label: string;
  epistemic_class: EpistemicClass;
  quantity: LedgerRowValue;
  qualitative_direction: string;
  source_citation: string;
}

interface ForceLedgerSnapshot {
  schema_version: "v2.0";
  context_id: "parallel_plate_1d" | "grounded_box_2d" | "schematic_3d_exodus";
  unit_domain: UnitDomain;
  transport_mode: "live" | "offline" | "static_schematic";
  whole_body_thrust_status: "NOT MEASURED / NOT ESTABLISHED";
  p2_scientific_status: "PENDING_SCIENTIFIC_ACCEPTANCE";
  provenance: {
    source_head_sha: string | null;
    kernel_blob_sha1: {
      electrostatics_baseline: "97f65dfa25db7730323edd5e52c98b17371fdeaa";
      electrostatics_numerics: "a29f1f3a55946f33760179677dd3dbeb6a2ebde2";
    };
  };
  rows: ForceLedgerRow[];
}
```

### 7.4 Accessibility, Responsive Layout & Regression Test Requirements

1. **Desktop & Mobile Layout:** Verified at desktop `1280×860` and mobile `375×812` & `390×844` with `document.documentElement.scrollWidth - window.innerWidth <= 1` (`0 px` target overflow), readable wrapping for all ledger tables and null-control cards, and preserved 3D viewport visibility at the top of mobile screens.
2. **Keyboard & ARIA Accessibility:** Full keyboard reachability (`Tab`, `Enter`/`Space`, arrow keys on tablists/radiogroups), accurate `aria-selected` / `aria-checked` / `aria-expanded` / `aria-disabled` states, `aria-live="polite"` status announcements, and zero raw LaTeX delimiters in rendered DOM.
3. **Required Automated Test Suites (Implementation Phase — Pending Spec Acceptance + Owner Kickoff):**
   - **`tests/test_v2_force_story_contracts.py` (Python + Node/JS parity):**
     - Dimensional analysis & exact numeric parity between Python and JS for `H2-ION`, `H2-WIRE`, `REF-PHOTON`, and `REF-ION-EXHAUST`.
     - Strict vacuum out-of-validity-regime test proving `evaluate_h2_ion_wind_atmospheric(..., pressure_regime="rarefied_or_high_vacuum")` returns `value is None` and `status == "OUT_OF_MODEL_VALIDITY_REGIME"`.
     - Schema rejection tests proving unknown/pending/unmodeled rows reject numeric `0.0` coercion, cross-unit (`N` + `N/m`) aggregation is rejected, and `whole_body_thrust_status == "NOT MEASURED / NOT ESTABLISHED"`.
     - Cryptographic preservation tests confirming unchanged git blob SHA-1 for `electrostatics_baseline.py`, `electrostatics_numerics.py`, and `docs/V1_SOLVER_INTEGRATION_SPEC.md`, `--check-committed` snapshot parity, and **zero** Track B P2 (`exodus_hypothesis_evaluator`, `exodus_patent_geometry`, `p2_`) imports.
   - **`tests/test_v2_browser_smoke.py` (Playwright — Desktop `1280×860`, Mobile `375×812` & `390×844`):**
     - **V2-A:** H0/H1/H2/Compare All switching; Boundary A/B/C ledger sync across 1D (`N`), 2D (`N/m`), and 3D Schematic (`PENDING_SCIENTIFIC_ACCEPTANCE`); verified `UNBALANCED_EXCEEDS_TOLERANCE` coarse `n=41` banner never labeled thrust; Boundary A/B 3D highlight and 2D contour overlay toggles; zero 2D `N/m` arrows on 3D Exodus blade.
     - **V2-B:** H2 atmospheric ion-wind calculation vs high-vacuum `OUT_OF_MODEL_VALIDITY_REGIME` display; Lorentz wire comparator & reference comparators; 6-control Null-Control Matrix keyboard/disclosure navigation; live sequential 3-point `W` clearance sweep under `run_v1_solver.py` with mid-sweep cancellation/stale-response rejection; truthful `file://` and static `http.server` offline fallback locking live sweep while keeping offline B2 preset comparison and comparators working.
     - **Preservation & Isolation:** Chapter 5 scalar-wave isolation (`> 200 ms` post-debounce zero `/api/v1/solve` & `/api/v1/study` checks across V2 triggers), zero console/page errors, `<= 1 px` mobile overflow, and full `229`-test V0/V0.1/V0.2/V1/P0/P1 suite passing without regression.

---

## 8. Independent Review Acceptance Criteria (V2 Spec R1)

This specification is ready for independent ChatGPT acceptance when:

1. All 8 mandatory scientific constraints (Section 1) are satisfied with zero unit conflation, zero `0.0` coercion of unknowns, zero P2 physics leakage, and no unjustified vacuum extrapolation of $F \approx Id/\mu$.
2. H0, H1 (with exact US11511891B2 citations and Eq. 4 / Eq. 11 contested-derivation audit), H2 (with explicit validity domains), Boundary A/B/C ledgers, reference comparators, and the 6-control Null-Control Matrix are scientifically sound and internally consistent.
3. V2-A and V2-B implementation contracts, typed schemas, live/offline parity, single-slot V1 sweep serialization, Chapter 5 isolation, accessibility, and automated test suites are complete and unambiguously testable.
4. Frozen P0/P1 kernels, accepted V1 Spec R5, accepted V1 baselines, and Track B P2 (`Draft PR #11`) remain untouched; Track B remains at `2 of 5` accepted scientific gates.
5. **Independent Review Verdict:** `0 HIGH, 0 MEDIUM` findings on this specification, followed by separate explicit owner authorization before opening any V2-A or V2-B implementation branch.
