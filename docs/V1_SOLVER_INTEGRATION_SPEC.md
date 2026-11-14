# V1 Specification & Implementation Plan — Validated P0/P1 Solver Integration (Revision R2)

**Status:** Specification R2 (remediating all 2 HIGH and 4 MEDIUM findings from ChatGPT V1 Specification Review R1 [`issuecomment-6878836067`](https://github.com/aguacatero/scalar-wave-viz/pull/18#issuecomment-6878836067)); pending independent R2 review and explicit owner authorization before any V1 implementation begins.  
**Baseline Anchor:** Frozen accepted V0.2 educational code SHA `634437f70e6b2bdd5b3bd41d6b77cbe551078f05` ([Draft PR #18](https://github.com/aguacatero/scalar-wave-viz/pull/18), canonical R6 acceptance [`issuecomment-6871100151`](https://github.com/aguacatero/scalar-wave-viz/pull/18#issuecomment-6871100151)) stacked on accepted V0.1 SHA `55da03af781dbc1470a2bd22a7b9dfc93bbf0950` ([Draft PR #15](https://github.com/aguacatero/scalar-wave-viz/pull/15)) and accepted P0/P1 `main` (`bc3929605300177c3ac26a579930af915c5cebea`).  
**Track B Isolation:** Uses **only** accepted P0 (`electrostatics_baseline.py`, git blob `97f65dfa25db7730323edd5e52c98b17371fdeaa`) and P1 (`electrostatics_numerics.py`, git blob `a29f1f3a55946f33760179677dd3dbeb6a2ebde2`) calculations. **Zero unaccepted P2 calculations, geometries, or H0/H1 patent claims** from [Draft PR #11](https://github.com/aguacatero/scalar-wave-viz/pull/11) may be imported, copied, or exposed in V1. Accepted P0/P1 kernels must **not** be modified under this UI task without a separate scientific review.

---

## 1. Purpose & Epistemic Separation

V0.2 delivered an independently accepted 3D educational visual experience using **schematic** field streamlines and bounded force arrows over an Exodus-inspired 3D single-stage electrode layout.

V1 connects interactive controls to **supported, validated conventional P0/P1 electrostatic calculations** while enforcing strict epistemic separation between:
1. **ESTABLISHED MODEL (COMPUTED):** Quantitative outputs from validated P0/P1 solvers (`parallel_plate_benchmark`, `verify_plate_force_virtual_work`, `electrode_pair_in_grounded_box`, `evaluate_whole_apparatus_force_budget`, and optional on-demand `electrode_pair_mesh_study` + `assess_probe_convergence` / `force_mesh_convergence_study`).
2. **PROVISIONAL ILLUSTRATIVE SCENE (SCHEMATIC):** The 3D Exodus-inspired knife-edge wedge geometry, schematic streamlines, and `#slider-eps` dielectric visual proxy.
3. **TOY MATHEMATICAL ILLUSTRATION:** The isolated Chapter 5 mathematical scalar-wave contrast view.

V1 **never** claims whole-body propellantless thrust, **never** maps 2D `N/m` cylinder-in-box results onto the 3D Exodus knife-edge mesh, **never** presents an unbalanced numerical residual as closed force balance, and **always** preserves `WHOLE-BODY THRUST: NOT MEASURED / NOT ESTABLISHED`.

---

## 2. Validated P0/P1 Solver Scope & Scoped Output Contract

### 2.1 Supported P0/P1 Calculations (Read-Only Accepted Kernels)

| V1 Solver Mode | Validated Python API | Canonical Inputs (SI) | Strictly Scoped Outputs & Units | Validity & Limitations |
| --- | --- | --- | --- | --- |
| **1D Ideal Parallel-Plate Analytic Benchmark** | `electrostatics_baseline.parallel_plate_benchmark`<br>`electrostatics_baseline.verify_plate_force_virtual_work` | `voltage_v` ($\Delta V \ge 0$ in `V`), `gap_m` (`m`), `area_m2` (`m²`) | **1D-only fields:** `electric_field_v_per_m` (`V/m`), `pressure_pa` (`Pa`), `force_on_positive_plate_n` (`+N`), `force_on_negative_plate_n` (`-N`), `net_pair_force_n` (`0.0 N`), `stored_energy_j` (`J`), `virtual_work` (`virtual_work_fixed_v_n`, `virtual_work_fixed_q_n`, `signed_f_gap_fixed_v_n`, `signed_f_gap_fixed_q_n` in `N`) | Assumes infinite planar conductors in homogeneous vacuum ($\varepsilon_r = 1.0$, `EPSILON_0_F_PER_M = 8.8541878188e-12 F/m`); neglects fringing fields (emits fringing warning when $\sqrt{A}/d < 5$). Not a 3D blade or dielectric solver. |
| **2D Cylindrical Electrodes in Grounded Square Box** | `electrostatics_baseline.electrode_pair_in_grounded_box`<br>`electrostatics_numerics.evaluate_whole_apparatus_force_budget`<br>*Optional on-demand multi-grid studies:*<br>`electrostatics_baseline.electrode_pair_mesh_study`<br>`electrostatics_baseline.assess_probe_convergence`<br>`electrostatics_numerics.force_mesh_convergence_study` | `GroundedBoxConfig`: `n` $\in \{41, 81, 101\}$, `box_width_m` (`m`), `left_electrode` & `right_electrode` (`center_x_m`, `center_y_m`, `radius_m`, `voltage_v`) subject to Section 3 grid-resolved domain & contour topology checks | **2D-only fields:** `potential_v` (`V`, shape `[n, n]`), `ex_v_per_m` & `ey_v_per_m` (`V/m`, masked non-vacuum nodes encoded as JSON `null`), boolean `vacuum_mask` / `conductor_mask` / `boundary_mask`, `grid_axes` (`indexing: "ij"`), `grid_spacing_m` (`m`), `max_discrete_residual_v` (`V`), and **full 6-component vector `force_budget`** (`N/m`) when topology passes | **2D cross-section only (`N/m` force per unit depth, NOT 3D `N`)**; circular conductors in $0\text{ V}$ grounded square enclosure (NOT 3D Exodus knife-edge blade); homogeneous vacuum ($\varepsilon_r = 1.0$, no dielectric potting); $O(h)$ staircase boundary truncation; peak $|E|$ is grid-sensitive; mechanical supports/standoffs are unmodeled (`unmodeled_reaction_explanation`). |

**Contractual Scope Discipline (`V1-SPEC-R1-M1`):**
- 1D-only fields (`pressure_pa`, `stored_energy_j`, `virtual_work_*`) are **never** synthesized or extrapolated for 2D grounded-box runs.
- 2D-only fields (`max_discrete_residual_v`, `N/m` `WholeApparatusForceBudget`, 2D `[n, n]` field slices) are **never** synthesized for 1D parallel-plate runs.

### 2.2 Excluded Scope & Cryptographic P2 Isolation (`V1-SPEC-R1-M4`)

- **No P2 imports or copied logic:** Zero imports, calls, or copied equations/meshes/outputs from Draft PR #11 (`p2_*`, `Eq. (11)`, `FIG. 21` 3D FEM or inhomogeneous dielectric calculations).
- **Cryptographic Kernel Integrity Guard:** Automated V1 tests verify exact git blob SHA-1 hashes of `electrostatics_baseline.py` (`97f65dfa25db7730323edd5e52c98b17371fdeaa`) and `electrostatics_numerics.py` (`a29f1f3a55946f33760179677dd3dbeb6a2ebde2`) so V1 UI integration cannot silently alter accepted P0/P1 scientific code.
- **Dependency Allowlist:** V1 backend bridge (`run_explorer.py` + V1 helper module) may import **only** Python standard library modules, `numpy`, `electrostatics_baseline`, and `electrostatics_numerics`.
- **Dielectric Proxy Lock:** `#slider-eps` ($\varepsilon_r \in [1.0, 5.0]$) remains **`VISUAL_MATERIAL_PROXY_ONLY`** and never alters any computed P0/P1 vacuum calculation.
- **`scalar_wave_3d.py` Isolation:** Remains excluded from propulsion claims and isolated inside Chapter 5's mathematical contrast view.

---

## 3. Domain Eligibility, Contour Topology & Honest Force Residual Accounting

### 3.1 Grid-Resolved Eligibility & Snapped-Contour Topology Validation (`V1-SPEC-R1-F1`)

Continuous `GroundedBoxConfig` bounds (`abs(cx) + r < W/2`, `center_dist > r_L + r_R`) are necessary but **not sufficient** for valid 2D force-budget evaluation because `electrode_pair_in_grounded_box` rasterizes disks onto an $n \times n$ grid (`h = box_width_m / (n - 1)`) and `compute_maxwell_stress_contour` snaps contour bounds to `np.clip(..., 1, n - 2)` checking only perimeter `vacuum_mask` rather than enclosed body topology.

Without modifying accepted P0/P1 kernels, the V1 bridge adapter enforces **two deterministic validation gates** for `grounded_box_2d`:

1. **Pre-Solve Grid-Resolved Domain Eligibility Gate:**
   - Reject arbitrary unvalidated geometries with HTTP `400` (`code: "INVALID_FORCE_DOMAIN"`) before solving if any grid-resolution invariant fails:
     - Discrete resolution minimum: `radius_m >= 3.0 * h` for both electrodes (ensures resolved circular cross-sections rather than 1–2 pixel degenerate masks).
     - Inter-electrode vacuum clearance: `center_dist - (r_L + r_R) >= 6.0 * h` (guarantees distinct non-overlapping electrode contours with $\ge 2$ interior vacuum cells between them).
     - Wall clearance: `W/2 - (abs(cx) + r) >= 6.0 * h` and `W/2 - (abs(cy) + r) >= 6.0 * h` for both electrodes (guarantees `wall_margin = 2.5 * h` sits cleanly inside vacuum between the outer box and every electrode contour).
     - Supported geometry family in interactive UI: collinear symmetric or bounded off-axis (`|cy| <= W/4` subject to all wall/inter-electrode `6.0 * h` clearances above) with `n` $\in \{41, 81, 101\}$.
2. **Post-Solve Snapped-Contour Topology Gate (Before Returning Force Budget):**
   - After obtaining `FieldSolution`, reconstruct the exact snapped index boxes `(ix_min, ix_max, iy_min, iy_max)` that `evaluate_whole_apparatus_force_budget` uses for `c_left`, `c_right`, and `c_enclosure_inner` and verify directly on the boolean masks (`left_mask`, `right_mask`, `boundary_mask`, `vacuum_mask`):
     - `c_left` perimeter is 100% `vacuum_mask`; strict interior contains **all** `left_mask` nodes (`np.all(left_mask[ix_min+1:ix_max, iy_min+1:iy_max] == left_mask[ix_min+1:ix_max, iy_min+1:iy_max])` / zero `left_mask` nodes outside `c_left` interior), **zero** `right_mask` nodes, and **zero** `boundary_mask` nodes.
     - `c_right` perimeter is 100% `vacuum_mask`; strict interior contains **all** `right_mask` nodes, **zero** `left_mask` nodes, and **zero** `boundary_mask` nodes.
     - `c_left` and `c_right` index boxes are strictly disjoint and lie strictly inside `c_enclosure_inner`.
     - `c_enclosure_inner` perimeter is 100% `vacuum_mask`; strict interior contains **all** nodes of `left_mask | right_mask` and **zero** `boundary_mask` nodes.
   - **Fail-Closed Withholding Rule:** If any contour topology check fails—even when the Laplace potential solve itself succeeds—the bridge **must withhold all force-budget values** (`force_budget: null`, `force_budget_status: "WITHHELD_INVALID_CONTOUR_TOPOLOGY"`, diagnostic message explaining which contour failed).

### 3.2 Full 6-Component Force Budget & Four-Way Numerical Uncertainty Separation (`V1-SPEC-R1-F2`)

1. **Full 6-Component Vector Budget (`N/m`):**
   - `force_budget` exposes **all six conductor components**, vector sum residuals, norm, exact tolerance, and closure status:
     - `left_electrode_fx_n_per_m`, `left_electrode_fy_n_per_m`
     - `right_electrode_fx_n_per_m`, `right_electrode_fy_n_per_m`
     - `enclosure_reaction_fx_n_per_m`, `enclosure_reaction_fy_n_per_m`
     - `net_electrostatic_force_fx_n_per_m`, `net_electrostatic_force_fy_n_per_m`
     - `net_electrostatic_force_norm_n_per_m` (`hypot(net_fx, net_fy)`)
     - `relative_closure_residual` (`norm / max(||F_left||, ||F_right||, ||F_enc||)` when nonzero, else `0.0`)
     - `tolerance_n_per_m` (exact threshold passed to `evaluate_whole_apparatus_force_budget`, e.g., `1e-4 N/m`)
     - `is_force_balanced_to_tolerance` (`bool`) and `force_closure_status`: `"BALANCED_WITHIN_TOLERANCE"` | `"UNBALANCED_EXCEEDS_TOLERANCE"`.
   - **Voltage-Scaling Disclosure & Non-Suppression Rule:** Stress and finite-grid discretization residuals scale as $V^2$ for fixed geometry. Passing `< 1e-4 N/m` at $1\text{ kV}$ does **not** imply closure within `1e-4 N/m` at $50\text{ kV}$. V1 **never** clamps residuals to zero, **never** states "equal and opposite" or "balanced" when `is_force_balanced_to_tolerance === false`, and displays a prominent amber/red warning banner whenever `force_closure_status === "UNBALANCED_EXCEEDS_TOLERANCE"`.
2. **Strict Separation of Four Numerical Quality Quantities:**
   - **Discrete PDE Residual (`V`):** `max_discrete_residual_v` (single-grid Laplace solver stopping residual).
   - **Force Closure Residual (`N/m`):** `net_electrostatic_force_norm_n_per_m` vs `tolerance_n_per_m` (whole-contour conservation check on a single grid).
   - **Finite-Grid Force Sensitivity (`N/m` / `%`):** Single-solve `/api/v1/solve` reports `force_mesh_sensitivity_status: "NOT_ASSESSED"`. Optional on-demand multi-resolution study (`POST /api/v1/study` or explicit `include_convergence_study: true` running `force_mesh_convergence_study` across `n_list = (41, 81, 101)` — $\ge 3$ distinct resolutions) reports per-component finite-grid variation (`max_abs_change_to_prev`, `max_relative_change_to_prev`) honestly without claiming single-grid convergence.
   - **Probe Field Stability (`V/m` / `%`):** Single-solve `/api/v1/solve` reports `probe_stability_status: "NOT_ASSESSED"`. Optional on-demand multi-resolution study invokes `electrode_pair_mesh_study` + `assess_probe_convergence` (`electrostatics_baseline.py`, requiring $\ge 3$ distinct resolutions; `is_converged` remains `False` for finite-grid stability, with `is_stable` and `convergence_status` reported verbatim).

---

## 4. API, Serialization, Concurrency & Local Bridge Security Contract

### 4.1 Bounded SI Input Schema & Canonical Echo (`V1-SPEC-R1-M1`)

- **Unified Grid Allowlist:** Interactive `/api/v1/solve` accepts **only** `n` $\in \{41, 81, 101\}$ (JSON integer, rejecting `bool`).
- **Strict JSON Schema Validation (Reject `400` on violation):**
  - Unknown top-level or nested parameter keys rejected (`additionalProperties: false`).
  - Booleans (`True`/`False`) explicitly rejected anywhere a number or integer is expected (`isinstance(v, bool)` check before `int`/`float`).
  - Non-finite numbers (`NaN`, `Infinity`, `-Infinity`), strings, `null` for required fields, and out-of-range overflows rejected.
  - Bounded SI input ranges:
    - `parallel_plate_1d`: `voltage_v` $\in [0.0, 50000.0]$ (`V`, potential difference $\Delta V$), `gap_m` $\in [0.005, 0.200]$ (`m`), `area_m2` $\in [1e-4, 0.05]$ (`m²`).
    - `grounded_box_2d`: `n` $\in \{41, 81, 101\}$, `box_width_m` $\in [0.04, 0.20]$ (`m`), `radius_m` $\in [0.0015, 0.015]$ (`m`), `left_voltage_v` & `right_voltage_v` $\in [-50000.0, 50000.0]$ (`V`), `center_x_m` & `center_y_m` finite and satisfying Section 3.1 clearances.
- **Voltage Difference vs. Polarity & Real Preset Mapping:**
  - `parallel_plate_1d` is parameterized by scalar potential difference $\Delta V$ (uniform field invariant to common-mode offset).
  - `grounded_box_2d` preserves distinct electrode potentials $(V_L, V_R)$ relative to $0\text{ V}$ grounded outer walls: asymmetric $(-20\text{ kV}, 0\text{ V})$ and symmetric bipolar $(\pm 10\text{ kV})$ presets produce physically distinct wall-image fields and enclosure reactions.
  - Presets explicitly label their exact physical geometries without conflation:
    - **P0/P1 Canonical Benchmark Preset:** `box_width_m = 0.040 m` (`40 mm`), `r = 0.003 m` (`3 mm`), `center_x = ±0.008 m`, surface gap `10.0 mm`, `V_L = +500 V`, `V_R = -500 V`.
    - **V0.2 Explorer-Aligned Benchmark Preset:** `box_width_m = 0.160 m` (`160 mm`), `r = 0.003 m` (`3 mm`), surface gap `d >= 16.0 mm` (default `25.0 mm`, matching V0.2 slider range `16–50 mm`), `V_L = -20000 V`, `V_R = 0 V`.
- **Canonical Response Echo & Metadata:** Every `200` response echoes `request_id`, `input_fingerprint`, `model_id`, `epistemic_label: "ESTABLISHED MODEL"`, canonical `parameters` in SI units, `constants: {"epsilon_0_f_per_m": 8.8541878188e-12}`, `provenance` (`module`, `function`, `git_commit`, solver blob SHA-1, `whole_body_thrust_status: "NOT MEASURED / NOT ESTABLISHED"`), and `uncertainty_and_limits`.

### 4.2 Strict RFC 8259 Serialization, Axis Ordering & Race Protection (`V1-SPEC-R1-M2`)

- **Strict JSON Serialization (`allow_nan=False`):**
  - Python server serializes all payloads with `json.dumps(payload, allow_nan=False)`.
  - Before serialization, validate `np.all(np.isfinite(sol.potential_v))` and `np.all(np.isfinite(sol.ex_v_per_m[sol.vacuum_mask]))` and `np.all(np.isfinite(sol.ey_v_per_m[sol.vacuum_mask]))`.
  - Non-vacuum cells (`~sol.vacuum_mask`) in `ex_v_per_m` and `ey_v_per_m` are emitted explicitly as JSON `null` alongside boolean `vacuum_mask`, `conductor_mask`, and `boundary_mask`—**never** `NaN`/`Infinity` and **never** `0.0` (which would falsely imply zero physical field inside conductors).
- **Explicit Array Shape & Axis Ordering:**
  - `electrode_pair_in_grounded_box` builds coordinates via `np.meshgrid(coords, coords, indexing='ij')`.
  - Payload includes `grid_axes: {"coords_m": [...], "shape": [n, n], "axis_0": "x_m", "axis_1": "y_m", "indexing": "ij"}` so client rendering indexes `arr[ix][iy]` consistently with `(x_m[ix], y_m[iy])`.
- **Client Concurrency, Stale-Response Rejection & State Invalidation:**
  - Client attaches monotonically increasing `request_id` + canonical `input_fingerprint` to every solve request and maintains `latestRequestId` and `activeModelMode`.
  - Any response with `resp.request_id !== latestRequestId` or mismatched `activeModelMode` is discarded immediately.
  - Whenever `solveState` is `"pending"` or `"error"`, active live computed readouts and 2D slice overlays are immediately cleared/invalidated (never showing stale parameters as current). Any fallback offline snapshot card stays visually isolated with its exact original frozen parameters printed on the card.

### 4.3 Local Bridge Isolation & Resource Bounds (`V1-SPEC-R1-M3`)

In `run_explorer.py`:
- **Enforce Loopback at Server Creation:** `create_server(host, port)` (not merely the CLI `--host` default) validates `host` $\in \{\text{"127.0.0.1"}, \text{"localhost"}, \text{"::1"}\}$ and raises `ValueError` for non-loopback addresses (`0.0.0.0`, external IPs).
- **Origin, Host & Header Validation for `/api/v1/*`:**
  - Validate `Host` header matches bound loopback host/port; otherwise HTTP `403`.
  - On `POST /api/v1/solve` and `POST /api/v1/study`, validate `Origin` (when present) matches exact same-origin `http://127.0.0.1:<port>` or `http://localhost:<port>` (`403` on foreign origin); emit **zero** permissive `Access-Control-Allow-Origin: *` CORS headers.
  - Require `Content-Type: application/json` (`415` otherwise).
- **Payload, Concurrency & Runtime Bounds:**
  - Reject bodies `> 8192` bytes (`413 Payload Too Large`); enforce socket read timeout (`2.0 s`).
  - Use bounded `ThreadingTCPServer` (`daemon_threads = True`) with a non-blocking/bounded solve lock/semaphore (`max_concurrent_solves = 1`, returning `429 Too Many Requests` if a prior solve is still running beyond brief queue wait) and a bounded solve wall-clock guard (`5.0 s`, returning `504` structured error if exceeded).
  - Return structured JSON errors `{ "error": { "code", "message", "field" } }` on all `4xx`/`5xx` failures.
- **Client Debouncing:** Debounce slider `input` events (`150 ms`) and attach `AbortController` to in-flight fetches (recognizing browser abort alone does not halt synchronous server compute, which is bounded server-side by `n <= 101` and concurrency/runtime guards).
- **Offline / No Cloud:** Zero external API calls or automated live dispatch.

---

## 5. True Offline Delivery, Visual Separation & Iceberg Preservation (`V1-SPEC-R1-M4`)

### 5.1 True `file://` and Static HTTP Offline Compatibility

- Sibling `fetch("*.json")` fails under `file://` in modern browsers due to CORS/same-origin restrictions.
- V1 therefore bundles deterministic P0/P1 reference snapshots in **`explorer/v1_reference_snapshots.js`** (defining `window.V1_REFERENCE_SNAPSHOTS`, loaded via `<script>` in `index.html` alongside `explorer/v1_reference_snapshots.json` for schema/parity verification via `scripts/generate_v1_snapshots.py`).
- **1D Parallel-Plate Analytic:** Uses exact closed-form JS evaluation (`EPSILON_0_F_PER_M = 8.8541878188e-12`) verified against Python `parallel_plate_benchmark` within `max(1e-15, 1e-12 * max(|js|, |py|))` (covering exact `0.0` at `0 V`).
- **2D Grounded-Box Offline Fail-Closed Behavior:** When `/api/v1/capabilities` is unavailable (`file://` or static `http.server`), V1 **locks** the 2D snapshot selector to precomputed presets, **disables** arbitrary 2D geometry/voltage/grid recalculation controls, displays `SOLVER BRIDGE OFFLINE — Showing locked static P0/P1 reference snapshot (launch python run_explorer.py for live 2D Laplace recalculation)`, and **never** echoes moved slider values onto frozen snapshot numbers.

### 5.2 Unmistakable Visual Separation & Iceberg Preservation

- **Dedicated 2D Benchmark Viewport / Mode Isolation:**
  - When Computed 2D Benchmark Mode is active, render the 2D `potential_v` / `|E|` colormap on a dedicated 2D cross-section canvas/inset (with explicit `x (mm)` and `y (mm)` axes, circular electrode cross-sections, outer $0\text{ V}$ grounded box outline, and `N/m` vector budget arrows) OR unmistakably separate axes while **hiding 3D Exodus schematic force arrows (`forceGroup`)** so **zero `N/m` arrows ever appear attached to the 3D Exodus knife-edge blade**.
  - Persistent mode badge clearly labels `ESTABLISHED MODEL (COMPUTED — 2D VACUUM FD LAPLACE, N/m)` vs `PROVISIONAL ILLUSTRATIVE SCENE (SCHEMATIC 3D EXODUS MODEL)`.
- **Chapter 5 & Iceberg Preservation:**
  - All 6 Iceberg chapters, Surface/Shallow/Deeper/Research disclosures, `Explore Freely`, `syncWaveContrastUI()`, and mobile 375px/390px layouts remain intact.
  - Entering Chapter 5 mathematical scalar-wave view hides all physical AND computed 2D overlays cleanly.

---

## 6. Validation Plan & Independent Acceptance Criteria

### 6.1 Required Automated Test Suites

1. **V1 Solver Bridge, Topology & Security Unit Tests (`tests/test_v1_solver_bridge.py`):**
   - **Parity & Constants:** `parallel_plate_1d` JS and `/api/v1/solve` match `electrostatics_baseline.parallel_plate_benchmark` within `max(1e-15, 1e-12 * max(|js|, |py|))` including `V = 0` exact zero parity and `EPSILON_0_F_PER_M = 8.8541878188e-12`.
   - **Negative Contour & Domain Topology Tests (`V1-SPEC-R1-F1`):** Coarse-grid/small-radius (`n=41, r=0.5 mm, W=80 mm`), near-wall (`< 6*h`), insufficient inter-electrode separation (`< 6*h`), and synthetic wrong-enclosure contour tests verify force-budget withholding (`force_budget is None`) even if potential solves succeed.
   - **Vector Force Residual & $V^2$ Scaling Tests (`V1-SPEC-R1-F2`):** Off-axis nonzero `Fy` across all 6 components; deliberately unbalanced coarse-grid high-voltage case (`is_force_balanced_to_tolerance is False` -> `UNBALANCED_EXCEEDS_TOLERANCE`); $V^2$ scaling check across fixed geometry.
   - **Schema & Strict JSON Serialization Tests (`V1-SPEC-R1-M1/M2`):** Reject `bool`, unknown keys, `NaN`/`Inf`, `n=121` or `n=42`; verify `allow_nan=False`, `null` on `~vacuum_mask`, `indexing='ij'` shape `[n, n]`, and scoped 1D vs 2D fields.
   - **Security & Resource Bounds Tests (`V1-SPEC-R1-M3`):** Reject non-loopback `create_server('0.0.0.0', ...)`, wrong `Host`/`Origin` (`403`), non-JSON `Content-Type` (`415`), oversized body (`413`), malformed JSON (`400`), and verify zero permissive CORS headers.
   - **Offline Snapshot Parity & P2 Isolation Guard (`V1-SPEC-R1-M4`):** Verify `v1_reference_snapshots.js` matches `v1_reference_snapshots.json` and `electrostatics_baseline`/`electrostatics_numerics` outputs; verify exact git blob SHA-1 hashes of `electrostatics_baseline.py` (`97f65dfa25db7730323edd5e52c98b17371fdeaa`) and `electrostatics_numerics.py` (`a29f1f3a55946f33760179677dd3dbeb6a2ebde2`), dependency allowlist, and zero P2 imports/logic.
2. **Playwright V1 Browser Regression Tests (`tests/test_v1_browser_smoke.py` + preserved 34 `test_v0_browser_smoke.py` tests):**
   - Live bridge tests: slider sweeps update computed `E`, `p`, `F`, 6-component `N/m` budget, and `force_closure_status`; `0 V` yields exact zero; rapid slider drag rejects stale responses (`request_id`); bridge `500`/`400` invalidates current computed readout; unbalanced high-V coarse run renders warning without claiming balance; `#slider-eps` leaves computed P0/P1 values invariant with `VISUAL PROXY ONLY` badge.
   - Visual separation & Chapter 5 tests: computed mode hides 3D schematic `forceGroup` arrows (zero `N/m` arrows attached to Exodus blade); Chapter 5 wave mode hides all physical and computed overlays.
   - True offline tests: run Playwright against **both** `file://.../explorer/index.html` AND static `python -m http.server` (no `/api/v1/solve`), verifying locked snapshot display, disabled arbitrary 2D controls, and working 1D analytic parity.
   - Mobile `375px` and `390px` zero-overflow checks.

### 6.2 Independent V1 Acceptance Gate

V1 implementation may merge only after:
1. All P0/P1, V0–V0.2, and V1 unit + Playwright tests pass in CI with manifest provenance gate green and intact P0/P1 solver blob hashes.
2. Independent scientific/UX review accepts the V1 PR on exact HEAD SHA, confirming zero P2 leakage, strict computed-vs-schematic separation, honest unbalanced residual reporting, and offline/loopback security.
3. Explicit owner authorization is given.

---

## 7. Merge Sequencing & Integrated-Tree Verification Plan (PRs #15 and #18)

Per the owner sequencing recommendation in [`issuecomment-6878836067`](https://github.com/aguacatero/scalar-wave-viz/pull/18#issuecomment-6878836067):

1. **Current Verified Branch Graph:**
   - `main`: `bc3929605300177c3ac26a579930af915c5cebea` (contains accepted P0 PR #5, P1 PR #10, and V0 PR #14 `5d8b822e8771dc19a4bf2a27bfc013e3662e03ea`).
   - Draft PR #15 (`feat/v0-1-visual-ux-polish` at `55da03af781dbc1470a2bd22a7b9dfc93bbf0950`, targeting `main`): V0.1 R5 accepted (`pullrequestreview-5816455237`).
   - Draft PR #18 (`feat/v0-2-learn-physics-backwards`, targeting `feat/v0-1-visual-ux-polish` at `55da03af781dbc1470a2bd22a7b9dfc93bbf0950`): V0.2 R6 accepted at frozen code SHA `634437f70e6b2bdd5b3bd41d6b77cbe551078f05` + documentation-only closeout/V1 spec revisions.
2. **Owner-Authorized Execution Sequence (No Merge Without Explicit Authorization):**
   - **Step 1 — Merge PR #15 (`feat/v0-1-visual-ux-polish` $\to$ `main`):**
     - Owner marks PR #15 ready and authorizes merge into `main` (preserving ancestry where possible; **do not delete `feat/v0-1-visual-ux-polish` before PR #18 is retargeted and verified**).
     - Verify integrated `main` tree with full repository CI (`140+` tests, `examples/electrostatics_demo.py`, manifest provenance gate).
   - **Step 2 — Retarget & Verify PR #18 (`feat/v0-2-learn-physics-backwards` $\to$ `main`):**
     - Retarget PR #18 base from `feat/v0-1-visual-ux-polish` to `main`.
     - Verify `git diff main..<PR18_HEAD>` matches the accepted V0.2 delta (preserving accepted V0.1 ancestry or tree equivalence plus zero unexpected implementation changes relative to frozen `634437f70e6b2bdd5b3bd41d6b77cbe551078f05`), and confirm fresh CI passes (`157` tests + manifest provenance gate).
     - Owner marks PR #18 ready and authorizes merge into `main`; verify integrated `main` tree CI.
   - **Step 3 — Branch V1 from Verified `main`:**
     - Only after V1 Specification R2 is accepted, V0.2 is verified on `main` (or explicitly stacked per owner instruction), and owner authorizes V1 kickoff, create a dedicated V1 feature branch and separate draft PR.
   - **Track B Separation:** Draft PR #11 (`p2-patent-geometry-exodus-2026-10-25`) remains isolated; P2 R10 scientific remediation may proceed independently, and no P3 work begins.
