# V2 Design Specification — Whole-Device Force Story (Revision R2 — Draft for Independent Re-Review)

**Status:** **IN PROGRESS — DRAFT R2 SPECIFICATION FOR INDEPENDENT RE-REVIEW (NOT YET INDEPENDENTLY ACCEPTED, NOT IMPLEMENTED, NOT MERGED).**  
**Tracking Issue:** [Issue #30](https://github.com/aguacatero/scalar-wave-viz/issues/30) (`V2 — Whole-Device Force Story`)  
**Draft PR:** [PR #31](https://github.com/aguacatero/scalar-wave-viz/pull/31) (`OPEN`, `draft`, unmerged)  
**Specification Branch:** `feat/v2-whole-device-force-story-spec`  
**Prior Reviewed R1 SHA & Governing Review:** `453f7840461c7f2d1de1c2515421cc6df7c075a6` — [ChatGPT Independent R1 Review #6059541798](https://github.com/aguacatero/scalar-wave-viz/pull/31#pullrequestreview-6059541798) (`REVISE — 0 HIGH, 5 MEDIUM, 2 LOW`; remediating `V2-SPEC-R1-M1`, `M2`, `M3`, `M4`, `M5`, `L1`, `L2`)  
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

**Lossless Native V1 Adapter Status & Error Mapping (`V2-SPEC-R1-M2`):** V2 preserves native V1 status and error codes verbatim without collapsing distinct failure modes into a single generic label:

| Native V1 Response / Error Condition | HTTP Status | Native V1 Field / Code | Exact V2 `LedgerRowValue.status` | `native_v1_code` Preserved |
| --- | --- | --- | --- | --- |
| Valid 2D force budget returned | `200` | `force_budget_status: "COMPUTED"` | `COMPUTED_VECTOR_2D` / `COMPUTED_RESIDUAL_2D` | `"COMPUTED"` |
| Post-solve snapped-contour topology gate failed (`potential_v` succeeded, `force_budget: null`) | `200` | `force_budget_status: "WITHHELD_INVALID_CONTOUR_TOPOLOGY"` | `WITHHELD_INVALID_CONTOUR_TOPOLOGY` (`value: null`) | `"WITHHELD_INVALID_CONTOUR_TOPOLOGY"` |
| Pre-solve grid-resolved domain eligibility rejected (`/api/v1/solve`) | `400` | `error.code: "INVALID_FORCE_DOMAIN"` | `REJECTED_INVALID_FORCE_DOMAIN` (`value: null`) | `"INVALID_FORCE_DOMAIN"` |
| Primary grid ineligible during `/api/v1/study` (`force_budget: null`) | `200` | `force_budget_status: "WITHHELD_INELIGIBLE_PRIMARY_GRID"` | `WITHHELD_INELIGIBLE_PRIMARY_GRID` (`value: null`) | `"WITHHELD_INELIGIBLE_PRIMARY_GRID"` |
| Multi-grid `/api/v1/study` coarse level ineligible or invalid topology | `200` | `force_study.status: "WITHHELD_INELIGIBLE_MESH_LEVEL"` / `"WITHHELD_INVALID_CONTOUR_TOPOLOGY"` | `WITHHELD_INELIGIBLE_MESH_LEVEL` / `WITHHELD_INVALID_CONTOUR_TOPOLOGY` (`value: null`) | Exact native `force_study.status` |
| Schema/transport/worker/offline-lookup error (`400`/`408`/`413`/`415`/`429`/`500`/`503`/`504`, `NETWORK_ERROR`, `MALFORMED_JSON`, `IDENTITY_MISMATCH`, `OFFLINE_SNAPSHOT_UNAVAILABLE`) | `4xx` / `5xx` / `null` | `error.code` or client error code | `UNAVAILABLE_SOLVER_ERROR` (`value: null`) | Exact native `error.code` |
| Invalidation / pending request / Chapter 5 wave mode active | N/A | `solveState: "pending" \| "idle"` or `activeViewContext: "scalar_wave_contrast"` | `CLEARED_PENDING_OR_INACTIVE` (`value: null`) | N/A |

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

#### 7.1.1 Explicit V1 → V2 State Synchronization & Atomic Identity Contract (`V2-SPEC-R1-M3`)

Accepted `window.__v1SolverUI` currently exposes `getState()` (containing `activeModelMode`, `activeViewContext`, `activeEndpoint`, `transportMode`, `solveState`, `clientStateGeneration`, `currentCanonicalFingerprint`, `latestDispatchedRequestId`, `isComputed2DActive`, and `lastRenderedResponse`), with **no** push subscription API. Slice V2-A must **not** assume an undocumented emitter and must **not** alter V1's accepted request/invalidation/DOM semantics:

1. **Minimal Additive Read-Only Observer Hook on `window.__v1SolverUI`:**
   - Extend `window.__v1SolverUI.getState()` with read-only `lastError: { code: string, message: string, httpStatus: number | null } | null` (reset to `null` inside `invalidatePending()` and `renderVerifiedResponse()`, populated inside `handleCurrentError()`).
   - Add `window.__v1SolverUI.subscribe(listener)` returning `unsubscribe()`. V1 notifies registered listeners synchronously **immediately after** committing its own state inside `invalidatePending()`, `renderVerifiedResponse()`, `handleCurrentError()`, and `syncTransportUI()`, passing `{ eventType: "invalidate" | "ready" | "error" | "transport", state: window.__v1SolverUI.getState() }`.
   - Listener invocation is wrapped in `try { listener(evt); } catch (_err) {}` so a V2 subscriber can never disrupt V1 execution. With zero subscribers, V1 behavior is byte-for-byte identical to accepted PR #28.
2. **Pull-on-Mount + Atomic Identity Validation in V2:**
   - On DOM initialization, V2 pulls initial state synchronously via `window.__v1SolverUI.getState()` and registers its `subscribe()` callback.
   - V2 renders `COMPUTED_SCALAR_1D`, `COMPUTED_VECTOR_2D`, or `COMPUTED_RESIDUAL_2D` ledger rows **if and only if ALL six atomic predicates hold** on the received `state`:
     1. `state.solveState === "ready"`
     2. `state.lastRenderedResponse !== null`
     3. `state.lastRenderedResponse.request_id === state.latestDispatchedRequestId`
     4. `state.lastRenderedResponse.input_fingerprint === state.currentCanonicalFingerprint`
     5. `(state.activeModelMode === "parallel_plate_1d" && state.activeViewContext === "v1_1d") || (state.activeModelMode === "grounded_box_2d" && state.activeViewContext === "v1_2d")`
     6. `state.clientStateGeneration >= lastRenderedV2Generation` (monotonically non-decreasing; V2 never retains cached solver payloads across generation bumps).
   - **Immediate Synchronous Stale-Ledger Clearing:** Whenever `eventType === "invalidate"`, `state.solveState === "pending"`, `state.solveState === "idle"`, `state.activeViewContext === "scalar_wave_contrast"`, or any atomic predicate fails, V2 **immediately clears** all numeric `COMPUTED_*` cells (rendering `CLEARED_PENDING_OR_INACTIVE` / `"—"` or the appropriate schematic/wave view) so V2 can never display an older solver ledger after a slider edit, mode switch, chapter change, `Explore Freely`, wave toggle, or offline switch.
   - **Lossless Error Mapping:** Whenever `state.solveState === "error"`, V2 clears all `COMPUTED_*` cells and maps `state.lastError.code` directly per §3.2 (`INVALID_FORCE_DOMAIN` → `REJECTED_INVALID_FORCE_DOMAIN`; other codes → `UNAVAILABLE_SOLVER_ERROR` preserving `native_v1_code`).

### 7.2 Slice `V2-B` — Competing-Mechanism Comparators, Coordinated Live Clearance Sweep & Null-Control Laboratory

- **Scope:**
  - Pure-Python + JS parity-tested comparator module (`v2_comparators.py` + JS mirror in `explorer/v2_force_story_ui.js`) implementing `evaluate_h2_ion_wind_atmospheric`, `evaluate_h2_lorentz_lead_bound`, `evaluate_ref_photon_recoil`, and `evaluate_ref_ion_exhaust` under strict fail-closed validation (§7.2.2).
  - Interactive 6-control Null-Control Laboratory (§5).
  - Live `H2-WALL` 3-point chamber-clearance sweep (`W ∈ {0.080, 0.120, 0.160} m` on `asymmetric_hv_80mm_bench` geometry, fixed electrodes `cx = ±0.015 m`, `r = 0.007 m`, `-20 kV / 0 V`, pinned strictly to `n = 101` — empirically verified against accepted `v1_solver_adapter.py` to pass V1 Section 3.1/3.2 gates with `BALANCED_WITHIN_TOLERANCE` `< 1e-4 N/m` at all three widths and case-specific enclosure reaction decay `8.38e-2 → 1.96e-2 → 8.43e-3 N/m`; `n = 41` is ineligible at `W = 0.160 m` because `r < 3h`, and `n = 81` at `W = 0.160 m` yields `UNBALANCED_EXCEEDS_TOLERANCE` `8.01e-4 N/m`).

#### 7.2.1 Global Single-Slot Backend Concurrency, Preemption & Bounded `429` Contract (`V2-SPEC-R1-M4`)

Because the local solver server enforces a **single shared backend compute slot** (`max_concurrent_computes = 1`, returning HTTP `429` on overlap, and `503 WORKER_UNAVAILABLE_POISONED` taking strict precedence over `429`) and because aborting a browser `fetch` via `AbortController` does **not** guarantee the Python child worker has already finished or released `_compute_lock`, V2-B enforces explicit client-side global arbitration plus bounded `429` handling:

1. **Shared Client-Side Request Arbitration (Last User Intent Wins — Mutually Exclusive):**
   - `window.__v1SolverUI` exposes a narrow additive coordination helper (`beginExternalSweepCoordination(onPreempt)` / `endExternalSweepCoordination()`):
     - *When V2-B starts a live 3-point sweep:* V1 synchronously runs `invalidatePending(activeModelMode, activeViewContext, null, "idle")` (clearing any pending V1 debounce timer and aborting any in-flight V1 `fetch`), increments `v2SweepGeneration += 1`, sets `v2SweepState = "running"`, and registers `onPreempt`.
     - *When ANY V1/Explorer user transition occurs during an active sweep* (V1 slider edit, preset/grid change, `Run Convergence Study`, `setMode()`, chapter switch, `Explore Freely`, Chapter 5 wave toggle, or `Retry Live`/offline transition): V1 invokes `onPreempt()` **synchronously before** scheduling its own work. `onPreempt()` immediately increments `v2SweepGeneration += 1`, calls `sweepAbortController.abort()`, clears any pending `429` backoff retry timer (`clearTimeout`), sets `v2SweepState = "cancelled"`, and prevents any further sweep step from firing.
2. **Sequential Step Dispatch & Bounded `429` Retry Policy (Handling Outstanding Worker Compute After Abort):**
   - Sweep steps `k ∈ {0, 1, 2}` (`W = 0.080, 0.120, 0.160 m`) dispatch strictly sequentially (`step k+1` never starts before `step k` resolves and passes `capturedSweepGen === v2SweepGeneration`).
   - If step `k` receives HTTP **`429`** (e.g., a recently aborted V1 solve/study is still finishing inside the Python worker's `_compute_lock`):
     - Re-check `capturedSweepGen === v2SweepGeneration && !isScalarWaveViewActive() && transportMode === "live"`. If false, discard silently.
     - Retry up to **`max_retries_per_step = 3`** using deterministic backoff delays **`[250, 500, 1000] ms`** (maximum retry wait `1750 ms` per step; timer handle stored and cleared immediately on `onPreempt()` / cancel).
     - Before issuing each retry `fetch`, re-check `capturedSweepGen === v2SweepGeneration && !isScalarWaveViewActive() && transportMode === "live"`.
3. **Fail-Closed `503` Precedence, Explicit Partial-Result Semantics & Offline Fallback:**
   - On HTTP **`503`** (`WORKER_UNAVAILABLE_POISONED`), **zero retries** are performed; sweep halts immediately with `sweep_status: "PARTIAL_ABORTED_POISONED"`.
   - On exhausted `429` retries, sweep halts immediately with `sweep_status: "PARTIAL_ABORTED_BUSY"`.
   - On any `400`/`408`/`500`/`504`/network/JSON/identity-mismatch error, sweep halts immediately with `sweep_status: "PARTIAL_ABORTED_ERROR"`.
   - On static HTTP fallback (`501`/`405`/`404` non-JSON or `V1_A_TRANSPORT_ONLY`), sweep halts immediately, switches V1/V2 to `transportMode = "offline"`, locks the live sweep button (`SOLVER BRIDGE OFFLINE`), and displays the bundled B2 offline preset comparison.
   - **Partial-Result Truthfulness Rule:** Whenever `sweep_status !== "COMPLETED"`, already-finished steps may remain visible **explicitly labeled `PARTIAL SWEEP — INCOMPLETE`**, every unexecuted/failed step records `status: "NOT_RUN_SWEEP_TERMINATED"` (`value: null`), and V2 **withholds** any multi-point decay summary or completed-trend badge!

#### 7.2.2 Fail-Closed Comparator Input Validation Contract (`V2-SPEC-R1-L2`, Python & JS Parity)

All four V2-B comparator functions in `v2_comparators.py` and their JS mirror in `explorer/v2_force_story_ui.js` MUST enforce identical strict, non-coercing validation (matching V1-B2's non-coercing numeric standard):

| Comparator Function | Required Parameters & Exact Closed SI Bounds | Strict Type / Whitelist / Failure Rules |
| --- | --- | --- |
| `evaluate_h2_ion_wind_atmospheric(current_a, gap_m, mobility_m2_per_vs, pressure_regime)` | `current_a ∈ [0.0, 5.0e-4]` (`A`), `gap_m ∈ [5.0e-3, 1.0e-1]` (`m`), `mobility_m2_per_vs ∈ [1.2e-4, 2.5e-4]` (`m²/(V·s)`), `pressure_regime ∈ {"atmospheric_1atm_collisional", "rarefied_or_high_vacuum"}` | Reject `bool`, `None`/`null`/`undefined`, strings for numbers, objects/arrays, `NaN`, `±Infinity` → `status: "INVALID_COMPARATOR_INPUT"`, `value: null`, `reason_code: "NON_FINITE_OR_TYPE_ERROR"`.<br>Any `pressure_regime` not in the 2-item whitelist (empty string, unknown string, numeric pressure, `null`, `bool`) → `status: "INVALID_COMPARATOR_INPUT"`, `value: null`, `reason_code: "UNSUPPORTED_PRESSURE_REGIME"`.<br>Out-of-bounds numeric input (including `< 0`, `mobility <= 0`, or above max) → `status: "INVALID_COMPARATOR_INPUT"`, `value: null`, `reason_code: "OUT_OF_RANGE"`.<br>When `pressure_regime == "rarefied_or_high_vacuum"` AND numeric inputs are valid → `status: "OUT_OF_MODEL_VALIDITY_REGIME"`, `value: null`, `reason_code: "COLLISIONAL_DRIFT_INVALID_IN_VACUUM"` (if numeric inputs are invalid even under rarefied selector, return `INVALID_COMPARATOR_INPUT` first).<br>When valid + atmospheric: exact `0.0 N` at `current_a == 0.0`; Python/JS parity tolerance `max(1e-15, 1e-12 * max(|js|, |py|))`. |
| `evaluate_h2_lorentz_lead_bound(current_a, length_m, b_field_t)` | `current_a ∈ [0.0, 1.0e-1]` (`A`), `length_m ∈ [5.0e-2, 1.0]` (`m`), `b_field_t ∈ [2.5e-5, 6.5e-5]` (`T`) | Identical strict non-coercing type/finiteness (`NON_FINITE_OR_TYPE_ERROR`) and closed-range (`OUT_OF_RANGE`) fail-closed returns (`value: null`); exact `0.0 N` at `current_a == 0.0`. |
| `evaluate_ref_photon_recoil(power_w)` | `power_w ∈ [0.0, 1.0e3]` (`W`), `c = 299792458.0 m/s` | Identical strict fail-closed validation (`NON_FINITE_OR_TYPE_ERROR` / `OUT_OF_RANGE`, `value: null`); exact `0.0 N` at `power_w == 0.0`. |
| `evaluate_ref_ion_exhaust(beam_current_a, accel_voltage_v, ion_mass_kg)` | `beam_current_a ∈ [0.0, 1.0e-1]` (`A`), `accel_voltage_v ∈ [1.0e2, 5.0e3]` (`V`), `ion_mass_kg ∈ [1.67e-27, 4.0e-25]` (`kg`), `q_i = 1.602176634e-19 C` | Identical strict fail-closed validation (`NON_FINITE_OR_TYPE_ERROR` / `OUT_OF_RANGE`, `value: null`, rejecting `<= 0` mass or voltage); exact `0.0 N` at `beam_current_a == 0.0`. |

### 7.3 Typed Schema Contracts (Exhaustive Discriminated Unions — `V2-SPEC-R1-M2`, `L1`, `L2`)

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
      status: "WITHHELD_INELIGIBLE_MESH_LEVEL";
      value: null;                     // NEVER 0.0
      http_status: 200;
      native_v1_code: "WITHHELD_INELIGIBLE_MESH_LEVEL";
      failed_levels: number[];
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

interface ForceLedgerRow {
  row_id: string;
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
    input_fingerprint: string | null;
    request_id: number | null;
  };
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
     - **Typed Schema & Lossless V1 Mapping Rejection Tests (`V2-SPEC-R1-M2`):** Reject scalar-only `value` on 2D vector rows; reject 2D vector rows omitting signed `fx_n_per_m` / `fy_n_per_m`; reject numeric `0.0` on any `null`-value status (`UNKNOWN_UNMODELED`, `PENDING_SCIENTIFIC_ACCEPTANCE`, `OUT_OF_MODEL_VALIDITY_REGIME`, `INVALID_COMPARATOR_INPUT`, `WITHHELD_INVALID_CONTOUR_TOPOLOGY`, `WITHHELD_INELIGIBLE_PRIMARY_GRID`, `WITHHELD_INELIGIBLE_MESH_LEVEL`, `REJECTED_INVALID_FORCE_DOMAIN`); reject cross-unit (`N` + `N/m`) aggregation; verify lossless 1-to-1 preservation of native V1 `WITHHELD_INVALID_CONTOUR_TOPOLOGY`, `WITHHELD_INELIGIBLE_PRIMARY_GRID`, `INVALID_FORCE_DOMAIN`, and `WITHHELD_INELIGIBLE_MESH_LEVEL`.
     - **Charter Crosswalk (`V2-SPEC-R1-L1`):** Assert every `EpistemicClass` maps cleanly to valid `ScientificCharterCategory[]` and every conditional comparator output carries non-empty `what_if_parameters` and `"WHAT-IF PARAMETER"` charter disclosure.
     - **Comparator Parity & Complete Fail-Closed Negative Matrix (`V2-SPEC-R1-L2`):** Verify exact Python-vs-JS numeric parity (`max(1e-15, 1e-12 * max(|js|, |py|))`) at boundary extrema and `0.0` current/power across all 4 comparators; verify fail-closed `value: null` (`INVALID_COMPARATOR_INPUT` / `OUT_OF_MODEL_VALIDITY_REGIME`) in **both** Python and JS for `pressure_regime = "rarefied_or_high_vacuum"`, unknown regime strings (`""`, `"low_vacuum"`, `"760"`, `null`, `true`), `NaN`, `+Inf`, `-Inf`, negative inputs, zero mobility/mass, above-max inputs, booleans (`true`/`false`), and numeric strings (`"10"`).
     - **Cryptographic Baseline & P2 Isolation:** Assert unchanged git blob SHA-1 for `electrostatics_baseline.py`, `electrostatics_numerics.py`, and `docs/V1_SOLVER_INTEGRATION_SPEC.md`, `--check-committed` snapshot parity, and **zero** Track B P2 (`exodus_hypothesis_evaluator`, `exodus_patent_geometry`, `p2_`) imports.
   - **`tests/test_v2_browser_smoke.py` (Playwright — Desktop `1280×860`, Mobile `375×812` & `390×844`):**
     - **V2-A Sync & Identity (`V2-SPEC-R1-M1`, `M2`, `M3`):** Verify `window.__v1SolverUI.subscribe()` + `getState()` atomic sync across slider edits (immediate synchronous V2 ledger clear before `150 ms` debounce), mode switches (`1D → 2D → 3D`), chapter changes, `Explore Freely`, live→offline fallback, current `400 INVALID_FORCE_DOMAIN` / `200 WITHHELD_INVALID_CONTOUR_TOPOLOGY` / `500` error mapping, and delayed stale `200`/`500` responses never repopulating a cleared V2 ledger; verify signed `(Fx, Fy)` display in `N/m`, `UNBALANCED_EXCEEDS_TOLERANCE` coarse `n=41` banner never labeled thrust, zero 2D `N/m` arrows on 3D Exodus blade, and Surface A/B strict non-conflation.
     - **V2-B Global Concurrency, Adversarial `429`/Abort & Scientific Framing (`V2-SPEC-R1-M4`, `M5`, `L2`):**
       - Adversarial live tests with `run_v1_solver.py` + delayed worker simulation: (a) V1 slider/study traffic immediately preceding V2 sweep causing transient `429` → bounded backoff retry succeeds without crashing; (b) sustained `429` exhausting `max_retries_per_step = 3` → deterministic `PARTIAL_ABORTED_BUSY` state with unrun steps `null` and trend summary withheld; (c) `503 WORKER_UNAVAILABLE_POISONED` → immediate stop with `0` retries; (d) mid-sweep preemption via V1 mode/slider/study/chapter/Chapter 5 wave toggle → synchronous cancel, `0` stray sweep fetches past `240 ms`, and delayed step responses discarded; (e) mid-sweep offline fallback transition.
       - Verify `NC-WALL` DOM text strictly qualifies the 3-point 2D sweep as a case-specific `N/m` model trend, never asserts universal monotonicity or unique identification of measured `µN` wall coupling, and never equates `N/m` with `µN`.
       - Verify `H2-ION` atmospheric calculation vs high-vacuum `OUT_OF_MODEL_VALIDITY_REGIME` (`value: null`), `H2-WIRE` & reference comparators, 6-control Null-Control Lab keyboard navigation, and truthful `file://` / static `http.server` offline fallback.
     - **Preservation & Isolation:** Chapter 5 scalar-wave isolation (`> 200 ms` post-debounce zero `/api/v1/solve` & `/api/v1/study` checks across V2 triggers), zero console/page errors, `<= 1 px` mobile overflow at `375px` & `390px`, and full `229`-test V0/V0.1/V0.2/V1/P0/P1 suite passing without regression.

---

## 8. Independent Review Acceptance Criteria (V2 Spec R2)

This specification is ready for independent ChatGPT acceptance when:

1. All 7 R1 findings (`V2-SPEC-R1-M1`, `M2`, `M3`, `M4`, `M5`, `L1`, `L2`) are closed cleanly without weakening any of the 8 mandatory scientific constraints in Section 1.
2. Surface A (qualitative 3D Exodus DUT hypotheses) and Surface B (separate quantitative 1D/2D P0/P1 analogues) never imply shared geometry or conflate units (`N` vs `N/m` vs `PENDING_SCIENTIFIC_ACCEPTANCE`).
3. Typed ledger schemas represent signed 2D `(Fx, Fy)` vectors cleanly without scalar coercion, preserve native V1 `WITHHELD_INVALID_CONTOUR_TOPOLOGY` / `INVALID_FORCE_DOMAIN` / `WITHHELD_INELIGIBLE_MESH_LEVEL` statuses losslessly, and reject `0.0` coercion of unknowns.
4. V1 → V2 synchronization (`subscribe()` + `getState()` atomic validation), global single-slot backend concurrency (`onPreempt`, bounded `429` retry, `503` fail-closed precedence, partial-result semantics), `NC-WALL` evidence-compatible framing, Charter 5-category crosswalk, and fail-closed Python/JS comparator validation are completely and testably specified.
5. Frozen P0/P1 kernels, accepted V1 Spec R5, accepted V1 baselines, and Track B P2 (`Draft PR #11`) remain untouched; Track B remains at `2 of 5` accepted scientific gates.
6. **Independent Review Verdict:** `0 HIGH, 0 MEDIUM` findings on this specification, followed by separate explicit owner authorization before opening any V2-A or V2-B implementation branch.
