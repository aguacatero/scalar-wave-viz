# V2 Design Specification — Whole-Device Force Story (Revision R4 — Draft for Independent Re-Review)

**Status:** **IN PROGRESS — DRAFT R4 SPECIFICATION FOR INDEPENDENT RE-REVIEW (NOT YET INDEPENDENTLY ACCEPTED, NOT IMPLEMENTED, NOT MERGED).**  
**Tracking Issue:** [Issue #30](https://github.com/aguacatero/scalar-wave-viz/issues/30) (`V2 — Whole-Device Force Story`)  
**Draft PR:** [PR #31](https://github.com/aguacatero/scalar-wave-viz/pull/31) (`OPEN`, `draft`, unmerged)  
**Specification Branch:** `feat/v2-whole-device-force-story-spec`  
**Prior Reviewed SHAs & Governing Reviews:**
- R3 SHA `e4ff7b8cd0a3ebf7a8b4548a6cc2ef3920e042eb` — [ChatGPT Independent R3 Review #6068596697](https://github.com/aguacatero/scalar-wave-viz/pull/31#pullrequestreview-6068596697) (`REVISE — 0 HIGH, 2 MEDIUM, 0 LOW`; remediating `V2-SPEC-R3-M1`, `V2-SPEC-R3-M2` in R4)
- R2 SHA `4717a60f31e04a1e7c459d3c2b14acaa8bacb0ef` — [ChatGPT Independent R2 Review #6066454553](https://github.com/aguacatero/scalar-wave-viz/pull/31#pullrequestreview-6066454553) (`REVISE — 0 HIGH, 2 MEDIUM, 1 LOW`; R2 remediations preserved and hardened)
- R1 SHA `453f7840461c7f2d1de1c2515421cc6df7c075a6` — [ChatGPT Independent R1 Review #6059541798](https://github.com/aguacatero/scalar-wave-viz/pull/31#pullrequestreview-6059541798) (`REVISE — 0 HIGH, 5 MEDIUM, 2 LOW`; all 7 R1 remediations `V2-SPEC-R1-M1`–`M5`, `L1`, `L2` preserved)  
**Verified `main` Baseline:** `3519e409e60c126ca724f9b2bf2bf360a0855592` (post-V1-B3 Polish R2 closeout [PR #29](https://github.com/aguacatero/scalar-wave-viz/pull/29), `main` CI [Run 45547040079](https://github.com/aguacatero/scalar-wave-viz/actions/runs/45547040079) `success`, `229` tests passing)  
**Governing Contracts:** [Scientific Charter](SCIENCE_CHARTER.md), [Exodus Model Contract](EXODUS_MODEL_CONTRACT.md), [Visual Product Vision](PROPULSION_EXPLORER_VISION.md), [Accepted V1 Solver Integration Spec R5](V1_SOLVER_INTEGRATION_SPEC.md) (git blob `3ccf8ae0e8caa4d367d93eddd173dda98a13f00a`, unchanged)  
**Implementation Gate:** **Do NOT begin V2-A or V2-B code implementation until this specification receives independent ChatGPT acceptance (`0 HIGH, 0 MEDIUM`) AND separate explicit owner kickoff authorization.**

---

## 1. Purpose, User Goal & Mandatory Scientific Boundaries

V1 connected interactive Propulsion Explorer controls to validated conventional P0/P1 electrostatic calculations (`parallel_plate_1d` and `grounded_box_2d`) alongside the provisional 3D Exodus schematic and isolated Chapter 5 mathematical scalar-wave contrast view. **V2 — Whole-Device Force Story** bridges the next conceptual gap for curious learners, engineers, and physicists:

> *"If a sharp electrode experiences a strong local electrostatic force, why doesn't the whole device automatically move — where do the opposing forces and momentum go, what ordinary laboratory artifacts can imitate thrust, and what discriminating experiment could tell the difference?"*

Every V2 screen must directly answer the four north-star questions (**What am I seeing? Why does it happen? What changes it? How could we test it?**) while enforcing eight non-negotiable scientific constraints:

1. **Strict Unit & Dimensionality Segregation:** Never mix 1D parallel-plate forces in **`N`**, 2D grounded-box signed vector forces per unit depth in **`N/m`**, or conditional H2 comparator estimates in **`N`**, and never multiply a 2D `N/m` result by an assumed length $L_z$ to fabricate a 3D Exodus Newton (`N`) force prediction. Never imply that a 1D ideal plate or 2D circular-electrode calculation represents the 3D patented Exodus blade apparatus.
2. **Numerical Residual ≠ Physical Thrust:** Never portray a discrete Maxwell stress closure residual (`|F_net|` in `N/m`, whether balanced `< 1e-4 N/m` or unbalanced `>= 1e-4 N/m`) as measured or predicted propellantless thrust.
3. **Never Coerce Unknowns to Zero:** Never substitute `0.0` for unmodeled, uncalibrated, unbounded, invalid, out-of-validity-regime, withheld, or pending-acceptance force terms. Non-computed terms must carry `value: null` (never numeric `0.0`) and an explicit typed status code.
4. **Epistemic Distinctness:** Keep **H0** (established conventional electrostatics), **H1** (published Exodus patent hypothesis), **H2** (competing ordinary mechanisms), **mathematical scalar-wave toys** (Chapter 5), and **experimental measurements** (cited literature with apparatus and uncertainty) visually, structurally, and programmatically distinct.
5. **Conditional Ion-Drift Model & No Unjustified Vacuum Extrapolation:** Treat $F_{\text{ion}} \approx I d / \mu$ strictly as a conditional atmospheric-pressure collisional drift-regime estimate with explicitly stated assumptions. **Do not** extrapolate $F_{\text{ion}}$ into rarefied or high-vacuum pressure regimes without a justified kinetic/rarefied-gas model.
6. **Preservation of Frozen Baselines & Zero P2 Leakage:** Preserve frozen P0 (`electrostatics_baseline.py`, blob `97f65dfa25db7730323edd5e52c98b17371fdeaa`), frozen P1 (`electrostatics_numerics.py`, blob `a29f1f3a55946f33760179677dd3dbeb6a2ebde2`), accepted V1 Spec R5 (blob `3ccf8ae0e8caa4d367d93eddd173dda98a13f00a`), accepted V1-A/B1/B2/B3/Polish behavior and contracts, and committed B2 snapshots (`explorer/v1_reference_snapshots.js` / `.json`) completely unchanged. Zero imports, copied equations, meshes, or outputs from unaccepted Track B P2 ([Draft PR #11](https://github.com/aguacatero/scalar-wave-viz/pull/11)) may enter V2.
7. **Explicit P2 Pending Gate for 3D Exodus Whole-Device Forces:** The quantitative 3D Exodus whole-device electrostatic force result remains explicitly marked `status: "PENDING_SCIENTIFIC_ACCEPTANCE"` (`value: null`, `blocking_gate: "TRACK_B_P2"`) until a separately reviewed and accepted P2 baseline exists.
8. **No Anomalous Propulsion Claims:** Do not infer or imply demonstrated propellantless propulsion from simulations, patent grants, schematic arrows, or incomplete force accounting. `WHOLE-BODY THRUST: NOT MEASURED / NOT ESTABLISHED` remains invariant across all V2 surfaces.

---

## 2. Epistemic Taxonomy, Scientific Charter Crosswalk & Hypothesis Architecture (`H0`, `H1`, `H2`)

### 2.1 V2 Seven-Class UI Taxonomy ↔ Scientific Charter Five-Category Crosswalk (`V2-SPEC-R1-L1`)

[docs/SCIENCE_CHARTER.md](SCIENCE_CHARTER.md) defines **five** canonical epistemic categories: `ESTABLISHED MODEL`, `PUBLISHED HYPOTHESIS`, `WHAT-IF PARAMETER`, `EXPERIMENTAL MEASUREMENT`, and `UNVERIFIED NUMERICAL OUTPUT`. V2 uses a **seven-value** panel/row `epistemic_class` enum to distinguish visual/illustrative/pending UI surfaces cleanly, paired with an **orthogonal `charter_categories` crosswalk** and mandatory **`WHAT-IF PARAMETER` disclosure** on every user-chosen unmeasured parameter so zero Charter categories are lost or obscured:

| V2 `epistemic_class` | Public UI Badge Label | Exact Scientific Charter Category Mapping | Orthogonal `WHAT-IF PARAMETER` Rule | Permitted Use in V2 | Prohibited Use |
| --- | --- | --- | --- | --- | --- |
| `"ESTABLISHED_MODEL"` | `ESTABLISHED MODEL` | `ESTABLISHED MODEL` | None on canonical constants ($\varepsilon_0$, $c$, $e$, $m_{\text{Xe}}$); user-selected exploratory slider inputs on textbook comparators carry `WHAT-IF PARAMETER` tag | Frozen P0/P1 solver outputs (`parallel_plate_1d`, `grounded_box_2d`) and exact textbook conservation laws / reference comparators | Claiming experimental validation or 3D Exodus thrust |
| `"PUBLISHED_HYPOTHESIS"` | `PUBLISHED HYPOTHESIS` | `PUBLISHED HYPOTHESIS` | Patent-cited dimensions/potentials flagged as sourced claims, not validated measurements | Cited Exodus patent claims/equations (`US11511891B2`, `US20230121805A1`, `US20240011469A1`) with contested-derivation audit | Implying physical validation or displaying unaccepted P2 numeric outputs |
| `"CONDITIONAL_CONFOUNDER_MODEL"` | `CONDITIONAL CONFOUNDER MODEL` | `ESTABLISHED MODEL` *(equation form strictly inside stated validity regime)* + `WHAT-IF PARAMETER` *(on unmeasured user inputs)* | **Mandatory `WHAT-IF PARAMETER` badge** on every user-adjusted unmeasured parameter ($I$, $d$, $\mu$, $I_{\text{lead}}$, $L_{\text{lead}}$, $B_{\text{ambient}}$) | Parametric textbook order-of-magnitude H2 comparators (`H2-ION` atmospheric air only, `H2-WIRE` straight-wire bound) | Presenting as calibrated apparatus measurement or extrapolating outside validity regime |
| `"EXPERIMENTAL_MEASUREMENT"` | `EXPERIMENTAL MEASUREMENT` | `EXPERIMENTAL MEASUREMENT` | None (sourced published values only) | Peer-reviewed published experimental bounds with apparatus, units, uncertainty, and controls (e.g., Tajmar & Schreiber 2020 `±0.3 mg ≈ ±3 µN` under studied configurations) | Synthetic/simulated data or uncited thrust claims |
| `"PROVISIONAL_ILLUSTRATIVE_SCENE"` | `PROVISIONAL ILLUSTRATIVE SCENE` | `UNVERIFIED NUMERICAL OUTPUT` *(non-computed schematic)* + `WHAT-IF PARAMETER` *(on `#slider-eps` visual proxy & sandbox sliders)* | **Mandatory `WHAT-IF PARAMETER` / `VISUAL PROXY ONLY`** on `#slider-eps` | 3D Exodus schematic geometry, schematic field/force directions, Boundary A/B/C visual cut-shells | Attaching 1D `N` or 2D `N/m` computed values as 3D blade forces |
| `"TOY_MATHEMATICAL_ILLUSTRATION"` | `MATHEMATICAL TOY (ISOLATED)` | `UNVERIFIED NUMERICAL OUTPUT` *(illustrative mathematical toy)* + `WHAT-IF PARAMETER` *(arbitrary toy wave parameters)* | Toy wave speed/frequency explicitly non-physical | Chapter 5 isolated 3D scalar-wave contrast (`scalarWaveGroup`) | Coupling to capacitor force ledgers or propulsion claims |
| `"UNVERIFIED_PENDING_P2"` | `PENDING SCIENTIFIC ACCEPTANCE (P2)` | `UNVERIFIED NUMERICAL OUTPUT` *(withheld pending Track B P2 acceptance)* | N/A (`value: null`) | 3D Exodus whole-device electrostatic/dielectric force slots (`value: null`, `blocking_gate: "TRACK_B_P2"`) | Substituting `0.0` or importing unaccepted Draft PR #11 outputs |

### 2.2 Strict Cross-Geometry Comparison Architecture (`V2-SPEC-R1-M1`)

Because accepted P0/P1 solvers model **1D infinite parallel plates** (`N`) and **2D circular conductors in a grounded square box** (`N/m`), whereas Exodus patent hypothesis `H1` refers to a **distinct 3D tapered knife-edge blade + dielectric potting assembly** whose quantitative 3D analysis remains pending under Track B P2, V2 **strictly prohibits** comparing H0, H1, and H2 numerically as if they evaluated the same physical apparatus. Instead, V2 enforces two **separate, non-conflating comparison surfaces**:

1. **Surface A — Qualitative 3D Exodus DUT Hypothesis Framing (`comparison_surface: "qualitative_3d_dut_hypotheses"`):**
   - Explicitly bannered: `QUALITATIVE 3D EXODUS COMPARISON — NO ACCEPTED 3D QUANTITATIVE FORCE SOLUTION (P2 PENDING)`.
   - Compares **H0** (qualitative continuum Maxwell momentum conservation; 3D quantitative DUT force `PENDING_SCIENTIFIC_ACCEPTANCE`), **H1** (`PUBLISHED_HYPOTHESIS` citing US11511891B2 Eqs. 4–11 + contested-derivation audit; 3D quantitative prediction `PENDING_SCIENTIFIC_ACCEPTANCE`), and **H2** (qualitative competing laboratory mechanisms + conditional atmospheric/wire order-of-magnitude scales clearly tagged as separate textbook bounds, NOT 3D Exodus predictions).
   - **Invariant:** Zero computed 1D (`N`) or 2D (`N/m`) P0/P1 numbers may appear inside Surface A's H0/H1/H2 comparison cards.
2. **Surface B — Separate Quantitative P0/P1 Benchmark Analogues (`comparison_surface: "quantitative_p0_p1_analogues"`):**
   - Explicitly bannered: `SEPARATE IDEALIZED P0/P1 BENCHMARK ANALOGUE — NOT 3D EXODUS GEOMETRY`.
   - Displays **either** the active `parallel_plate_1d` (`N`) balance **or** the active `grounded_box_2d` (`N/m`) 6-component vector balance — illustrating *how conventional closed-boundary momentum accounting works quantitatively* in an accepted benchmark geometry without implying shared geometry with the 3D Exodus blade assembly or pairing P0/P1 numbers side-by-side against an H1 patent thrust claim.

### 2.3 Hypothesis `H0` — Conventional Electrostatics & Closed-Boundary Momentum Accounting

- **Physical Basis:** Homogeneous vacuum Laplace equation $\nabla^2 \Phi = 0$, $\mathbf{E} = -\nabla \Phi$, and vacuum Maxwell stress tensor
  $$T_{ij} = \varepsilon_0 \left(E_i E_j - \frac{1}{2}|\mathbf{E}|^2 \delta_{ij}\right), \qquad \varepsilon_0 = 8.8541878188 \times 10^{-12}\ \text{F/m}.$$
  Force on any isolated body $k$ enclosed by a vacuum contour/surface $\partial V_k$ is $\mathbf{F}_k = \oint_{\partial V_k} \mathbf{T}\cdot\hat{\mathbf{n}}\,dA$.
- **Exact Quantitative Benchmark Sources Permitted in V2 (`H0`, Surface B only):**
  1. **`parallel_plate_1d` (`electrostatics_baseline.parallel_plate_benchmark`, unit: `N`):** Opposing plate forces $F_+ = +\frac{1}{2}\varepsilon_0 E^2 A$ and $F_- = -\frac{1}{2}\varepsilon_0 E^2 A$, exact net pair force $F_{\text{net}} = 0.0\ \text{N}$, cross-checked via fixed-$V$ and fixed-$Q$ virtual work; fringing warning when $\sqrt{A}/d < 5$.
  2. **`grounded_box_2d` (`electrostatics_baseline.electrode_pair_in_grounded_box` + `electrostatics_numerics.evaluate_whole_apparatus_force_budget`, unit: `N/m`):** Full 6-component signed vector force budget (`left_electrode`, `right_electrode`, `enclosure_reaction` in signed `fx_n_per_m, fy_n_per_m`) plus discrete closure residual (`net_electrostatic_force_fx_n_per_m`, `net_electrostatic_force_fy_n_per_m`, `net_electrostatic_force_norm_n_per_m`) evaluated strictly against `tolerance_n_per_m = 1e-4 N/m` (`<` `BALANCED_WITHIN_TOLERANCE` vs `>=` `UNBALANCED_EXCEEDS_TOLERANCE`), using V1's exact Section 3.1/3.3 topology and multi-grid gates.
  3. **3D Exodus Whole-Device `H0` Evaluation (Surface A):** Explicitly `status: "PENDING_SCIENTIFIC_ACCEPTANCE"` (`value: null`, `blocking_gate: "TRACK_B_P2"`). Qualitative continuum momentum conservation ($\sum \mathbf{F}_{\text{internal}} = \mathbf{0}$; $\mathbf{F}_{\text{DUT,net}} = \oint_{\partial V_A} \mathbf{T}\cdot\hat{\mathbf{n}}\,dA = \mathbf{F}_{\text{external}}$) is explained without fabricating 3D Newton numbers.
- **Core Physical Lesson (Demonstrated in Separate 2D Analogue):** In `asymmetric_hv_80mm_bench` (`-20 kV / 0 V`), the left electrode and right electrode forces do **not** cancel pairwise (`F_L + F_R ≠ 0`) because unbalanced electric flux terminates on the grounded `0 V` outer box — the missing reaction force appears directly on the enclosure (`F_enc`), restoring whole-system conservation `F_L + F_R + F_enc → 0` as $h \to 0$. In contrast, `bipolar_hv_80mm_bench` (`-10 kV / +10 kV`) suppresses enclosure coupling by symmetry.

### 2.4 Hypothesis `H1` — Published Exodus Patent Proposition (Cited & Unvalidated)

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

### 2.5 Hypothesis `H2` — Competing Ordinary Laboratory Mechanisms (Confounders)

V2 models four competing ordinary mechanisms capable of producing apparent micro-Newton to milli-Newton forces on high-voltage laboratory apparatuses:

| ID | Competing Mechanism | V2 Quantitative / Qualitative Representation | Explicit Assumptions & Validity Limits |
| --- | --- | --- | --- |
| **`H2-ION`** | **Corona Discharge / Ion Wind (Atmospheric Air)** | Conditional 1D collisional drift-regime comparator: $F_{\text{ion}} \approx \dfrac{I \cdot d}{\mu}$ (`N`).<br>*Dimensional check:* $\text{A}\cdot\text{m} / (\text{m}^2\cdot\text{V}^{-1}\cdot\text{s}^{-1}) = \text{A}\cdot\text{V}\cdot\text{s}/\text{m} = \text{J}/\text{m} = \text{N}$.<br>*`WHAT-IF PARAMETER` inputs:* $I \in [0, 500]\ \mu\text{A}$, $d \in [5, 100]\ \text{mm}$, $\mu \in [1.2, 2.5] \times 10^{-4}\ \text{m}^2/(\text{V}\cdot\text{s})$ (default $2.0 \times 10^{-4}$ literature range for air ions at `1 atm`). | **Strict Validity Gate (`ATMOSPHERIC_COLLISIONAL_AIR_ONLY`):** Valid **only** as an order-of-magnitude upper-scale estimate in steady, unipolar, space-charge-limited collisional ion drift at ~`1 atm` (`760 Torr`) where Knudsen number $Kn = \lambda/d \ll 1$, ion drift speed dominates bulk airflow, and neutral collisions transfer 100% of ion momentum to gas. **Prohibition:** Must **never** extrapolate $F_{\text{ion}}(P)$ into vacuum/rarefied pressures via $\mu \propto 1/P$ or ad-hoc pressure scaling. Selecting `"rarefied_or_high_vacuum"` returns `value: null`, `status: "OUT_OF_MODEL_VALIDITY_REGIME"` with qualitative gas-density reduction note (~7.88 orders of magnitude from `760` to `10^-5 Torr`, Tajmar & Schreiber 2020). Any non-whitelisted regime or invalid/non-finite/out-of-range input fails closed (`INVALID_COMPARATOR_INPUT`, §7.2.2). |
| **`H2-WALL`** | **Chamber Wall / Enclosure Image-Charge Coupling** | **Accepted P0/P1 `grounded_box_2d` 2D benchmark analogue (`N/m`):** Side-by-side comparison of asymmetric single-ended HV (`asymmetric_hv_80mm_bench`, `-20 kV / 0 V`) vs symmetric bipolar HV (`bipolar_hv_80mm_bench`, `-10 kV / +10 kV`), plus (in live `run_v1_solver.py` mode only) a coordinated 3-point box-width sweep (`W ∈ {0.080, 0.120, 0.160} m` at pinned `n = 101`, §7.2.1). | Strictly a **case-specific 2D vacuum circular-electrode analogue (`N/m`)** for that modeled geometry and tested width range — **NOT** a general monotonicity theorem across arbitrary geometries, and **NOT** a 3D chamber force in `µN`/`N`. Offline mode locks the live sweep and compares bundled B2 snapshots only. |
| **`H2-WIRE`** | **Power-Lead Lorentz Force, Electrostatic Lead Pull & Support Reactions** | Conditional straight-wire geomagnetic Lorentz upper-bound comparator: $F_{\text{Lorentz,max}} = I_{\text{lead}} \cdot L_{\text{lead}} \cdot B_{\text{ambient}}$ (`N`).<br>*Dimensional check:* $\text{A}\cdot\text{m}\cdot\text{T} = \text{N}$.<br>*`WHAT-IF PARAMETER` inputs:* $I_{\text{lead}} \in [0, 100]\ \text{mA}$, $L_{\text{lead}} \in [0.05, 1.0]\ \text{m}$, $B_{\text{ambient}} \in [25, 65]\ \mu\text{T}$ (default $50\ \mu\text{T}$).<br>**Electrostatic lead attraction, cable stiffness hysteresis, and support reaction magnitude:** explicitly `value: null`, `status: "UNKNOWN_UNMODELED"`. | Assumes a single unshielded straight current segment perpendicular to uniform $B_{\text{ambient}}$ (ignores twisted-pair/coaxial cancellation). Provides an order-of-magnitude upper bound on magnetic lead artifacts only; does not model AC EMI, electrostatic wire sag, or mechanical feedthrough creep. |
| **`H2-DRIFT`** | **Thermal Drift, Outgassing & Instrument / Balance Systematics** | Quantitative magnitude for an uncalibrated apparatus is strictly **`value: null`, `status: "UNKNOWN_UNMODELED"`** (zero fabricated drift equations). Paired with cited peer-reviewed experimental noise/null benchmark: **Tajmar & Schreiber (2020)** (*J. Electrostat.* 107, 103477, DOI `10.1016/j.elstat.2020.103477`) reporting null force bounds down to `±0.3 mg ≈ ±3 µN` under studied high-vacuum balance configurations. | Experimental resolution and thermal-drift rates depend strictly on specific torsion/precision balance hardware, thermal shielding, pump vibration isolation, and vacuum outgassing history. Never generalized as a universal instrument floor. |

---

## 3. System-Boundary Force & Momentum-Accounting Ledgers (`Boundary A`, `B`, `C`)

V2 replaces static prose-only ledger tables with a synchronized, provenance-aware **Three-Boundary Momentum Ledger** scoped strictly to ONE active physical context at a time: (1) **`parallel_plate_1d` (`N`)**, (2) **`grounded_box_2d` (`N/m`, signed 2D `(Fx, Fy)` vectors)**, or (3) **`schematic_3d_exodus` (`PENDING_SCIENTIFIC_ACCEPTANCE`)**. Contexts and unit domains are **never mixed** in one table.

### 3.1 Boundary Definitions & Momentum-Transfer Paths

| Boundary | Physical Control Volume | Governing Conservation Statement | Momentum-Transfer Paths |
| --- | --- | --- | --- |
| **Boundary A — Device Under Test (`boundary_a_dut`)** | Suspended test assembly: high-voltage electrode(s), counter-electrode, dielectric potting (3D schematic only), and internal structural mount. | $\sum \mathbf{F}_{\text{internal}} \equiv \mathbf{0}$ (Newton III pairwise cancellation).<br>$\mathbf{F}_{\text{DUT,net}} = \oint_{\partial V_A} \mathbf{T}\cdot\hat{\mathbf{n}}\,dA + \mathbf{F}_{\text{mech,ext}} + \mathbf{F}_{\text{gas/ion}} = \mathbf{F}_{\text{external}}$. | 1. Internal electrode $\leftrightarrow$ electrode traction transmitted through structural mount (closed internally).<br>2. Internal dielectric polarization stress balanced by electrodes/mount (closed internally; 3D quantitative value `PENDING_SCIENTIFIC_ACCEPTANCE`).<br>3. External electric flux crossing $\partial V_A$ to Boundary B chamber walls.<br>4. External leads/feedthroughs or ambient gas ions crossing $\partial V_A$. |
| **Boundary B — Chamber & External Environment (`boundary_b_environment`)** | Grounded conductive vacuum chamber / enclosure walls, laboratory ground, external power leads/feedthroughs, and ambient gas (if not in high vacuum). | $\mathbf{F}_{\text{B}} = \mathbf{F}_{\text{wall,image}} + \mathbf{F}_{\text{leads,ext}} + \mathbf{F}_{\text{gas,reaction}}$. | Receives equal and opposite momentum from any unbalanced external electric flux (`enclosure_reaction` in `grounded_box_2d`), HV cable forces, or atmospheric ion-wind momentum transferred to surrounding air and chamber walls. |
| **Boundary C — Total Closed System (`boundary_c_closed`)** | Complete isolated system enclosing Boundary A + Boundary B + electromagnetic fields ($\mathbf{E}, \mathbf{B} \to \mathbf{0}$ at $\partial V_C$). | $\dfrac{d}{dt}\left(\mathbf{P}_{\text{DUT}} + \mathbf{P}_{\text{env}} + \mathbf{P}_{\text{EM,field}}\right) = \mathbf{0}$.<br>In static electrostatics ($\mathbf{B} = \mathbf{0} \implies \mathbf{P}_{\text{EM}} = \mathbf{0}$): $\mathbf{F}_{\text{A}} + \mathbf{F}_{\text{B}} = \mathbf{0}$ identically in the continuum limit. | Zero net momentum creation. Any non-zero $\mathbf{F}_{\text{net}}$ in a finite-grid 2D simulation is a **numerical discretization closure residual**, never a violation of momentum conservation. |

### 3.2 Exact Per-Context Ledger Contract & Lossless Native V1 Status Mapping (`V2-SPEC-R1-M2`)

| Ledger Row | `parallel_plate_1d` (`N`, scalar) | `grounded_box_2d` (`N/m`, signed 2D `(Fx, Fy)` vector) | `schematic_3d_exodus` (`PENDING_SCIENTIFIC_ACCEPTANCE`) |
| --- | --- | --- | --- |
| **Active / Left Electrode** | `COMPUTED_SCALAR_1D`: `value_n = force_on_positive_plate_n` (`+N`) | `COMPUTED_VECTOR_2D`: `(fx_n_per_m, fy_n_per_m, magnitude_n_per_m)` from `left_electrode_fx/fy_n_per_m` *(or lossless native withheld/rejected status below)* | `PENDING_SCIENTIFIC_ACCEPTANCE` (`value: null`; qualitative direction `+X`) |
| **Counter / Right Electrode** | `COMPUTED_SCALAR_1D`: `value_n = force_on_negative_plate_n` (`-N`) | `COMPUTED_VECTOR_2D`: `(fx_n_per_m, fy_n_per_m, magnitude_n_per_m)` from `right_electrode_fx/fy_n_per_m` | `PENDING_SCIENTIFIC_ACCEPTANCE` (`value: null`; qualitative direction `-X`) |
| **Dielectric Potting** | `NOT_APPLICABLE_VACUUM_MODEL` (`value: null`, $\varepsilon_r = 1$) | `NOT_APPLICABLE_VACUUM_MODEL` (`value: null`, $\varepsilon_r = 1$) | `PENDING_SCIENTIFIC_ACCEPTANCE` (`value: null`; `#slider-eps` is `VISUAL PROXY ONLY` / `WHAT-IF PARAMETER`) |
| **Internal Support Mount** | `UNKNOWN_UNMODELED` (`value: null`; equal & opposite static strut load required to hold gap $d$) | `UNKNOWN_UNMODELED` (`value: null`; mechanical standoffs not in 2D Laplace model) | `UNKNOWN_UNMODELED` (`value: null`; qualitative constraint reaction) |
| **Boundary A DUT Net Electrostatic Flux** | `COMPUTED_SCALAR_1D`: `value_n = net_pair_force_n = 0.0 N` (ideal infinite plates; fringing neglected) | `COMPUTED_VECTOR_2D`: signed vector sum `(left_fx + right_fx, left_fy + right_fy)` (`N/m`) — explicitly labeled **external wall-coupled DUT flux**, NOT isolated thrust | `PENDING_SCIENTIFIC_ACCEPTANCE` (`value: null`; unknown pending P2 calibrated geometry) |
| **Boundary B Enclosure / Wall Reaction** | `NOT_APPLICABLE_OPEN_1D_LIMIT` (`value: null`) | `COMPUTED_VECTOR_2D`: `(fx_n_per_m, fy_n_per_m, magnitude_n_per_m)` from `enclosure_reaction_fx/fy_n_per_m` | `PENDING_SCIENTIFIC_ACCEPTANCE` (`value: null`) |
| **Boundary B Power Leads & Gas/Ion Coupling** | `UNKNOWN_UNMODELED` (`value: null`) | `UNKNOWN_UNMODELED` (`value: null`) | `UNKNOWN_UNMODELED` (`value: null`; see conditional H2 comparators) |
| **Boundary C Numerical Closure Residual** | `COMPUTED_SCALAR_1D`: `value_n = 0.0 N` (exact analytic cancellation) | `COMPUTED_RESIDUAL_2D`: signed `(net_fx_n_per_m, net_fy_n_per_m)`, `norm_n_per_m`, `relative_closure_residual`, `tolerance_n_per_m = 1e-4`, `is_force_balanced_to_tolerance` (strict `<`), `force_closure_status` (`BALANCED_WITHIN_TOLERANCE` vs `UNBALANCED_EXCEEDS_TOLERANCE`) — explicitly labeled **DISCRETIZATION RESIDUAL, NOT THRUST** | `PENDING_SCIENTIFIC_ACCEPTANCE` (`value: null`) |
| **Whole-Body Propellantless Thrust** | `NOT MEASURED / NOT ESTABLISHED` | `NOT MEASURED / NOT ESTABLISHED` | `NOT MEASURED / NOT ESTABLISHED` |

**Lossless Native V1 Adapter Status, Error Mapping & Primary-vs-Study Provenance Separation (`V2-SPEC-R1-M2`, `V2-SPEC-R2-L1`, `V2-SPEC-R3-M1`):** V2 preserves native V1 status, error codes, and native `{ n, reason }` study-failure records verbatim without collapsing distinct failure modes or dropping diagnostic reasons, AND strictly separates **primary-grid force-budget provenance** (`source_scope: "primary_force_budget"`) from **multi-grid convergence-study provenance** (`source_scope: "convergence_study"`):

| Native V1 Response / Error Condition | HTTP Status | Native V1 Field / Code | V2 `source_scope` | Exact V2 Status Mapping | `native_v1_code` Preserved |
| --- | --- | --- | --- | --- | --- |
| Valid 2D primary force budget returned | `200` | `force_budget_status: "COMPUTED"` | `"primary_force_budget"` | `COMPUTED_VECTOR_2D` / `COMPUTED_RESIDUAL_2D` | `"COMPUTED"` |
| Post-solve primary snapped-contour topology gate failed (`force_budget: null`) | `200` | `force_budget_status: "WITHHELD_INVALID_CONTOUR_TOPOLOGY"` | `"primary_force_budget"` | `WITHHELD_INVALID_CONTOUR_TOPOLOGY` (`value: null`) | `"WITHHELD_INVALID_CONTOUR_TOPOLOGY"` |
| Primary grid ineligible during `/api/v1/study` (`force_budget: null`) | `200` | `force_budget_status: "WITHHELD_INELIGIBLE_PRIMARY_GRID"` | `"primary_force_budget"` | `WITHHELD_INELIGIBLE_PRIMARY_GRID` (`value: null`) | `"WITHHELD_INELIGIBLE_PRIMARY_GRID"` |
| Pre-solve grid-resolved domain eligibility rejected (`/api/v1/solve`) | `400` | `error.code: "INVALID_FORCE_DOMAIN"` | `"primary_force_budget"` | `REJECTED_INVALID_FORCE_DOMAIN` (`value: null`) | `"INVALID_FORCE_DOMAIN"` |
| Multi-grid `/api/v1/study` coarse level ineligible or invalid topology (independent of primary grid!) | `200` | `force_study.status: "WITHHELD_INELIGIBLE_MESH_LEVEL"` / `"WITHHELD_INVALID_CONTOUR_TOPOLOGY"`, `force_study.failed_levels: [{ n, reason }, ...]`, `rows: []`, `derived_sensitivity: null` | `"convergence_study"` (`convergence_study_provenance` record) | `WITHHELD_INELIGIBLE_MESH_LEVEL` / `WITHHELD_INVALID_CONTOUR_TOPOLOGY` (`value: null`, native `failed_levels: StudyFailedLevelRecord[]` preserving every `{ n, reason }` verbatim, `rows: []`, `derived_sensitivity: null`) — **MUST NOT overwrite or clear computed primary-grid `force_budget` rows** | Exact native `force_study.status` |
| Schema/transport/worker/offline-lookup/retry-exhaustion error (`400`/`408`/`413`/`415`/`429`/`500`/`503`/`504`, `HTTP_429_RETRY_EXHAUSTED`, `NETWORK_ERROR`, `MALFORMED_JSON`, `IDENTITY_MISMATCH`, `OFFLINE_SNAPSHOT_UNAVAILABLE`) | `4xx` / `5xx` / `null` | `error.code` or client error code | `"primary_force_budget"` | `UNAVAILABLE_SOLVER_ERROR` (`value: null`) | Exact native `error.code` |
| Invalidation / pending request / transport-epoch mismatch (`V2-SPEC-R2-M1`, `V2-SPEC-R3-M2`) / Chapter 5 wave mode active | N/A | `solveState: "pending" \| "idle"`, `TRANSPORT_EPOCH_MISMATCH`, or `activeViewContext: "scalar_wave_contrast"` | `"primary_force_budget"` | `CLEARED_PENDING_OR_INACTIVE` (`value: null`) | N/A |

**Simultaneous Primary-Grid + Withheld-Study Invariant (`V2-SPEC-R2-L1`, `V2-SPEC-R3-M1`):** Accepted `v1_solver_adapter.py::_run_gated_studies()` (lines 1129–1197) can return `force_budget_status: "COMPUTED"` (valid signed primary-grid `N/m` vectors, e.g. at primary `n = 101`, `box_width_m = 0.160 m`) **simultaneously** with `force_study: { status: "WITHHELD_INELIGIBLE_MESH_LEVEL", study_n_list: [41, 81, 101], failed_levels: [{ n: 41, reason: "Electrode radius min(0.007, 0.007) < 3h (0.012 m) at n=41" }], rows: [], derived_sensitivity: null }` (or `"WITHHELD_INVALID_CONTOUR_TOPOLOGY"` with native `{ n, reason }` topology diagnostics) in the **same HTTP `200` response**. V2 MUST populate primary ledger rows exclusively from `resp.force_budget` / `resp.force_budget_status` under `source_scope: "primary_force_budget"` (preserving all valid signed `(fx_n_per_m, fy_n_per_m)` `N/m` vectors and closure residual) while recording `resp.force_study` / `resp.force_mesh_sensitivity_status` exclusively inside the independent `convergence_study_provenance` record (`source_scope: "convergence_study"`, `value: null`, native `failed_levels: StudyFailedLevelRecord[]` preserving every `{ n, reason }` diagnostic verbatim without collapsing to `number[]`, `rows: []`, `derived_sensitivity: null`, and **zero** fabricated numerical study rows or `0.0` placeholders).

---

## 4. Established-Physics Reference Comparators (Validity-Bounded)

To help beginners calibrate intuition about force magnitudes without fabricating unverified propulsion claims, V2-B includes two strictly textbook **Reference Comparators** (`epistemic_class: "ESTABLISHED_MODEL"` with `WHAT-IF PARAMETER` labels on user-selected exploratory inputs), kept visually distinct from H0 electrostatic stress and H1 patent claims:

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

## 5. Discriminating Null-Control Matrix (`V2-SPEC-R1-M5` Qualified)

V2-B presents an interactive **Null-Control Laboratory** covering six mandatory experimental controls, each with explicit predictions, observables, assumptions, and limitations. Simulated 2D `N/m` model behavior is strictly separated from real 3D laboratory `µN` balance measurements:

| Control ID | Experimental Manipulation | Observable & SI Unit | `H0` Conventional Prediction | `H1` Patent Hypothesis Prediction | `H2` Confounder Signature | Key Assumptions & Limitations |
| --- | --- | --- | --- | --- | --- | --- |
| **`NC-VAC`** | **Vacuum Pressure Sweep** (`760 Torr` $\to$ `< 10^-5 Torr`) | Balance force $F_x(P)$ (`µN`), leakage current $I(P)$ (`µA`), pressure $P$ (`Torr` / `Pa`) | $F_{\text{propellantless}} = 0$; air/ion-wind artifacts vanish as gas density drops `~7.9` orders of magnitude; residual wall/lead forces persist if unshielded. | Purported vacuum electrostatic effect should persist at `< 10^-5 Torr` (exact $P$-dependence not derived in US11511891B2). | Corona ion wind & air convection collapse sharply below Paschen / rarefied transition; outgassing jets may spike transiently during pumpdown. | High vacuum suppresses gas collisions but does **not** eliminate chamber image charges, HV cable forces, thermal radiation recoil, or outgassing bursts. |
| **`NC-POL`** | **Voltage Polarity Inversion** (`+V` vs `-V` and `0 V` null) | Force asymmetry $\Delta F = F(+V) - F(-V)$ (`µN`) and $F(V)$ vs $V^2$ fit | Pure Maxwell electrostatic traction is strictly even in voltage ($F \propto V^2$, $\Delta F = 0$); `0 V` yields $0$. | Eq. (11) scales with $E^2 \propto V^2$ (even in $V$, $\Delta F = 0$); polarity-dependent net shift would contradict pure $E^2$ scaling. | Unipolar corona onset asymmetry (negative vs positive Trichel/streamer thresholds), trapped dielectric charge, and DC Lorentz lead force ($F \propto I \times B$) change sign or magnitude under polarity flip. | Requires matched $|+V| = |-V|$ supply stability and full dielectric discharge/rest period between runs to avoid trapped-charge hysteresis. |
| **`NC-FLIP`** | **180° Physical Orientation Flip** on Torsion Balance Arm | Lab-frame force $F_{\text{lab}}(\theta = 0^\circ)$ vs $F_{\text{lab}}(\theta = 180^\circ)$ (`µN`) | Zero true device-fixed thrust ($F_{\text{device}} = 0$); lab-fixed environmental drifts remain invariant. | Genuine device-fixed thrust must invert cleanly in lab coordinates: $F_{\text{lab}}(180^\circ) = -F_{\text{lab}}(0^\circ)$. | Thermal room gradients, floor tilt, pump vibration, and fixed feedthrough drag do **not** invert cleanly; chamber-wall asymmetry may change if device is off-center. | Must maintain identical center-of-mass position, cable routing, and wall clearances before and after the 180° flip. |
| **`NC-WALL`** | **Chamber Wall Clearance Sweep** (increase distance to grounded shield) | Measured balance force $F_x(d_{\text{wall}})$ (`µN`) with uncertainty $\pm \sigma_F$ (`µN`) vs enclosure clearance $d_{\text{wall}}$ (`m`) *(separate from 2D `N/m` simulation analogue)* | In the distant-wall limit ($d_{\text{wall}} \to \infty$), external electrostatic wall coupling vanishes ($F_{\text{wall}} \to 0$). *Separate 2D model analogue:* for the single verified 2D `asymmetric_hv_80mm_bench` geometry at `n = 101` across `W ∈ {0.080, 0.120, 0.160} m`, simulated `enclosure_reaction_fx_n_per_m` decays monotonically (`8.38e-2 → 1.96e-2 → 8.43e-3 N/m`); this is a **case-specific 2D numerical trend**, not a universal monotonicity theorem across arbitrary 3D geometries. | Internal-only claimed thrust should remain invariant within experimental uncertainty once grounded walls are far enough away that external field coupling is negligible. | A measured reduction in `µN` force as grounded chamber walls move farther away — **after** controlling radiative thermal view factors, pumping conductance, and cable routing and exceeding measurement uncertainty — is **consistent with** Boundary A $\leftrightarrow$ B capacitive image-charge coupling (not uniquely diagnostic by itself). | Moving walls can simultaneously alter thermal radiation view factors, vacuum pumping conductance, stray magnetic shielding, and feedthrough geometry; wall-sweep evidence must be combined with thermal/dummy/isolation controls (`NC-DUMMY`, `NC-ISO`) and full uncertainty propagation. Never equate 2D `N/m` sweep values with 3D `µN` apparatus measurements. |
| **`NC-DUMMY`** | **Symmetrical / Zero-Asymmetry Dummy Load Control** (same mass, $V$, power dissipation, capacitance, and leads) | Force difference $F_{\text{asym}} - F_{\text{dummy}}$ (`µN`) | Both symmetric dummy and isolated asymmetric DUT produce zero propellantless thrust; any residual matches shared thermal/wire/EMI systematics. | Symmetric dummy has $E_1^2 A_1 = E_2^2 A_2 \implies F_{\text{H1,dummy}} = 0$, whereas asymmetric DUT should depart above combined uncertainty. | Nonzero force on symmetric dummy exposes Joule heating thermal convection/outgassing, HV lead pull, balance EMI pickup, or power-supply recoil. | Dummy must match heat dissipation spatial profile, total HV capacitance, and surface area to avoid differential outgassing. |
| **`NC-ISO`** | **Self-Contained Battery & Wireless Telemetry Isolation** (zero external HV/power leads crossing Boundary A) | Net force $F_{\text{isolated}}$ (`µN`) with on-board HV multiplier and optical/RF telemetry | Eliminates external wire Lorentz/electrostatic forces crossing Boundary A; isolated DUT net force equals remaining chamber/radiation/outgassing coupling only. | True propellantless thrust must persist without external power leads crossing Boundary A. | Force disappearance when external HV feedthroughs are removed identifies lead-wire Lorentz/electrostatic artifacts. | On-board battery/inverter adds mass (reducing torsion-balance sensitivity) and internal heat dissipation (requiring thermal-drift monitoring). |

---

## 6. Beginner-Friendly 3D Visualization Behavior & Progressive Disclosure

V2 preserves the accepted V0.2 nonblocking 3-panel Iceberg architecture and V1 Solver tab, adding a dedicated **Force Story (V2)** experience without visual clutter or regressions:

1. **Progressive Disclosure (Iceberg Depth):**
   - *Surface (Default):* Plain-English cards answering *"Which parts pull on each other, what pulls on the outer chamber, and why does the total stay balanced?"* with color-coded Boundary A (cyan dashed control-volume shell), Boundary B (amber chamber-wall ring/highlight), and Boundary C (closed-system badge).
   - *Shallow (`V2-SPEC-R1-M1` Segregated Surfaces):*
     - **Surface A (Qualitative 3D Exodus DUT Hypotheses):** Side-by-side qualitative **H0 vs H1 vs H2** cards for the provisional 3D Exodus schematic (`3D H0: PENDING_SCIENTIFIC_ACCEPTANCE`, `3D H1: PUBLISHED HYPOTHESIS / PENDING_SCIENTIFIC_ACCEPTANCE`, `H2: competing laboratory confounders`), with zero 1D/2D P0/P1 numbers mixed in.
     - **Surface B (Separate Quantitative P0/P1 Benchmark Analogue):** Separate bannered card summarizing the active 1D (`N`) or 2D (`N/m`) conventional electrostatic closed-boundary balance as a distinct benchmark geometry (never labeled as a 3D Exodus prediction).
   - *Deeper (`<details>`):* Accessible semantic HTML equations (zero raw LaTeX delimiters `\frac`, `\nabla`, `\varepsilon`, `\propto`), dimensional checks, US11511891B2 Eq. (4)/Eq. (11) audit ledger, Scientific Charter crosswalk, and H2 validity assumptions.
   - *Research (`<details>`):* Full 6-control Null-Control Matrix, Tajmar & Schreiber (2020) reference bounds, and P2 blocking status (`PENDING_SCIENTIFIC_ACCEPTANCE`).
2. **Strict Visual Separation Rules:**
   - **3D Schematic Mode (`PROVISIONAL_ILLUSTRATIVE_SCENE`):** Optional Boundary A / Boundary B visual highlight toggle outlines the suspended DUT vs grounded chamber walls in the existing Three.js viewport. **Zero** 2D `N/m` or 1D `N` numerical vectors are ever attached to the 3D Exodus knife-edge mesh.
   - **2D Computed Benchmark Mode (`ESTABLISHED_MODEL`):** Reuses the dedicated `#v1-2d-viewport` cross-section canvas (with 3D `forceGroup` hidden) and adds an optional **Boundary A / B / C contour overlay** visually tracing the exact accepted P1 `c_left`, `c_right`, and `c_enclosure_inner` closed integration paths alongside the 6-component signed `N/m` ledger.
   - **Chapter 5 Scalar-Wave Contrast (`MATHEMATICAL TOY (ISOLATED)`):** Strictly inherits PR #28's `V1-B3-POLISH-R1-M1` isolation invariant — whenever Chapter 5 scalar-wave contrast is active, all V2 Force Story live solver/sweep triggers and V1 1D/2D panels are hidden/disabled, zero `/api/v1/solve` or `/api/v1/study` traffic can fire, and explicit mode transitions silently exit wave contrast via `{ silentV1Notify: true }`.

---

## 7. Implementation Design Contracts (`V2-A` & `V2-B`)

V2 implementation will proceed only **after** independent V2-Spec acceptance (`0 HIGH, 0 MEDIUM`) and separate owner authorization, split into two reviewable slices:

### 7.1 Slice `V2-A` — H0/H1/H2 Comparison, System-Boundary Momentum Ledgers & V1 State Synchronization

- **Scope:**
  - Read-only V2 data/UI modules (`explorer/v2_force_story_data.js` + `explorer/v2_force_story_ui.js`) plus minimal additive read-only observer hook in `explorer/v1_solver_ui.js` (§7.1.1).
  - Interactive **Surface A (Qualitative 3D DUT H0/H1/H2)** and **Surface B (Separate Quantitative P0/P1 Analogue)** views (`role="tablist"` / `role="radiogroup"`), synchronized Three-Boundary Force & Momentum Ledger (`Boundary A / B / C`) with signed 2D `(Fx, Fy)` vectors (`N/m`), 1D scalars (`N`), and 3D `PENDING_SCIENTIFIC_ACCEPTANCE`, plus optional 3D Boundary A/B highlight overlay and 2D P1 contour-path overlay.
  - Zero new backend HTTP endpoints; zero changes to `electrostatics_baseline.py`, `electrostatics_numerics.py`, `v1_worker_bridge.py`, `v1_solver_adapter.py`, `run_explorer.py`, `run_v1_solver.py`, or B2 snapshots.

#### 7.1.1 Explicit V1 → V2 State Synchronization, Transport Epoch & Pending-Transition Settlement Contract (`V2-SPEC-R1-M3`, `V2-SPEC-R2-M1`, `V2-SPEC-R3-M2`)

Accepted `window.__v1SolverUI` currently exposes `getState()` (containing `activeModelMode`, `activeViewContext`, `activeEndpoint`, `transportMode`, `solveState`, `clientStateGeneration`, `currentCanonicalFingerprint`, `latestDispatchedRequestId`, `isComputed2DActive`, and `lastRenderedResponse`), with **no** push subscription API, and accepted `setTransportMode(mode)` (`explorer/v1_solver_ui.js` lines 1455–1459) mutates `transportMode` and calls `syncTransportUI()` without invalidating `lastRenderedResponse`, incrementing `clientStateGeneration`, aborting pending requests, or changing `solveState`. Slice V2-A must **not** assume an undocumented emitter, must **not** retroactively relabel a previous live response as an offline snapshot (or vice versa), must **never** strand V1 in a permanent `solveState === "pending"` state when transport changes mid-request, and must **preserve** accepted PR #28 V1 semantics outside this narrowly defined integration:

1. **Minimal Additive Read-Only Observer & Transport-Origin Metadata on `window.__v1SolverUI`:**
   - Extend `window.__v1SolverUI.getState()` with three read-only fields:
     - `lastError: { code: string, message: string, httpStatus: number | null } | null` (reset to `null` inside `invalidatePending()` and `renderVerifiedResponse()`, populated inside `handleCurrentError()`).
     - `transportEpoch: number` (initialized to `0`; incremented synchronously by `+1` whenever `transportMode` actually changes — `nextMode !== transportMode` — inside `setTransportMode(mode)`, `enterOfflineModeAndRender()`, and the `v1-btn-retry-live` click handler, **immediately before** calling `syncTransportUI()`).
     - `lastRenderedOrigin: { transportMode: "live" | "offline", transportEpoch: number } | null` (captured at `dispatchCurrentRequest()` into `captured.transportMode` and `captured.transportEpoch`, stamped synchronously inside `renderVerifiedResponse(captured, resp)`, and reset to `null` inside `invalidatePending()` and `handleCurrentError()`).
   - Extend `isCapturedCurrent(captured)` in `explorer/v1_solver_ui.js` with `captured.transportMode === transportMode && captured.transportEpoch === transportEpoch` so any in-flight live/offline response returning after a transport transition is rejected by the shared staleness gate.
   - Add `window.__v1SolverUI.subscribe(listener)` returning `unsubscribe()`. V1 notifies registered listeners synchronously **immediately after** committing its own state inside `invalidatePending()`, `renderVerifiedResponse()`, `handleCurrentError()`, and `syncTransportUI()`, passing `{ eventType: "invalidate" | "ready" | "error" | "transport", state: window.__v1SolverUI.getState() }`.
   - Listener invocation is wrapped in `try { listener(evt); } catch (_err) {}` so a V2 subscriber can never disrupt V1 execution.
2. **Deterministic Pending-Transition Cancellation & State-Settlement Rule (`V2-SPEC-R3-M2`):**
   - Because `isCapturedCurrent(captured)` rejects any delayed response or error whose captured `(transportMode, transportEpoch)` no longer matches current state, leaving `solveState === "pending"` during a transport transition without cancellation or replacement dispatch would strand V1's pending badge and `#v1-2d-canvas-status` (`"Computing validated 2D P0/P1 solution..."`) indefinitely. Every transport-changing path MUST therefore obey a deterministic settlement rule:
     - **Direct `window.__v1SolverUI.setTransportMode(nextMode)` when `nextMode !== transportMode`:**
       1. Preempt any active V2-B external sweep synchronously (`onPreempt()`) and clear `preemptedSweepAtMs = null`.
       2. Commit `transportMode = nextMode` and increment `transportEpoch += 1`.
       3. **Pending-Work Settlement Barrier:** If V1 has any active pending work (`solveState === "pending" || debounceTimerId !== null || activeAbortController !== null || v1RetryTimerId !== null`), synchronously invoke `invalidatePending(activeModelMode, activeViewContext, null, "idle")` — incrementing `clientStateGeneration`, clearing `debounceTimerId` and `v1RetryTimerId`, aborting `activeAbortController`, clearing `lastRenderedResponse`/`lastRenderedOrigin`/`lastError`/readouts/error banner/2D canvas, transitioning `solveState` via `setSolveStateUI("idle")` (hiding the computing status overlay — **zero permanent pending state**), and emitting `{ eventType: "invalidate", state }` to V2 subscribers.
       4. Invoke `syncTransportUI()` (updating transport badges/controls and emitting `{ eventType: "transport", state }`).
       5. When NO pending work exists (`solveState` is `"ready"`, `"error"`, or `"idle"` with no active timers/controllers), step 3 is skipped so accepted PR #28 non-pending `setTransportMode()` behavior in V1 remains untouched while V2's 8-predicate transport-epoch gate synchronously clears stale V2 numeric rows.
     - **Automatic Live → Offline Fallback (`enterOfflineModeAndRender(endpointToRun)`):** Preempts any external sweep, commits `transportMode = "offline"`, increments `transportEpoch += 1`, calls `syncTransportUI()`, then invokes `invalidatePending(activeModelMode, targetView, endpointToRun || "/api/v1/solve", "pending")` and immediately dispatches `dispatchCurrentRequest()` (which executes `executeOfflineRequest(captured)` synchronously under the new `transportEpoch` and settles `solveState` immediately to `"ready"` or `"error"`).
     - **User `Retry Live` Action (`#v1-btn-retry-live` click handler):** Preempts any external sweep, commits `transportMode = "live"`, increments `transportEpoch += 1`, calls `syncTransportUI()`; if `activeModelMode !== "schematic_3d" && !isScalarWaveViewActive()`, dispatches a verified replacement request via `scheduleV1Request("/api/v1/solve", true)` under the new `transportEpoch`; otherwise, if any pending V1 state existed, settles synchronously via `invalidatePending(activeModelMode, activeViewContext, null, "idle")`.
     - **Delayed Response / Error Arrival After Transport Change:** When an aborted or in-flight pre-transition HTTP `200` OR HTTP `500`/network error eventually resolves after the transport transition, `isCapturedCurrent(captured)` returns `false` (failing both `clientStateGeneration` and `transportMode`/`transportEpoch`), so V1 discards the obsolete completion silently (zero stale values, zero obsolete error banner, zero mutation away from `"idle"` or the newer verified state) and V2 remains cleanly cleared until a verified response publishes under the new `(transportMode, transportEpoch)`.
3. **Pull-on-Mount + 8-Predicate Atomic Identity & Transport-Origin Validation in V2:**
   - On DOM initialization, V2 pulls initial state synchronously via `window.__v1SolverUI.getState()` and registers its `subscribe()` callback.
   - V2 renders `COMPUTED_SCALAR_1D`, `COMPUTED_VECTOR_2D`, or `COMPUTED_RESIDUAL_2D` ledger rows **if and only if ALL eight atomic predicates hold** on the received `state`:
     1. `state.solveState === "ready"`
     2. `state.lastRenderedResponse !== null`
     3. `state.lastRenderedResponse.request_id === state.latestDispatchedRequestId`
     4. `state.lastRenderedResponse.input_fingerprint === state.currentCanonicalFingerprint`
     5. `(state.activeModelMode === "parallel_plate_1d" && state.activeViewContext === "v1_1d") || (state.activeModelMode === "grounded_box_2d" && state.activeViewContext === "v1_2d")`
     6. `state.clientStateGeneration >= lastRenderedV2Generation` (monotonically non-decreasing; V2 never retains cached solver payloads across generation bumps)
     7. `state.lastRenderedOrigin !== null`
     8. `state.lastRenderedOrigin.transportMode === state.transportMode && state.lastRenderedOrigin.transportEpoch === state.transportEpoch` (exact transport-origin & epoch parity — prevents any prior-transport response from rendering under a new transport mode).
   - **Immediate Synchronous Stale-Ledger & Transport-Change Clearing Barrier (`V2-SPEC-R2-M1`, `V2-SPEC-R3-M2`):** Whenever `eventType === "invalidate"`, `eventType === "transport"` with mismatched `(transportMode, transportEpoch)` (e.g. direct `setTransportMode("offline")` or `setTransportMode("live")` without dispatching a new request), `state.solveState === "pending"`, `state.solveState === "idle"`, `state.activeViewContext === "scalar_wave_contrast"`, or **any** of the 8 atomic predicates fails, V2 **immediately and synchronously clears** all numeric `COMPUTED_*` cells (rendering `CLEARED_PENDING_OR_INACTIVE` / `"—"`, with `reason_code: "TRANSPORT_EPOCH_MISMATCH"` on transport transitions, or the appropriate schematic/wave view). V2 updates its transport badge truthfully to `state.transportMode` and **never** displays or retroactively relabels a prior live response as an offline snapshot (or a prior offline snapshot as a live result) until a fresh verified response publishes under the new `(transportMode, transportEpoch)`.
   - **Lossless Error Mapping & Primary-vs-Study Separation (`V2-SPEC-R2-L1`, `V2-SPEC-R3-M1`):** Whenever `state.solveState === "error"`, V2 clears all `COMPUTED_*` cells and maps `state.lastError.code` directly per §3.2 (`INVALID_FORCE_DOMAIN` → `REJECTED_INVALID_FORCE_DOMAIN`; other codes including `HTTP_429_RETRY_EXHAUSTED` → `UNAVAILABLE_SOLVER_ERROR` preserving `native_v1_code`). Whenever `state.solveState === "ready"` passes all 8 predicates for a `/api/v1/study` response, V2 populates primary force-ledger rows (`source_scope: "primary_force_budget"`) strictly from `resp.force_budget` / `resp.force_budget_status` and records `resp.force_study` / `resp.force_mesh_sensitivity_status` separately in `convergence_study_provenance` (`source_scope: "convergence_study"`, preserving native `failed_levels: { n, reason }[]` verbatim).

### 7.2 Slice `V2-B` — Competing-Mechanism Comparators, Coordinated Live Clearance Sweep & Null-Control Laboratory

- **Scope:**
  - Pure-Python + JS parity-tested comparator module (`v2_comparators.py` + JS mirror in `explorer/v2_force_story_ui.js`) implementing `evaluate_h2_ion_wind_atmospheric`, `evaluate_h2_lorentz_lead_bound`, `evaluate_ref_photon_recoil`, and `evaluate_ref_ion_exhaust` under strict fail-closed validation (§7.2.2).
  - Interactive 6-control Null-Control Laboratory (§5).
  - Live `H2-WALL` 3-point chamber-clearance sweep (`W ∈ {0.080, 0.120, 0.160} m` on `asymmetric_hv_80mm_bench` geometry, fixed electrodes `cx = ±0.015 m`, `r = 0.007 m`, `-20 kV / 0 V`, pinned strictly to `n = 101` — empirically verified against accepted `v1_solver_adapter.py` to pass V1 Section 3.1/3.2 gates with `BALANCED_WITHIN_TOLERANCE` `< 1e-4 N/m` at all three widths and case-specific enclosure reaction decay `8.38e-2 → 1.96e-2 → 8.43e-3 N/m`; `n = 41` is ineligible at `W = 0.160 m` because `r < 3h`, and `n = 81` at `W = 0.160 m` yields `UNBALANCED_EXCEEDS_TOLERANCE` `8.01e-4 N/m`).

#### 7.2.1 Global Single-Slot Backend Concurrency, Preemption & Shared Bounded `429` Recovery (`V2-SPEC-R1-M4`, `V2-SPEC-R2-M2`)

Because the local solver server enforces a **single shared backend compute slot** (`max_concurrent_computes = 1`, returning HTTP `429` on overlap, and `503 WORKER_UNAVAILABLE_POISONED` taking strict precedence over `429`) and because aborting a browser `fetch` via `AbortController.abort()` does **not** guarantee the Python child worker has already finished or released `_compute_lock`, V2-B enforces symmetric client-side global arbitration plus bounded `429` recovery in **both** transition directions (`V1 → V2 sweep` AND `V2 sweep → preempting V1 request`):

1. **Shared Client-Side Request Arbitration (Last User Intent Wins — Mutually Exclusive):**
   - `window.__v1SolverUI` exposes a narrow additive coordination helper (`beginExternalSweepCoordination(onPreempt)` / `endExternalSweepCoordination()`):
     - *When V2-B starts a live 3-point sweep:* V1 synchronously runs `invalidatePending(activeModelMode, activeViewContext, null, "idle")` (clearing any pending V1 debounce timer, any pending post-preemption V1 retry timer, and aborting any in-flight V1 `fetch`), increments `v2SweepGeneration += 1`, sets `v2SweepState = "running"`, and registers `onPreempt`.
     - *When ANY V1/Explorer user transition occurs during an active sweep* (V1 slider edit, preset/grid change, `Run Convergence Study`, `setMode()`, chapter switch, `Explore Freely`, Chapter 5 wave toggle, or `Retry Live`/offline transition): V1 invokes `onPreempt()` **synchronously before** scheduling its own work. `onPreempt()` immediately increments `v2SweepGeneration += 1`, calls `sweepAbortController.abort()`, clears any pending sweep `429` backoff retry timer (`clearTimeout`), sets `v2SweepState = "cancelled"`, and returns `hadInFlightSweepFetch: boolean` indicating whether an HTTP sweep step was actually in flight when aborted.
2. **V2 Sweep Sequential Step Dispatch & Bounded `429` Retry Policy (`V1 → V2` Transition):**
   - Sweep steps `k ∈ {0, 1, 2}` (`W = 0.080, 0.120, 0.160 m`) dispatch strictly sequentially (`step k+1` never starts before `step k` resolves and passes `capturedSweepGen === v2SweepGeneration`).
   - If step `k` receives HTTP **`429`** (e.g., a recently aborted V1 solve/study is still finishing inside the Python worker's `_compute_lock`):
     - Re-check `capturedSweepGen === v2SweepGeneration && !isScalarWaveViewActive() && transportMode === "live"`. If false, discard silently.
     - Retry up to **`max_retries_per_step = 3`** using deterministic backoff delays **`[250, 500, 1000] ms`** (hard per-step retry deadline `2000 ms`; timer handle stored and cleared immediately on `onPreempt()` / cancel).
     - Before issuing each retry `fetch`, re-check `capturedSweepGen === v2SweepGeneration && !isScalarWaveViewActive() && transportMode === "live"`.
3. **Shared Admission & Bounded `429` Recovery for V1-After-V2-Preemption (`V2 → V1` Transition, `V2-SPEC-R2-M2`):**
   - **Strict Scoping (Zero Silent Change to Normal Non-Sweep V1 Behavior):** `v1_solver_ui.js` tracks a single internal timestamped marker `preemptedSweepAtMs: number | null` set to `Date.now()` **only** when `onPreempt()` reports `hadInFlightSweepFetch === true`. Under normal non-sweep V1 operation (`preemptedSweepAtMs === null` or expired `Date.now() - preemptedSweepAtMs > 5000`), accepted PR #28 V1 behavior is **completely unchanged**: HTTP `429` proceeds immediately to `handleCurrentError()` with `0` retries.
   - **Armed Post-Preemption Recovery Window:** When `dispatchCurrentRequest()` dispatches a live V1 request while `preemptedSweepAtMs !== null && Date.now() - preemptedSweepAtMs <= 5000`, it stamps `captured.allowPostPreempt429Recovery = true`, `captured.retryAttempt = 0`, and `captured.retryDeadlineMs = Date.now() + 2000` (finite budget: **`max_v1_post_preempt_retries = 3`**, deterministic backoff **`[250, 500, 1000] ms`**, hard wall-clock deadline **`2000 ms`** from initial dispatch, single tracked timer handle `v1RetryTimerId`).
   - **Staleness-First, Fail-Closed Recovery Rules:**
     - On every response, V1 evaluates `isCapturedCurrent(captured)` (`gen === clientStateGeneration && fp === currentCanonicalFingerprint && mode === activeModelMode && view === activeViewContext && reqId === latestDispatchedRequestId && transportMode === captured.transportMode && transportEpoch === captured.transportEpoch`) **first** before parsing, retrying, or displaying errors.
     - On HTTP **`503`** (`WORKER_UNAVAILABLE_POISONED`, `SERVER_SHUTTING_DOWN`, `WORKER_STARTUP_FAILED`, `WORKER_CRASHED`): **zero retries**; clear `preemptedSweepAtMs = null` and call `handleCurrentError(captured, errCode, errMsg)` immediately.
     - On HTTP **`429`** when `captured.allowPostPreempt429Recovery === true`:
       - If `captured.retryAttempt < 3` AND `Date.now() + backoffMs[captured.retryAttempt] <= captured.retryDeadlineMs`: increment `captured.retryAttempt += 1`, keep `solveState === "pending"` (preserving cleared V1 readouts and cleared V2 ledger), and schedule `v1RetryTimerId = setTimeout(...)`. When the timer fires, re-check `isCapturedCurrent(captured) && !isScalarWaveViewActive() && transportMode === "live"` **before** re-issuing `fetch` (reusing `captured.reqId`, `captured.fp`, `captured.gen`, `captured.transportEpoch` with a fresh `AbortController` assigned to `activeAbortController`).
       - If retries or the `2000 ms` deadline are exhausted: clear `preemptedSweepAtMs = null` and report an honest terminal error via `handleCurrentError(captured, "HTTP_429_RETRY_EXHAUSTED", "Solver remained busy after preempting an earlier clearance sweep (finite retries exhausted). Please retry.")` — never loop indefinitely and never restore stale numbers.
     - **Synchronous Cancellation on Superseding Intent:** `invalidatePending()` MUST synchronously execute `clearTimeout(v1RetryTimerId); v1RetryTimerId = null;` so any newer V1 slider/preset/study/mode/chapter/wave/transport action immediately cancels a pending post-preemption backoff retry (`0` extra fetches for the superseded intent). Transitions to `schematic_3d` or `scalar_wave_contrast` also clear `preemptedSweepAtMs = null`.
     - **Settlement Disarm:** On HTTP `200`, static offline fallback, or any non-`429` error, clear `preemptedSweepAtMs = null`.
4. **Fail-Closed `503` Precedence, Explicit Partial-Result Semantics & Offline Fallback (V2 Sweep):**
   - On HTTP **`503`** (`WORKER_UNAVAILABLE_POISONED`), **zero retries** are performed; sweep halts immediately with `sweep_status: "PARTIAL_ABORTED_POISONED"`.
   - On exhausted `429` retries, sweep halts immediately with `sweep_status: "PARTIAL_ABORTED_BUSY"`.
   - On any `400`/`408`/`500`/`504`/network/JSON/identity-mismatch error, sweep halts immediately with `sweep_status: "PARTIAL_ABORTED_ERROR"`.
   - On static HTTP fallback (`501`/`405`/`404` non-JSON or `V1_A_TRANSPORT_ONLY`), sweep halts immediately, switches V1/V2 to `transportMode = "offline"` (incrementing `transportEpoch`), locks the live sweep button (`SOLVER BRIDGE OFFLINE`), and displays the bundled B2 offline preset comparison.
   - **Partial-Result Truthfulness Rule:** Whenever `sweep_status !== "COMPLETED"`, already-finished steps may remain visible **explicitly labeled `PARTIAL SWEEP — INCOMPLETE`**, every unexecuted/failed step records `status: "NOT_RUN_SWEEP_TERMINATED"` (`value: null`), and V2 **withholds** any multi-point decay summary or completed-trend badge!

#### 7.2.2 Fail-Closed Comparator Input Validation Contract (`V2-SPEC-R1-L2`, Python & JS Parity)

All four V2-B comparator functions in `v2_comparators.py` and their JS mirror in `explorer/v2_force_story_ui.js` MUST enforce identical strict, non-coercing validation (matching V1-B2's non-coercing numeric standard):

| Comparator Function | Required Parameters & Exact Closed SI Bounds | Strict Type / Whitelist / Failure Rules |
| --- | --- | --- |
| `evaluate_h2_ion_wind_atmospheric(current_a, gap_m, mobility_m2_per_vs, pressure_regime)` | `current_a ∈ [0.0, 5.0e-4]` (`A`), `gap_m ∈ [5.0e-3, 1.0e-1]` (`m`), `mobility_m2_per_vs ∈ [1.2e-4, 2.5e-4]` (`m²/(V·s)`), `pressure_regime ∈ {"atmospheric_1atm_collisional", "rarefied_or_high_vacuum"}` | Reject `bool`, `None`/`null`/`undefined`, strings for numbers, objects/arrays, `NaN`, `±Infinity` → `status: "INVALID_COMPARATOR_INPUT"`, `value: null`, `reason_code: "NON_FINITE_OR_TYPE_ERROR"`.<br>Any `pressure_regime` not in the 2-item whitelist (empty string, unknown string, numeric pressure, `null`, `bool`) → `status: "INVALID_COMPARATOR_INPUT"`, `value: null`, `reason_code: "UNSUPPORTED_PRESSURE_REGIME"`.<br>Out-of-bounds numeric input (including `< 0`, `mobility <= 0`, or above max) → `status: "INVALID_COMPARATOR_INPUT"`, `value: null`, `reason_code: "OUT_OF_RANGE"`.<br>When `pressure_regime == "rarefied_or_high_vacuum"` AND numeric inputs are valid → `status: "OUT_OF_MODEL_VALIDITY_REGIME"`, `value: null`, `reason_code: "COLLISIONAL_DRIFT_INVALID_IN_VACUUM"` (if numeric inputs are invalid even under rarefied selector, return `INVALID_COMPARATOR_INPUT` first).<br>When valid + atmospheric: exact `0.0 N` at `current_a == 0.0`; Python/JS parity tolerance `max(1e-15, 1e-12 * max(|js|, |py|))`. |
| `evaluate_h2_lorentz_lead_bound(current_a, length_m, b_field_t)` | `current_a ∈ [0.0, 1.0e-1]` (`A`), `length_m ∈ [5.0e-2, 1.0]` (`m`), `b_field_t ∈ [2.5e-5, 6.5e-5]` (`T`) | Identical strict non-coercing type/finiteness (`NON_FINITE_OR_TYPE_ERROR`) and closed-range (`OUT_OF_RANGE`) fail-closed returns (`value: null`); exact `0.0 N` at `current_a == 0.0`. |
| `evaluate_ref_photon_recoil(power_w)` | `power_w ∈ [0.0, 1.0e3]` (`W`), `c = 299792458.0 m/s` | Identical strict fail-closed validation (`NON_FINITE_OR_TYPE_ERROR` / `OUT_OF_RANGE`, `value: null`); exact `0.0 N` at `power_w == 0.0`. |
| `evaluate_ref_ion_exhaust(beam_current_a, accel_voltage_v, ion_mass_kg)` | `beam_current_a ∈ [0.0, 1.0e-1]` (`A`), `accel_voltage_v ∈ [1.0e2, 5.0e3]` (`V`), `ion_mass_kg ∈ [1.67e-27, 4.0e-25]` (`kg`), `q_i = 1.602176634e-19 C` | Identical strict fail-closed validation (`NON_FINITE_OR_TYPE_ERROR` / `OUT_OF_RANGE`, `value: null`, rejecting `<= 0` mass or voltage); exact `0.0 N` at `beam_current_a == 0.0`. |

### 7.3 Typed Schema Contracts (Exhaustive Discriminated Unions — `V2-SPEC-R1-M2`, `L1`, `L2`; `V2-SPEC-R2-M1`, `L1`; `V2-SPEC-R3-M1`)

```ts
type EpistemicClass =
  | "ESTABLISHED_MODEL"
  | "PUBLISHED_HYPOTHESIS"
  | "CONDITIONAL_CONFOUNDER_MODEL"
  | "EXPERIMENTAL_MEASUREMENT"
  | "PROVISIONAL_ILLUSTRATIVE_SCENE"
  | "TOY_MATHEMATICAL_ILLUSTRATION"
  | "UNVERIFIED_PENDING_P2";

type ScientificCharterCategory =
  | "ESTABLISHED MODEL"
  | "PUBLISHED HYPOTHESIS"
  | "WHAT-IF PARAMETER"
  | "EXPERIMENTAL MEASUREMENT"
  | "UNVERIFIED NUMERICAL OUTPUT";

type UnitDomain = "N" | "N/m" | "NONE";

type NullableUncertainty = {
  status: "BOUNDED" | "NUMERICAL_RESIDUAL_ONLY" | "NOT_ASSESSED" | "UNBOUNDED_UNKNOWN";
  value: number | null;
  unit: UnitDomain;
  note: string;
};

type LedgerRowValue =
  | {
      status: "COMPUTED_SCALAR_1D";
      value_n: number;                 // finite IEEE-754 float64 in N (parallel_plate_1d only)
      unit: "N";
      uncertainty: NullableUncertainty;
    }
  | {
      status: "COMPUTED_VECTOR_2D";
      fx_n_per_m: number;              // signed finite IEEE-754 float64 in N/m (grounded_box_2d only)
      fy_n_per_m: number;              // signed finite IEEE-754 float64 in N/m
      magnitude_n_per_m: number;       // hypot(fx, fy) >= 0 in N/m
      unit: "N/m";
      uncertainty: NullableUncertainty;
    }
  | {
      status: "COMPUTED_RESIDUAL_2D";
      net_fx_n_per_m: number;          // signed residual x component (N/m)
      net_fy_n_per_m: number;          // signed residual y component (N/m)
      norm_n_per_m: number;            // >= 0 discrete closure norm (N/m)
      relative_closure_residual: number | null;
      tolerance_n_per_m: 1e-4;
      is_force_balanced_to_tolerance: boolean; // strict norm_n_per_m < 1e-4
      force_closure_status: "BALANCED_WITHIN_TOLERANCE" | "UNBALANCED_EXCEEDS_TOLERANCE";
      unit: "N/m";
    }
  | {
      status: "CONDITIONAL_ESTIMATE";
      value_n: number;                 // finite IEEE-754 float64 in N
      unit: "N";
      validity_regime: string;
      assumptions: string[];
      what_if_parameters: string[];    // Charter WHAT-IF PARAMETER disclosure
    }
  | {
      status: "WITHHELD_INVALID_CONTOUR_TOPOLOGY";
      value: null;                     // NEVER 0.0
      http_status: 200;
      native_v1_code: "WITHHELD_INVALID_CONTOUR_TOPOLOGY";
      diagnostic: string;
    }
  | {
      status: "REJECTED_INVALID_FORCE_DOMAIN";
      value: null;                     // NEVER 0.0
      http_status: 400;
      native_v1_code: "INVALID_FORCE_DOMAIN";
      diagnostic: string;
    }
  | {
      status: "WITHHELD_INELIGIBLE_PRIMARY_GRID";
      value: null;                     // NEVER 0.0
      http_status: 200;
      native_v1_code: "WITHHELD_INELIGIBLE_PRIMARY_GRID";
      diagnostic: string;
    }
  | {
      status: "WITHHELD_INELIGIBLE_MESH_LEVEL"; // Permitted ONLY when source_scope === "convergence_study"
      value: null;                     // NEVER 0.0; NEVER overwrites primary_force_budget rows
      http_status: 200;
      native_v1_code: "WITHHELD_INELIGIBLE_MESH_LEVEL";
      failed_levels: StudyFailedLevelRecord[]; // V2-SPEC-R3-M1: lossless native { n, reason }[] records
      diagnostic: string;
    }
  | {
      status: "UNAVAILABLE_SOLVER_ERROR";
      value: null;                     // NEVER 0.0
      http_status: number | null;
      native_v1_code: string;
      diagnostic: string;
    }
  | {
      status:
        | "UNKNOWN_UNMODELED"
        | "OUT_OF_MODEL_VALIDITY_REGIME"
        | "INVALID_COMPARATOR_INPUT"
        | "NOT_APPLICABLE_VACUUM_MODEL"
        | "NOT_APPLICABLE_OPEN_1D_LIMIT"
        | "CLEARED_PENDING_OR_INACTIVE"
        | "NOT_RUN_SWEEP_TERMINATED";
      value: null;                     // NEVER 0.0
      reason_code: string;
      note: string;
    }
  | {
      status: "PENDING_SCIENTIFIC_ACCEPTANCE";
      value: null;                     // NEVER 0.0
      blocking_gate: "TRACK_B_P2";
      note: string;
    };

type StudyFailedLevelRecord = {
  n: number;                           // Native integer grid level from v1_solver_adapter._run_gated_studies()
  reason: string;                      // Native eligibility or contour-topology diagnostic preserved verbatim
};

type LedgerRowSourceScope =
  | "primary_force_budget"
  | "convergence_study"
  | "comparator_estimate"
  | "qualitative_3d_dut"
  | "null_control_sweep";

type ConvergenceStudyStatusRecord =
  | {
      source_scope: "convergence_study";
      status: "NOT_REQUESTED";
      force_mesh_sensitivity_status: "NOT_ASSESSED";
      study_n_list: null;
      failed_levels: [];
      rows: [];
      derived_sensitivity: null;
      value: null;
    }
  | {
      source_scope: "convergence_study";
      status: "STABLE_WITHIN_STUDY_TOLERANCE" | "SENSITIVE_OR_UNBALANCED";
      force_mesh_sensitivity_status: "STABLE_WITHIN_STUDY_TOLERANCE" | "SENSITIVE_OR_UNBALANCED";
      study_n_list: number[];
      failed_levels: [];
      observed_order_status: "NOT_COMPUTED_NONUNIFORM_H_RATIO" | string;
    }
  | {
      source_scope: "convergence_study";
      status: "WITHHELD_INELIGIBLE_MESH_LEVEL" | "WITHHELD_INVALID_CONTOUR_TOPOLOGY";
      force_mesh_sensitivity_status: "WITHHELD_INELIGIBLE_MESH_LEVEL" | "WITHHELD_INVALID_CONTOUR_TOPOLOGY";
      study_n_list: number[];
      failed_levels: StudyFailedLevelRecord[]; // V2-SPEC-R3-M1: lossless native [{ n, reason }] verbatim
      rows: [];                        // Native empty array; NEVER synthesize numeric study rows
      derived_sensitivity: null;       // Native null; NEVER coerce to 0.0
      native_v1_code: "WITHHELD_INELIGIBLE_MESH_LEVEL" | "WITHHELD_INVALID_CONTOUR_TOPOLOGY";
      value: null;                     // NEVER 0.0; NEVER overwrites primary_force_budget rows
    };

interface ForceLedgerRow {
  row_id: string;
  source_scope: LedgerRowSourceScope;  // V2-SPEC-R2-L1: primary_force_budget rows NEVER overwritten by study status
  boundary: "boundary_a_dut" | "boundary_b_environment" | "boundary_c_closed";
  component_label: string;
  epistemic_class: EpistemicClass;
  charter_categories: ScientificCharterCategory[];
  quantity: LedgerRowValue;
  qualitative_direction: string;
  source_citation: string;
}

interface ForceLedgerSnapshot {
  schema_version: "v2.0";
  comparison_surface: "qualitative_3d_dut_hypotheses" | "quantitative_p0_p1_analogues";
  context_id: "parallel_plate_1d" | "grounded_box_2d" | "schematic_3d_exodus";
  unit_domain: UnitDomain;
  transport_mode: "live" | "offline" | "static_schematic";
  sync_identity: {
    client_state_generation: number;
    transport_epoch: number;                              // V2-SPEC-R2-M1
    response_origin_transport: "live" | "offline" | null; // V2-SPEC-R2-M1: must match transport_mode when computed
    input_fingerprint: string | null;
    request_id: number | null;
  };
  convergence_study_provenance: ConvergenceStudyStatusRecord | null; // V2-SPEC-R2-L1: independent of primary rows
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

### 7.4 Accessibility, Responsive Layout & Required Automated Test Suites

1. **Desktop & Mobile Layout:** Verified at desktop `1280×860` and mobile `375×812` & `390×844` with `document.documentElement.scrollWidth - window.innerWidth <= 1` (`0 px` target overflow), readable wrapping for all ledger tables and null-control cards, and preserved 3D viewport visibility at the top of mobile screens.
2. **Keyboard & ARIA Accessibility:** Full keyboard reachability (`Tab`, `Enter`/`Space`, arrow keys on tablists/radiogroups), accurate `aria-selected` / `aria-checked` / `aria-expanded` / `aria-disabled` states, `aria-live="polite"` status announcements, and zero raw LaTeX delimiters in rendered DOM.
3. **Required Automated Test Suites (Implementation Phase — Pending Spec Acceptance + Owner Kickoff):**
   - **`tests/test_v2_force_story_contracts.py` (Python + Node/JS parity):**
     - **Cross-Geometry Non-Conflation (`V2-SPEC-R1-M1`):** Assert Surface A (`qualitative_3d_dut_hypotheses`) contains zero computed 1D (`N`) or 2D (`N/m`) P0/P1 numbers and marks both 3D H0 and 3D H1 quantitative slots `PENDING_SCIENTIFIC_ACCEPTANCE`; assert Surface B explicitly banners separate idealized benchmark geometry and never emits shared-apparatus H1 numeric claims.
     - **Typed Schema, Lossless V1 Mapping & Primary-vs-Study Provenance Tests (`V2-SPEC-R1-M2`, `V2-SPEC-R2-L1`, `V2-SPEC-R3-M1`):** Reject scalar-only `value` on 2D vector rows; reject 2D vector rows omitting signed `fx_n_per_m` / `fy_n_per_m`; reject numeric `0.0` on any `null`-value status (`UNKNOWN_UNMODELED`, `PENDING_SCIENTIFIC_ACCEPTANCE`, `OUT_OF_MODEL_VALIDITY_REGIME`, `INVALID_COMPARATOR_INPUT`, `WITHHELD_INVALID_CONTOUR_TOPOLOGY`, `WITHHELD_INELIGIBLE_PRIMARY_GRID`, `WITHHELD_INELIGIBLE_MESH_LEVEL`, `REJECTED_INVALID_FORCE_DOMAIN`); reject cross-unit (`N` + `N/m`) aggregation; reject lossy `failed_levels: [41]` number-only arrays lacking `{ n, reason }`; verify lossless 1-to-1 preservation of native V1 `WITHHELD_INVALID_CONTOUR_TOPOLOGY`, `WITHHELD_INELIGIBLE_PRIMARY_GRID`, `INVALID_FORCE_DOMAIN`, and `WITHHELD_INELIGIBLE_MESH_LEVEL`; **simultaneous primary/study provenance test (`V2-SPEC-R2-L1`, `V2-SPEC-R3-M1`)**: feed an actual adapter-shaped HTTP `200` `/api/v1/study` payload generated by `v1_solver_adapter.py` (`n = 101`, `box_width_m = 0.160 m`, `asymmetric_hv_80mm_bench` electrodes, `study_n_list = [41, 81, 101]`) where `force_budget_status: "COMPUTED"` (valid signed primary-grid `N/m` vectors: `left_electrode_fx_n_per_m ≈ +6.711e-2`, `right_electrode_fx_n_per_m ≈ -7.561e-2`, `enclosure_reaction_fx_n_per_m ≈ +8.426e-3`, `BALANCED_WITHIN_TOLERANCE`) AND `force_study: { status: "WITHHELD_INELIGIBLE_MESH_LEVEL", study_n_list: [41, 81, 101], failed_levels: [{ n: 41, reason: "Electrode radius min(0.007, 0.007) < 3h (0.012 m) at n=41" }], rows: [], derived_sensitivity: null }` (plus an analogous `WITHHELD_INVALID_CONTOUR_TOPOLOGY` fixture with native `{ n, reason }` records), and assert: (a) all primary-grid `COMPUTED_VECTOR_2D` / `COMPUTED_RESIDUAL_2D` rows remain preserved under `source_scope: "primary_force_budget"`, (b) `convergence_study_provenance` independently records `status: "WITHHELD_INELIGIBLE_MESH_LEVEL"`, `source_scope: "convergence_study"`, `value: null`, `rows: []`, `derived_sensitivity: null`, and exact verbatim `failed_levels: [{ n: 41, reason: "Electrode radius min(0.007, 0.007) < 3h (0.012 m) at n=41" }]`, and (c) zero fabricated numeric study rows or `0.0` placeholders exist.
     - **Charter Crosswalk (`V2-SPEC-R1-L1`):** Assert every `EpistemicClass` maps cleanly to valid `ScientificCharterCategory[]` and every conditional comparator output carries non-empty `what_if_parameters` and `"WHAT-IF PARAMETER"` charter disclosure.
     - **Comparator Parity & Complete Fail-Closed Negative Matrix (`V2-SPEC-R1-L2`):** Verify exact Python-vs-JS numeric parity (`max(1e-15, 1e-12 * max(|js|, |py|))`) at boundary extrema and `0.0` current/power across all 4 comparators; verify fail-closed `value: null` (`INVALID_COMPARATOR_INPUT` / `OUT_OF_MODEL_VALIDITY_REGIME`) in **both** Python and JS for `pressure_regime = "rarefied_or_high_vacuum"`, unknown regime strings (`""`, `"low_vacuum"`, `"760"`, `null`, `true`), `NaN`, `+Inf`, `-Inf`, negative inputs, zero mobility/mass, above-max inputs, booleans (`true`/`false`), and numeric strings (`"10"`).
     - **Cryptographic Baseline & P2 Isolation:** Assert unchanged git blob SHA-1 for `electrostatics_baseline.py`, `electrostatics_numerics.py`, and `docs/V1_SOLVER_INTEGRATION_SPEC.md`, `--check-committed` snapshot parity, and **zero** Track B P2 (`exodus_hypothesis_evaluator`, `exodus_patent_geometry`, `p2_`) imports.
   - **`tests/test_v2_browser_smoke.py` (Playwright — Desktop `1280×860`, Mobile `375×812` & `390×844`):**
     - **V2-A Sync, Bidirectional Transport-Epoch Clearing, Pending-Transition Settlement & Identity (`V2-SPEC-R1-M1`, `M2`, `M3`; `V2-SPEC-R2-M1`, `L1`; `V2-SPEC-R3-M1`, `M2`):**
       - Verify `window.__v1SolverUI.subscribe()` + `getState()` 8-predicate atomic sync across slider edits (immediate synchronous V2 ledger clear before `150 ms` debounce), mode switches (`1D → 2D → 3D`), chapter changes, `Explore Freely`, live→offline fallback, current `400 INVALID_FORCE_DOMAIN` / `200 WITHHELD_INVALID_CONTOUR_TOPOLOGY` / `500` error mapping, and delayed stale `200`/`500` responses never repopulating a cleared V2 ledger.
       - **Bidirectional Direct Transport-Switch Adversarial Tests — Ready State (`V2-SPEC-R2-M1`):** (a) Ready live 2D ledger → direct `window.__v1SolverUI.setTransportMode("offline")` with zero request dispatch → assert V2 numeric ledger clears synchronously (`CLEARED_PENDING_OR_INACTIVE`, `TRANSPORT_EPOCH_MISMATCH`), zero prior live numbers remain labeled as offline snapshots, and ledger stays cleared until a verified offline snapshot publishes under the new `transportEpoch`; (b) reverse direction: ready offline 2D ledger → direct `window.__v1SolverUI.setTransportMode("live")` with zero request dispatch → assert V2 numeric ledger clears synchronously and never presents an offline snapshot as a live result until a verified live response publishes under the new `transportEpoch`.
       - **Pending-Request Transport-Transition Settlement Adversarial Tests (`V2-SPEC-R3-M2`):** (a) **Live → offline during pending request + delayed HTTP `200`:** start a delayed live 2D `/api/v1/solve` or `/api/v1/study` (`solveState === "pending"`), invoke direct `window.__v1SolverUI.setTransportMode("offline")` (zero replacement dispatch), assert BOTH V1 (`solveState === "idle"`, `#v1-2d-canvas-status` hidden, readouts cleared) and V2 (`CLEARED_PENDING_OR_INACTIVE`) settle synchronously, then release the delayed HTTP `200` and assert zero stale values render and V1 does NOT remain pending; (b) **Live → offline during pending request + delayed HTTP `500`/network error:** repeat with a delayed `500`/network failure and assert zero obsolete error banner renders and V1 stays cleanly `"idle"`; (c) **Offline → live during pending work (both delayed `200` and delayed error, plus `#v1-btn-retry-live` click and automatic fallback `enterOfflineModeAndRender`):** assert synchronous cancellation/settlement with zero stale values, zero obsolete error banners, and zero permanently pending state; (d) assert accepted non-transport V1 behavior remains unchanged.
       - Verify signed `(Fx, Fy)` display in `N/m`, simultaneous `COMPUTED` primary + `WITHHELD_INELIGIBLE_MESH_LEVEL` study UI preserving primary signed vectors while displaying verbatim native `{ n, reason }` study withholding separately (`V2-SPEC-R2-L1`, `V2-SPEC-R3-M1`), `UNBALANCED_EXCEEDS_TOLERANCE` coarse `n=41` banner never labeled thrust, zero 2D `N/m` arrows on 3D Exodus blade, and Surface A/B strict non-conflation.
     - **V2-B Global Concurrency, Bidirectional Preemption Recovery & Scientific Framing (`V2-SPEC-R1-M4`, `M5`, `L2`; `V2-SPEC-R2-M2`):**
       - **V1 → V2 Sweep Concurrency (`V2-SPEC-R1-M4`):** (a) V1 slider/study traffic immediately preceding V2 sweep causing transient `429` → bounded backoff retry succeeds; (b) sustained `429` exhausting `max_retries_per_step = 3` → deterministic `PARTIAL_ABORTED_BUSY` with unrun steps `null` and trend summary withheld; (c) `503 WORKER_UNAVAILABLE_POISONED` → immediate stop with `0` retries; (d) mid-sweep preemption via V1 mode/slider/study/chapter/Chapter 5 wave toggle → synchronous cancel, `0` stray sweep fetches past `240 ms`, delayed step responses discarded; (e) mid-sweep offline fallback transition.
       - **V2 Sweep → Preempting V1 Recovery (`V2-SPEC-R2-M2` — Actual-Worker & Delayed-Worker Tests):** (a) Active V2 sweep holds Python `_compute_lock` → preempting V1 slider/preset/study action hits transient `429`, bounded V1 post-preemption retry recovers once slot releases, and latest V1 intent renders truthfully in both V1 and V2 ledgers; (b) superseding newer V1 intent (or Chapter 5 wave / 3D schematic switch) during post-preemption retry backoff synchronously cancels the pending retry timer (`0` extra fetches for superseded intent); (c) persistent `429` past finite retry budget / `2000 ms` deadline terminates honestly with `HTTP_429_RETRY_EXHAUSTED` (no infinite loop, V2 ledger stays cleared); (d) `503 WORKER_UNAVAILABLE_POISONED` during preemption recovery fails closed immediately with `0` retries; (e) normal non-sweep V1 `429` (no prior sweep preemption) fails immediately with `0` retries, preserving accepted PR #28 V1 semantics.
       - Verify `NC-WALL` DOM text strictly qualifies the 3-point 2D sweep as a case-specific `N/m` model trend, never asserts universal monotonicity or unique identification of measured `µN` wall coupling, and never equates `N/m` with `µN`.
       - Verify `H2-ION` atmospheric calculation vs high-vacuum `OUT_OF_MODEL_VALIDITY_REGIME` (`value: null`), `H2-WIRE` & reference comparators, 6-control Null-Control Lab keyboard navigation, and truthful `file://` / static `http.server` offline fallback.
     - **Preservation & Isolation:** Chapter 5 scalar-wave isolation (`> 200 ms` post-debounce zero `/api/v1/solve` & `/api/v1/study` checks across V2 triggers), zero console/page errors, `<= 1 px` mobile overflow at `375px` & `390px`, and full `229`-test V0/V0.1/V0.2/V1/P0/P1 suite passing without regression.

---

## 8. Independent Review Acceptance Criteria (V2 Spec R4)

This specification is ready for independent ChatGPT acceptance when:

1. All 7 R1 findings (`V2-SPEC-R1-M1`–`M5`, `L1`, `L2`), all 3 R2 findings (`V2-SPEC-R2-M1`, `M2`, `L1`), AND both R3 findings (`V2-SPEC-R3-M1`, `V2-SPEC-R3-M2`) are closed cleanly without weakening any of the 8 mandatory scientific constraints in Section 1.
2. Surface A (qualitative 3D Exodus DUT hypotheses) and Surface B (separate quantitative 1D/2D P0/P1 analogues) never imply shared geometry or conflate units (`N` vs `N/m` vs `PENDING_SCIENTIFIC_ACCEPTANCE`).
3. Typed ledger schemas represent signed 2D `(Fx, Fy)` vectors cleanly without scalar coercion, preserve native V1 `WITHHELD_INVALID_CONTOUR_TOPOLOGY` / `INVALID_FORCE_DOMAIN` / `WITHHELD_INELIGIBLE_PRIMARY_GRID` / `WITHHELD_INELIGIBLE_MESH_LEVEL` statuses losslessly, separate `source_scope: "primary_force_budget"` from independent `convergence_study_provenance` preserving native `{ n, reason }` `StudyFailedLevelRecord[]` diagnostics verbatim (`V2-SPEC-R2-L1`, `V2-SPEC-R3-M1`), and reject `0.0` coercion of unknowns or fabricated study rows.
4. V1 → V2 synchronization enforces all 8 atomic identity predicates including `transportEpoch` & `lastRenderedOrigin`, deterministically cancels/settles pending V1 work on transport transitions without permanent pending states or stale delayed completions (`V2-SPEC-R2-M1`, `V2-SPEC-R3-M2`); global single-slot concurrency covers both `V1 → V2` sweep retries and narrowly scoped `V2 → V1` post-preemption bounded `429` recovery with fail-closed `503` precedence (`V2-SPEC-R2-M2`); `NC-WALL` inference, Charter 5-category crosswalk, and fail-closed Python/JS comparator validation are completely and testably specified.
5. Frozen P0/P1 kernels, accepted V1 Spec R5, accepted V1 baselines, and Track B P2 (`Draft PR #11`) remain untouched; Track B remains at `2 of 5` accepted scientific gates; whole-body thrust remains `NOT MEASURED / NOT ESTABLISHED`.
6. **Independent Review Verdict:** `0 HIGH, 0 MEDIUM` findings on this specification, followed by separate explicit owner authorization before opening any V2-A or V2-B implementation branch.
