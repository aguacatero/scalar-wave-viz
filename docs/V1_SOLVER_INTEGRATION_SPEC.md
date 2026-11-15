# V1 Specification & Implementation Plan — Validated P0/P1 Solver Integration (Revision R3)

**Status:** Specification R3 (remediating all 2 HIGH and 3 MEDIUM findings from ChatGPT V1 Specification Review R2 [`issuecomment-6880665729`](https://github.com/aguacatero/scalar-wave-viz/pull/18#issuecomment-6880665729), building on R1 [`issuecomment-6878836067`](https://github.com/aguacatero/scalar-wave-viz/pull/18#issuecomment-6878836067)); pending independent R3 review and explicit owner kickoff authorization before any V1 code begins.  
**Baseline Anchor:** Frozen accepted V0.2 educational code SHA `634437f70e6b2bdd5b3bd41d6b77cbe551078f05` ([Draft PR #18](https://github.com/aguacatero/scalar-wave-viz/pull/18), canonical R6 acceptance [`issuecomment-6871100151`](https://github.com/aguacatero/scalar-wave-viz/pull/18#issuecomment-6871100151)) stacked on accepted V0.1 SHA `55da03af781dbc1470a2bd22a7b9dfc93bbf0950` ([Draft PR #15](https://github.com/aguacatero/scalar-wave-viz/pull/15)) and accepted P0/P1 `main` (`bc3929605300177c3ac26a579930af915c5cebea`).  
**Track B Isolation:** Uses **only** accepted P0 (`electrostatics_baseline.py`, git blob `97f65dfa25db7730323edd5e52c98b17371fdeaa`) and P1 (`electrostatics_numerics.py`, git blob `a29f1f3a55946f33760179677dd3dbeb6a2ebde2`) calculations unchanged (`scipy.sparse.linalg.spsolve` is an existing transitive dependency of `electrostatics_baseline.py`, not a new direct bridge import). **Zero unaccepted P2 calculations, geometries, or H0/H1 patent claims** from [Draft PR #11](https://github.com/aguacatero/scalar-wave-viz/pull/11) may be imported, copied, or exposed in V1.

---

## 1. Purpose & Epistemic Separation

V1 connects interactive Propulsion Explorer controls to **validated conventional P0/P1 electrostatic calculations** while enforcing strict epistemic separation:
1. **ESTABLISHED MODEL (COMPUTED):** Quantitative outputs from validated P0/P1 kernels (`parallel_plate_benchmark`, `verify_plate_force_virtual_work`, `electrode_pair_in_grounded_box`, `evaluate_whole_apparatus_force_budget`, and gated multi-resolution diagnostics).
2. **PROVISIONAL ILLUSTRATIVE SCENE (SCHEMATIC — NON-COMPUTED):** The 3D Exodus-inspired knife-edge wedge layout (`W = 160 mm`, `3 mm` thickness, `0.5 mm` tip radius), schematic field streamlines, and `#slider-eps` dielectric proxy. Explicitly non-computed in V1 (`r = 3 mm` in `W = 160 mm` violates `r >= 3h` on every `{41, 81, 101}` grid and would require `n >= 161` under a separate grid/runtime review).
3. **TOY MATHEMATICAL ILLUSTRATION:** Isolated Chapter 5 `scalarWaveGroup` contrast view.

V1 **never** claims whole-body propellantless thrust, **never** maps 2D `N/m` cylinder-in-box results onto the 3D Exodus knife-edge mesh, **never** presents an unbalanced numerical residual as closed force balance, and **always** preserves `WHOLE-BODY THRUST: NOT MEASURED / NOT ESTABLISHED`.

---

## 2. Validated P0/P1 Solver Scope & Scoped Output Contract

### 2.1 Supported P0/P1 Calculations (Read-Only Accepted Kernels)

| V1 Solver Mode | Validated Python API | Canonical Inputs (SI) | Strictly Scoped Outputs & Units | Validity & Limitations |
| --- | --- | --- | --- | --- |
| **`parallel_plate_1d`** | `electrostatics_baseline.parallel_plate_benchmark`<br>`electrostatics_baseline.verify_plate_force_virtual_work` | `voltage_v` ($\Delta V \ge 0$ in `V`), `gap_m` (`m`), `area_m2` (`m²`) | **1D-only fields:** `electric_field_v_per_m` (`V/m`), `pressure_pa` (`Pa`), `force_on_positive_plate_n` (`+N`), `force_on_negative_plate_n` (`-N`), `net_pair_force_n` (`0.0 N`), `stored_energy_j` (`J`), `virtual_work` (`virtual_work_fixed_v_n`, `virtual_work_fixed_q_n`, `signed_f_gap_fixed_v_n`, `signed_f_gap_fixed_q_n` in `N`) | Ideal infinite planar conductors in vacuum ($\varepsilon_r = 1.0$, `EPSILON_0_F_PER_M = 8.8541878188e-12 F/m`); neglects fringing fields (emits fringing warning when $\sqrt{A}/d < 5$). Not a 3D blade or dielectric solver. |
| **`grounded_box_2d`** | `electrostatics_baseline.electrode_pair_in_grounded_box`<br>`electrostatics_numerics.evaluate_whole_apparatus_force_budget`<br>*Gated multi-grid studies (Section 3.3):*<br>`electrostatics_baseline.electrode_pair_mesh_study`<br>`electrostatics_baseline.assess_probe_convergence`<br>`electrostatics_numerics.force_mesh_convergence_study` | Nested `GroundedBoxConfig` (`n` $\in \{41, 81, 101\}$, `box_width_m`, `left_electrode`, `right_electrode`), `probe_xy_m`, subject to Section 3 gates | **2D-only fields:** `potential_v` (`V`, `[n, n]`), `ex_v_per_m` & `ey_v_per_m` (`V/m`, JSON `null` on `~vacuum_mask`), boolean `vacuum_mask` / `conductor_mask` / `boundary_mask`, `grid_axes` (`indexing: "ij"`), `grid_spacing_m` (`m`), `max_discrete_stencil_defect_v` (`V`), `probe` readout, and **full 6-component vector `force_budget`** (`N/m`) when topology passes | **2D cross-section (`N/m`, NOT 3D `N`)**; circular conductors in $0\text{ V}$ square box (NOT 3D Exodus blade/dielectric); homogeneous vacuum ($\varepsilon_r = 1.0$); $O(h)$ staircase boundary; peak $|E|$ is grid-sensitive; mechanical supports are unmodeled. |

- **No Cross-Mode Synthesis (`R1-M1`):** 1D-only fields (`pressure_pa`, `stored_energy_j`, `virtual_work_*`) are never emitted for `grounded_box_2d`. 2D-only fields (`max_discrete_stencil_defect_v`, `N/m` `force_budget`, `[n, n]` slices) are never emitted for `parallel_plate_1d`.

### 2.2 Excluded Scope & Cryptographic P2 Isolation (`R1-M4`)

- **Zero P2 Leakage:** Zero imports, calls, or copied equations/meshes from Draft PR #11 (`p2_*`, `Eq. (11)`, `FIG. 21` 3D FEM or inhomogeneous dielectric solvers).
- **Cryptographic Kernel Guard:** V1 tests verify exact git blob SHA-1 hashes of `electrostatics_baseline.py` (`97f65dfa25db7730323edd5e52c98b17371fdeaa`) and `electrostatics_numerics.py` (`a29f1f3a55946f33760179677dd3dbeb6a2ebde2`).
- **Direct Bridge Dependency Allowlist:** `run_explorer.py` and the V1 adapter/worker modules import **only** Python standard library modules, `numpy`, `electrostatics_baseline`, and `electrostatics_numerics` (preserving `scipy` strictly as a transitive dependency inside `electrostatics_baseline`).
- **Dielectric Proxy & Scalar Wave Isolation:** `#slider-eps` remains `VISUAL_MATERIAL_PROXY_ONLY` and never modifies any P0/P1 solver call; Chapter 5 `scalar_wave_3d` remains isolated from propulsion claims.

---

## 3. Domain Eligibility, Contour Topology, Multi-Grid Gating & Force Accounting

### 3.1 Pre-Solve Eligibility & Exact Kernel-Matched Contour Topology (`V1-SPEC-R2-F1`)

Continuous `GroundedBoxConfig` bounds (`abs(cx) + r < W/2`, Euclidean distance `> r_L + r_R`) are insufficient for force evaluation because:
1. `FieldSolution` stores combined `conductor_mask` (not separate `left_mask` / `right_mask`).
2. `evaluate_whole_apparatus_force_budget` (`electrostatics_numerics.py` L415–445) computes horizontal margins using **x-separation** `sep = abs(re.center_x_m - le.center_x_m)` and signed wall checks (`d_left_wall = (le.center_x_m - le.radius_m) - (-W/2)`, `d_right_wall = (W/2) - (re.center_x_m + re.radius_m)`), while `compute_maxwell_stress_contour` (L298–317) snaps bounds via `np.clip(np.argmin(np.abs(coords - b)), 1, n - 2)` and checks perimeter vacuum nodes only.

Without modifying accepted P0/P1 kernels, the V1 adapter enforces **two sequential gates** for every `grounded_box_2d` solve at resolution `n`:

1. **Pre-Solve Grid-Resolved Domain Eligibility Gate (HTTP `400`, `code: "INVALID_FORCE_DOMAIN"`):**
   - `h = box_width_m / (n - 1)` with `n` $\in \{41, 81, 101\}$.
   - Resolved conductor cross-section: `min(le.radius_m, re.radius_m) >= 3.0 * h`.
   - Canonical left-to-right x-ordered clearance (prevents swapped-electrode wrong-wall margins and diagonal contour overlap):
     `(re.center_x_m - re.radius_m) - (le.center_x_m + le.radius_m) >= 6.0 * h`.
   - Four-wall clearances for both electrodes:
     `W/2 - (abs(cx) + r) >= 6.0 * h` and `W/2 - (abs(cy) + r) >= 6.0 * h`.
   - Bounded off-axis UI regime: `abs(cy) <= W / 4.0`.

2. **Post-Solve Kernel-Matched Snapped-Contour Topology Gate (`200` with `force_budget: null` on failure):**
   - **Mask reconstruction:** Recompute `coords = np.linspace(-W / 2.0, W / 2.0, n)` and `x, y = np.meshgrid(coords, coords, indexing="ij")` (`electrostatics_baseline.py` L488–491):
     - `left_mask = (x - le.center_x_m)**2 + (y - le.center_y_m)**2 <= le.radius_m**2`
     - `right_mask = (x - re.center_x_m)**2 + (y - re.center_y_m)**2 <= re.radius_m**2`
     - Assert `np.any(left_mask)`, `np.any(right_mask)`, `not np.any(left_mask & right_mask)`, `np.array_equal(left_mask | right_mask, sol.conductor_mask)`, and `not np.any(sol.conductor_mask & sol.boundary_mask)` (rejects unexpected/merged bodies or mask mismatch).
   - **Exact margin & snapped-box reconstruction:** Compute `margin_x`, `margin_y`, and `wall_margin = 2.5 * h` using the exact formulas of `electrostatics_numerics.py` L415–445, then snap `c_left`, `c_right`, and `c_enclosure_inner` to exact index boxes `(ix_min, ix_max, iy_min, iy_max)` via `int(np.clip(np.argmin(np.abs(coords - bound)), 1, n - 2))`.
   - **Strict boolean interior & perimeter invariants:** For each contour box `B = (x0, x1, y0, y1)`, verify `x0 < x1` and `y0 < y1`, build strict interior mask `inside = zeros((n, n), bool); inside[x0+1:x1, y0+1:y1] = True`, and assert:
     - All 4 snapped perimeter edge slices lie 100% in `sol.vacuum_mask`.
     - `c_left`: `np.sum(left_mask & ~inside) == 0` (zero left-electrode nodes outside strict interior) AND `np.sum((right_mask | sol.boundary_mask) & inside) == 0`.
     - `c_right`: `np.sum(right_mask & ~inside) == 0` AND `np.sum((left_mask | sol.boundary_mask) & inside) == 0`.
     - `c_enclosure_inner`: `np.sum(sol.conductor_mask & ~inside) == 0` AND `np.sum(sol.boundary_mask & inside) == 0`.
     - Strict contour disjointness (`x1_L < x0_R or x1_R < x0_L or y1_L < y0_R or y1_R < y0_L`) and strict containment of both `c_left` and `c_right` boxes inside `c_enclosure_inner` (`x0_enc < x0_k` and `x1_k < x1_enc`, and analogously for `y`).
   - **Fail-Closed Rule:** If any post-solve mask or contour check fails, the Laplace field solve may still return `200`, but all force-budget values are withheld (`force_budget: null`, `force_budget_status: "WITHHELD_INVALID_CONTOUR_TOPOLOGY"`, with explicit diagnostic identifying the failed invariant).

### 3.2 Validated 2D Benchmark Presets & Full Enabled Slider Ranges (`V1-SPEC-R2-F1`)

Every V1 preset cleanly passes Section 3.1 across **all** `n` $\in \{41, 81, 101\}$ and uses distinct geometries without relabeling either P0/P1 or 3D Exodus:

| Preset ID | Physical Geometry & Potentials | Default `n` & Probe | Verified Slider Range (Valid Across All `n` $\in \{41, 81, 101\}$) | Expected Force Closure Behavior |
| --- | --- | --- | --- | --- |
| **`p0_p1_canonical_40mm`** *(Default P0/P1 Reference)* | `W = 0.040 m`, `r_L = r_R = 0.003 m`, `center_x = -/+ 0.008 m`, `cy = 0.0 m`, `d = 0.010 m`, `V_L = +500 V`, `V_R = -500 V` | `n = 101`, `probe = [0.0, 0.0]` | Symmetric gap `d in [6.0, 16.0] mm` (`center_x = -/+ (d/2 + 3 mm)` gives `wall >= 6 mm = 6h` at `n=41`), `V in [-50000, +50000] V` | `BALANCED_WITHIN_TOLERANCE` across `n in {41, 81, 101}` (`|F_net| ~ 10^-9 to 10^-18 N/m < 1e-4 N/m`) |
| **`asymmetric_hv_80mm_bench`** *(Asymmetric HV Enclosure Coupling)* | `W = 0.080 m`, `r_L = r_R = 0.007 m`, `center_x = -/+ 0.015 m`, `cy = 0.0 m`, `d = 0.016 m`, `V_L = -20000 V`, `V_R = 0 V` | `n = 101`, `probe = [0.0, 0.0]` | Symmetric gap `d in [12.0, 28.0] mm` (`r = 7 mm >= 6 mm = 3h`; `wall >= 12 mm = 6h` at `n=41`), `cy in [-20, +20] mm`, `V in [-50000, +50000] V` | At `n = 101, 81`: `BALANCED_WITHIN_TOLERANCE` (`|F_net| ~ 6.4e-5 to 7.8e-5 < 1e-4 N/m`); at `n = 41`: nonzero enclosure reaction (`~0.080 N/m`) with honest **`UNBALANCED_EXCEEDS_TOLERANCE`** (`|F_net| ~ 7.16e-4 >= 1e-4 N/m`) |
| **`bipolar_hv_80mm_bench`** *(Bipolar Contrast Benchmark)* | `W = 0.080 m`, `r_L = r_R = 0.007 m`, `center_x = -/+ 0.015 m`, `cy = 0.0 m`, `d = 0.016 m`, `V_L = -10000 V`, `V_R = +10000 V` | `n = 101`, `probe = [0.0, 0.0]` | Identical `[12.0, 28.0] mm` gap envelope valid across all `n in {41, 81, 101}` | Contrasts suppressed enclosure reaction (`~0` by symmetry) against asymmetric `-20 kV / 0 V` image forces |

- **Explicit Non-Conflation Note:** When UI widgets adjust geometry, client slider `min`/`max` enforces the exact active preset's valid `n`-aware domain `[max(5 mm, 6h), W - 4r - 12h]` (`max_d` for equal `r`, centered geometry) and disables controls outside valid bounds; the server independently enforces Section 3.1 on every `POST /api/v1/solve` and `POST /api/v1/study` call.

### 3.3 Full 6-Component Budget, Gated Studies & Separated Numerical Quality (`V1-SPEC-R2-F2`, `V1-SPEC-R2-M1`)

1. **Full 6-Component Force Budget (`N/m`) & Strict `<` Threshold:**
   - Exposes `left_electrode_fx_n_per_m`, `left_electrode_fy_n_per_m`, `right_electrode_fx_n_per_m`, `right_electrode_fy_n_per_m`, `enclosure_reaction_fx_n_per_m`, `enclosure_reaction_fy_n_per_m`, `net_electrostatic_force_fx_n_per_m`, `net_electrostatic_force_fy_n_per_m`, `net_electrostatic_force_norm_n_per_m`, `relative_closure_residual`, `tolerance_n_per_m = 1e-4`, `is_force_balanced_to_tolerance` (exact strict **`norm < tolerance_n_per_m`** matching `electrostatics_numerics.py` L458; equality `norm == tolerance_n_per_m` yields **`False`**), and `force_closure_status` (`"BALANCED_WITHIN_TOLERANCE"` | `"UNBALANCED_EXCEEDS_TOLERANCE"`).
   - **Narrative Replacement Rule (`V1-SPEC-R2-M1`):** Because `unmodeled_reaction_explanation` (`electrostatics_numerics.py` L460–469) states unconditionally that the system is balanced and net mechanical force is zero, V1 **never displays raw `unmodeled_reaction_explanation` when unbalanced**. Instead, UI and API emit two separate fields:
     - `continuum_and_unmodeled_supports_note`: explains continuum conservation ($F_L + F_R + F_{\text{enc}} \to 0$ as $h \to 0$) and unmodeled laboratory standoffs/feedthroughs.
     - `discrete_closure_verdict`: reports this exact grid's measured `|F_net|` vs `tolerance_n_per_m` (`<` balanced vs `>=` amber/red warning; **$V^2$ scaling disclosure**).
2. **Per-Level Gate Enforcement for Force & Probe Studies (`V1-SPEC-R2-F2`):**
   - Applies to `POST /api/v1/solve` (`include_convergence_study: true`), `POST /api/v1/study`, AND `scripts/generate_v1_snapshots.py`.
   - For **every** `n` in `study_n_list = (41, 81, 101)`:
     - Run Section 3.1 pre-solve eligibility AND post-solve snapped-contour topology validation at that `n` **before** emitting any study results.
     - Only if **all** levels in `study_n_list` pass both Section 3.1 gates may the adapter invoke `force_mesh_convergence_study(n_list=study_n_list, config=canonical_config)` on identical canonical parameters (or `electrode_pair_mesh_study` + `assess_probe_convergence` for `probe_study`).
     - If **any** resolution fails pre-solve eligibility or post-solve topology: return **zero** study force rows and zero derived sensitivities (`rows: []`, `derived_sensitivity: null`), set `force_study.status` to `"WITHHELD_INELIGIBLE_MESH_LEVEL"` or `"WITHHELD_INVALID_CONTOUR_TOPOLOGY"` with `failed_levels` and per-level reasons, while **retaining any independently valid primary single-grid `solution` and `force_budget`** on `/api/v1/solve`.
3. **Observed-Order Suppression for `(41, 81, 101)` & Explicit Multi-Threshold Reporting (`V1-SPEC-R2-F2`):**
   - `electrostatics_numerics.py` L577 computes a single `h_ratio = rows[-3].grid_spacing_m / rows[-2].grid_spacing_m` (`2.0` for `41->81`, while `81->101` is `1.25`). For `(41, 81, 101)`, V1 **must suppress all observed-order fields** (`observed_order_left_electrode: null`, `observed_order_right_electrode: null`, `observed_order_enclosure: null`, `observed_orders_by_component: null`, and every nested `component_assessments[k].observed_order: null`, setting `observed_order_status: "NOT_COMPUTED_NONUNIFORM_H_RATIO"`) and report only two-grid differences (`per_component_last_step_diff_n_per_m`, `max_component_last_step_diff_n_per_m`, `max_relative_change_to_prev`). Equal-ratio refinement triplets (e.g., `(41, 81, 161)`) require a separate future runtime/grid spec.
   - Four distinct numerical quality metrics & distinct thresholds reported separately without conflation:
     1. **Post-solve discrete 5-point Laplace stencil defect (`V`):** `max_discrete_stencil_defect_v` from direct sparse `spsolve` (`electrostatics_baseline.py` L277–281 — *not* an iterative stopping residual).
     2. **Single-grid force closure residual (`N/m`):** `net_electrostatic_force_norm_n_per_m` tested strictly `< 1e-4 N/m`.
     3. **Multi-grid force study thresholds (distinct from single-solve `1e-4`):** `force_mesh_convergence_study` internally passes `tolerance_n_per_m = 1e-3 N/m` per row (`L733`), while `evaluate_force_convergence_from_rows` (`L552–556`) defaults to `tolerance_residual_n_per_m = 1e-6 N/m`, `tolerance_relative_change = 0.05`, `tolerance_abs_change_n_per_m = 5e-4 N/m`, `tolerance_near_zero_abs_n_per_m = 1e-6 N/m`, and `significant_force_threshold_n_per_m = 1e-6 N/m`. Every threshold is labeled explicitly alongside its scope (`single_solve_1e-4` vs `study_row_1e-3` vs `study_convergence_1e-6`).
     4. **Probe field stability (`V/m`):** `probe_stability_status: "NOT_ASSESSED"` on single solves; on gated multi-grid studies reports `assess_probe_convergence` `is_stable` and `convergence_status` (`is_converged` remains `False`).

---

## 4. API Schema, Serialization, Debounce Invalidation & Local Security Contract

### 4.1 Exact Request Schema, Ordering, Probes & Canonical Fingerprint (`V1-SPEC-R2-M1`)

- All requests require JSON objects with `additionalProperties: false`. Booleans (`isinstance(v, bool)`), non-finite numbers (`NaN`, `Infinity`), strings for numbers, and missing required keys fail with HTTP `400`.
- **`POST /api/v1/solve` schema:**
  - `request_id`: required integer `>= 1`.
  - `mode`: required `"parallel_plate_1d"` | `"grounded_box_2d"`.
  - `parameters`: required object:
    - When `mode == "parallel_plate_1d"`: `{ voltage_v: [0.0, 50000.0], gap_m: [0.005, 0.200], area_m2: [1e-4, 0.05] }` (all required; `probe_xy_m` and `include_convergence_study` rejected with `400` in 1D mode).
    - When `mode == "grounded_box_2d"`: `{ n: 41 | 81 | 101, box_width_m: [0.04, 0.20], left_electrode: ElectrodeSchema, right_electrode: ElectrodeSchema }` where `ElectrodeSchema` requires `{ center_x_m: float, center_y_m: float, radius_m: [0.0015, 0.015], voltage_v: [-50000.0, 50000.0] }`.
  - Optional `probe_xy_m` (`grounded_box_2d` only; default `[0.0, 0.0]`): 2-element finite float list. Outside `[-W/2, W/2]^2` rejects with `400` (`INVALID_PROBE_COORDS`); inside boundary or conductor returns `200` with `probe_status: "NON_VACUUM"`, `probe_potential_v` as finite Dirichlet/boundary scalar, and **`probe_ex_v_per_m: null`, `probe_ey_v_per_m: null`**.
  - Optional `include_convergence_study` (`grounded_box_2d` only; default `false`): boolean. Runs Section 3.3 gated `(41, 81, 101)` force + probe study.
- **`POST /api/v1/study` schema:** Same as `grounded_box_2d` solve (`mode` must be `"grounded_box_2d"`), plus optional `study_n_list` (if supplied in V1, must equal `[41, 81, 101]`; other sequences rejected with `400`). Schema-valid requests whose coarse levels fail Section 3.1 return `200` with `force_study.status = "WITHHELD_INELIGIBLE_MESH_LEVEL"` or `"WITHHELD_INVALID_CONTOUR_TOPOLOGY"` and empty `rows: []`.
- **Canonical `input_fingerprint`:** `sha256` hex digest of `json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"), allow_nan=False)` containing `mode`, normalized SI numeric `parameters` (`float(v) + 0.0` normalizing `-0.0` to `0.0`), `probe_xy_m`, and `include_convergence_study`/`study_n_list`, **excluding** ephemeral `request_id`. Echoed in every `200` response along with `request_id`, `epistemic_label: "ESTABLISHED MODEL"`, `constants`, and `provenance`.

### 4.2 Strict RFC 8259 Serialization & Pre-Debounce Generation Invalidation (`R1-M2`, `V1-SPEC-R2-M2`)

- **Serialization & Axes:** Python serializes all responses with `json.dumps(payload, allow_nan=False)`; verifies finiteness on `potential_v` and `ex/ey[vacuum_mask]`; encodes `~vacuum_mask` cells in `ex_v_per_m`/`ey_v_per_m` explicitly as JSON `null` alongside boolean masks; includes `grid_axes: {"coords_m": [...], "shape": [n, n], "axis_0": "x_m", "axis_1": "y_m", "indexing": "ij"}`.
- **Synchronous Pre-Debounce Invalidation (`V1-SPEC-R2-M2`):**
  - Client maintains synchronous state tuple `(clientStateGeneration, currentCanonicalFingerprint, activeModelMode, activeViewContext, latestDispatchedRequestId)`.
  - On **every** slider/input change, preset selection, grid resolution change, mode transition (including `A -> B -> A` re-entry), chapter transition, Chapter 5 toggle, `Explore Freely` switch, or offline-fallback transition — executed **synchronously BEFORE starting the `150 ms` debounce timer**:
    1. Increment `clientStateGeneration += 1`, compute updated `currentCanonicalFingerprint`, and update `activeModelMode` / `activeViewContext`.
    2. Clear any pending debounce timer (`clearTimeout`) and invoke `AbortController.abort()` on any in-flight `fetch`.
    3. Immediately clear/invalidate live computed readouts and 2D overlays (`solveState = "pending"` or hidden view).
  - On **both success and error completion** of any network callback, commit UI state **only if all five match**:
    `capturedGen === clientStateGeneration && resp.input_fingerprint === currentCanonicalFingerprint && capturedMode === activeModelMode && capturedView === activeViewContext && resp.request_id === latestDispatchedRequestId`. Otherwise silently discard.

### 4.3 Local Bridge Isolation, Framed Reads & Hard-Cancellable Worker Concurrency (`V1-SPEC-R2-M3`)

In `run_explorer.py`:
- **Strict IPv4 Loopback Allowlist:** `create_server(host, port)` validates `host` $\in \{\text{"127.0.0.1"}, \text{"localhost"}\}$ (`socket.AF_INET` exclusively) and raises `ValueError` for `"::1"`, `"0.0.0.0"`, or external addresses.
- **Origin, Host, Framing & Slow-Read Bounds:**
  - Validate `Host` matches bound loopback host/port and same-origin `Origin` matches `http://127.0.0.1:<port>` or `http://localhost:<port>` on `POST /api/v1/*` (`403` otherwise; **zero** `Access-Control-Allow-Origin: *` headers).
  - Require `Content-Type: application/json` (`415` otherwise).
  - Reject missing `Content-Length` (`411`), negative/non-integer/duplicate `Content-Length` (`400`), any `Transfer-Encoding` header (`501`), and `Content-Length > 8192` (`413`).
  - Enforce **wall-clock total header + body read deadline `total_read_deadline_s = 2.0 s`** (independent of per-`recv` activity, returning `408` on slow-trickle reads) alongside `socket.settimeout(2.0)`.
- **Pre-Thread Admission & Shared Hard-Cancellable Single-Slot Compute Worker:**
  - `ThreadingHTTPServer` (`daemon_threads = True`, bounded active HTTP worker semaphore `max_active_http_workers = 8`; excess concurrent HTTP handshakes rejected immediately with `503` before queuing compute).
  - **Shared Single Compute Slot (`max_concurrent_computes = 1`):** Both `POST /api/v1/solve` and `POST /api/v1/study` acquire a single non-blocking `_compute_lock.acquire(blocking=False)` up front; concurrent solve/study calls immediately receive `429 Too Many Requests`.
  - **Isolated Single Worker Process (`multiprocessing.get_context("spawn")`):** Solve/study work runs in one persistent child worker process importing only the allowlisted kernel modules. A request applies `response_deadline_s = 5.0 s`; on expiry, the bridge calls `proc.kill()`, waits up to `worker_reap_timeout_s = 2.0 s` (`proc.join`) to ensure OS process termination, respawns a fresh worker **only after reaping completes**, **retains `_compute_lock` until the dead process has exited/reaped** (preventing overlapping SciPy computes), and returns HTTP `504` (`SOLVE_DEADLINE_EXCEEDED`). Server shutdown (`close()` / `SIGINT`) cleanly terminates/kills and reaps the worker within `2.0 s`.

---

## 5. True Offline Delivery, Visual Separation & Iceberg Preservation (`R1-M4` Closed)

- **`file://` & Static HTTP Compatibility:** Bundles precomputed snapshots for all three Section 3.2 presets (each vetted through Section 3.1/3.3 per-level gates by `scripts/generate_v1_snapshots.py`) in `explorer/v1_reference_snapshots.js` (`window.V1_REFERENCE_SNAPSHOTS` loaded via `<script>` alongside JSON parity fixture). 1D analytic parity uses exact closed-form JS (`max(1e-15, 1e-12 * max(|js|, |py|))`, exact `0.0` at `0 V`). Offline 2D locks to static presets, disables arbitrary 2D geometry/voltage/grid recalculation controls, and banners `SOLVER BRIDGE OFFLINE`.
- **Visual & Curriculum Separation:** Dedicated 2D benchmark cross-section viewport (with `x/y (mm)` axes and `N/m` budget vector readout) hides schematic 3D `forceGroup` arrows when computed 2D mode is active (zero `N/m` arrows attached to the 3D Exodus blade). All 6 Iceberg chapters, mobile 375px/390px layouts, `Explore Freely`, and Chapter 5 overlay suppression remain intact.

---

## 6. Validation Plan & Independent Acceptance Criteria

### 6.1 Required Automated Test Suites (Implementation Phase — Pending Spec Acceptance + Owner Kickoff)

1. **`tests/test_v1_solver_bridge.py`:**
   - **1D Parity & Exact Bounds:** JS/API parity against `parallel_plate_benchmark` (`max(1e-15, 1e-12 * max(|js|, |py|))`, exact zero at `0 V`, `EPSILON_0_F_PER_M = 8.8541878188e-12`).
   - **Preset Positives + Off-Axis Nonzero `Fy` (`R2-F1`):** Presets `p0_p1_canonical_40mm`, `asymmetric_hv_80mm_bench`, `bipolar_hv_80mm_bench` across slider extrema (`[6, 16] mm` / `[12, 28] mm`) and all `n in {41, 81, 101}`, plus eligible off-axis case (`Fy != 0`).
   - **Separated Schema vs Pre-Solve vs Post-Solve Withholding (`R2-F1`):**
     - *Schema `400`:* `r = 0.0005 m`, `bool` inputs, unknown keys, `n = 121`, `NaN`, swapped `probe_xy_m` outside box (`400`), valid non-vacuum `probe_xy_m` returning `200` with `probe_ex_v_per_m: null`.
     - *Pre-solve `400 INVALID_FORCE_DOMAIN`:* schema-valid `r = 0.002 m` at `W = 0.080 m, n = 41`, `< 6h` clearances, swapped `left.center_x_m >= right.center_x_m`, and **diagonal/off-axis negative test** (Euclidean separation `> 6h`, e.g. `cx = -/+0.002 m, cy = -/+0.012 m, r = 0.006 m` at `W = 0.080 m, n = 41`, rejected because x-projection gap `< 6h`).
     - *Post-solve `200 WITHHELD_INVALID_CONTOUR_TOPOLOGY`:* direct adapter test feeding an un-gated solved diagonal/tight `FieldSolution` and synthetic wrong-enclosure/merged mask into the post-solve topology gate (`force_budget is None` while `potential_v` succeeds).
   - **Multi-Grid Study Gating, Order Suppression & Multi-Threshold Tests (`R2-F2`):** Valid-fine/invalid-coarse test (`W = 0.080 m, r = 0.003 m, cx = -/+0.012 m, cy = 0.0` at `n = 101`: single-grid `/solve` `200` succeeds while `(41, 81, 101)` study returns `WITHHELD_INELIGIBLE_MESH_LEVEL` with `rows == []`), post-solve topology failure at `n = 41` withholding study, `observed_order_* is None` (top-level and nested `component_assessments[*].observed_order`) for `(41, 81, 101)`, strict `<` boundary equality test (`norm == tolerance_n_per_m` -> `is_force_balanced_to_tolerance is False`), unbalanced `n = 41` `-20 kV` honest reporting (`continuum_and_unmodeled_supports_note` separated from `UNBALANCED_EXCEEDS_TOLERANCE`), and `V^2` scaling test.
   - **HTTP Framing, Worker Timeout/Slot Retention & IPv4 Security (`R2-M3`):** Reject `create_server("::1", ...)` and `create_server("0.0.0.0", ...)` (`ValueError`); reject `Host`/`Origin` mismatch (`403`), non-JSON (`415`), `> 8192` bytes (`413`), missing (`411`), duplicate (`400`), `Transfer-Encoding: chunked` (`501`), and slow-trickle reads exceeding `2.0 s` wall clock (`408`); prove concurrent `/solve`+`/study` gets `429`; prove hung child worker returns `504`, keeps `_compute_lock` held until process exit/reap completes, then recovers cleanly to `200` on next solve.
   - **Offline Snapshot Parity & P2 Isolation Guard (`R1-M4`):** Verify `generate_v1_snapshots.py` passes Section 3.1/3.3 gates and matches JS/JSON parity, kernel SHA-1 hashes match (`97f65dfa...`, `a29f1f3a...`), and zero P2 imports exist.
2. **Playwright V1 Browser Tests (`tests/test_v1_browser_smoke.py` + preserved V0–V0.2 suite):**
   - Live bridge slider sweeps, `0 V` null parity, `#slider-eps` invariance + `VISUAL PROXY ONLY` badge, unbalanced banner display (raw narrative never claiming balance), and hidden 3D `forceGroup` in computed mode.
   - **Concurrency & View-Transition Races (`R2-M2`):** Delayed `200` AND delayed `500` responses arriving inside the `150 ms` debounce window after a newer move; rapid `A -> B -> A` mode switch while `A` is in flight; Chapter 5 entry while solve/study is in flight.
   - **True Offline Dual-Transport:** Both `file://.../explorer/index.html` and static `http.server` locked snapshot behavior + `375px`/`390px` mobile zero-overflow checks.

### 6.2 Independent V1 Acceptance Gate

V1 merges only after: (1) all P0/P1, V0–V0.2, and V1 tests pass CI with manifest provenance and intact kernel hashes; (2) independent scientific/UX review accepts exact V1 PR HEAD SHA; and (3) explicit owner merge authorization.

---

## 7. Merge Sequencing & Integrated-Tree Verification Plan (PRs #15 and #18)

1. **Preserved Draft Branch Graph:** `main` (`bc3929605300177c3ac26a579930af915c5cebea`) $\leftarrow$ Draft PR #15 (`feat/v0-1-visual-ux-polish`, accepted V0.1 SHA `55da03af781dbc1470a2bd22a7b9dfc93bbf0950`) $\leftarrow$ Draft PR #18 (`feat/v0-2-learn-physics-backwards`, accepted V0.2 SHA `634437f70e6b2bdd5b3bd41d6b77cbe551078f05` + doc-only R1–R3 revisions).
2. **Step 1 (Owner-Authorized):** Owner marks PR #15 ready and authorizes merge to `main` (do not delete `feat/v0-1-visual-ux-polish` until PR #18 is retargeted); verify integrated `main` tree CI (`140+` tests + manifest provenance).
3. **Step 2 (Owner-Authorized):** Retarget PR #18 base to `main`, verify `git diff main..PR18_HEAD` matches accepted V0.2 + doc revisions and fresh CI passes (`157` tests + manifest provenance), then merge PR #18 to `main` and verify integrated `main` CI.
4. **Step 3:** Only after V1 Specification R3 acceptance and explicit owner kickoff authorization, create a new V1 implementation branch and draft PR. Keep Draft PR #11 (P2 R10) strictly isolated on Track B.
