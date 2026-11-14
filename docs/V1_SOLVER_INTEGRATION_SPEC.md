# V1 Specification & Implementation Plan — Validated P0/P1 Solver Integration

**Status:** Proposed specification for owner review (prepared from frozen V0.2 accepted baseline SHA `634437f70e6b2bdd5b3bd41d6b77cbe551078f05`).  
**Target Track:** Track A — Visual Explorer V1 (stacked on V0.2 after owner-authorized branch/PR sequencing).  
**Track B Isolation:** Uses **only** accepted P0 (`electrostatics_baseline.py`) and P1 (`electrostatics_numerics.py`) calculations merged on `main` (`8e1fdb32655d073002ae5a794b08e48f19a78a0f`). **Zero unaccepted P2 calculations, geometries, or H0/H1 patent claims** from [Draft PR #11](https://github.com/aguacatero/scalar-wave-viz/pull/11) may be imported or exposed in V1.

---

## 1. Purpose & Baseline Anchor

V0.2 delivered an independently accepted 3D educational visual experience ([Draft PR #18](https://github.com/aguacatero/scalar-wave-viz/pull/18), canonical R6 acceptance [`issuecomment-6871100151`](https://github.com/aguacatero/scalar-wave-viz/pull/18#issuecomment-6871100151), code SHA `634437f70e6b2bdd5b3bd41d6b77cbe551078f05`) using **schematic** field streamlines and bounded force arrows over an Exodus-inspired 3D single-stage electrode layout.

V1 advances the [visual product vision](PROPULSION_EXPLORER_VISION.md) by connecting interactive parameter controls to **supported, validated conventional electrostatic solvers** while maintaining strict epistemic separation between:
1. **ESTABLISHED MODEL (COMPUTED):** Quantitative outputs from validated P0/P1 solvers (`parallel_plate_benchmark`, `electrode_pair_in_grounded_box`, `evaluate_whole_apparatus_force_budget`).
2. **PROVISIONAL ILLUSTRATIVE SCENE (SCHEMATIC):** The 3D Exodus-inspired knife-edge wedge geometry, schematic streamlines, and dielectric visual proxy.
3. **TOY MATHEMATICAL ILLUSTRATION:** The isolated Chapter 5 mathematical scalar-wave contrast view.

V1 **never** claims whole-body propellantless thrust, **never** presents 2D `N/m` cylinder-in-box results as 3D Exodus knife-edge predictions, and **always** enforces closed-system force accounting.

---

## 2. Validated P0/P1 Solver Scope vs. Excluded P2 Scope

### 2.1 Supported P0/P1 Calculations

| V1 Solver Mode | Validated Python API | Inputs & Units | Computed Outputs & Units | Validity & Limitations Exposed in UI |
| --- | --- | --- | --- | --- |
| **1D Ideal Parallel-Plate Analytic Benchmark** | `electrostatics_baseline.parallel_plate_benchmark`<br>`electrostatics_baseline.verify_plate_force_virtual_work` | `voltage_v` (`V`), `gap_m` (`m`), `area_m2` (`m²`) | `electric_field_v_per_m` (`V/m`), `pressure_pa` (`Pa`), `force_on_positive_plate_n` (`+N`), `force_on_negative_plate_n` (`-N`), `net_pair_force_n` (`0.0 N`), `stored_energy_j` (`J`), fixed-$V$ / fixed-$Q$ virtual-work check | Assumes infinite planar conductors in homogeneous vacuum ($\varepsilon_r = 1.0$); neglects fringing fields (displays automatic fringing warning when $\sqrt{A}/d < 5$). Not a 3D blade or dielectric solver. |
| **2D Cylindrical Electrodes in Grounded Square Box** | `electrostatics_baseline.electrode_pair_in_grounded_box`<br>`electrostatics_numerics.evaluate_whole_apparatus_force_budget`<br>`electrostatics_numerics.assess_probe_convergence` | `GroundedBoxConfig`: `n` $\in \{41, 81, 101\}$, `box_width_m` (`m`), `left_electrode` & `right_electrode` (`center_x_m`, `center_y_m`, `radius_m`, `voltage_v`) | 2D potential slice $V(x,y)$ (`V`), masked vacuum field $(E_x, E_y)$ (`V/m`, `NaN` on conductors/boundary), max discrete residual (`V`), `WholeApparatusForceBudget` (`N/m`): `left_electrode_fx_n_per_m`, `right_electrode_fx_n_per_m`, `enclosure_reaction_fx_n_per_m`, `net_electrostatic_force_fx_n_per_m`, `is_force_balanced_to_tolerance` | **2D cross-section only (`N/m` force per unit depth, not 3D `N`)**; circular conductors in $0\text{ V}$ grounded square enclosure (not 3D tapered Exodus blade); homogeneous vacuum ($\varepsilon_r = 1.0$, no solid dielectric potting); $O(h)$ staircase boundary discretization; peak $|E|$ is grid-sensitive; mechanical standoffs/supports are unmodeled (`unmodeled_reaction_explanation`). |

### 2.2 Explicitly Excluded / Deferred Scope

- **No P2 imports:** No imports or code copies from unaccepted P2 modules (`p2_*` or Draft PR #11). Specifically, 3D tapered blade + inhomogeneous dielectric potting FEM/BEM solves and US11511891B2 Eq. (11) H1 predictions remain outside V1 until P2 passes independent scientific review and owner-authorized merge.
- **No dielectric field recalculation in V1:** The existing `#slider-eps` dielectric permittivity slider ($\varepsilon_r \in [1, 5]$) **remains explicitly tagged `VISUAL_MATERIAL_PROXY_ONLY`** and must **not** scale or modify P0/P1 vacuum solver outputs.
- **No `scalar_wave_3d.py` propulsion coupling:** `scalar_wave_3d.py` remains strictly separate from propulsion claims; Chapter 5's mathematical scalar-wave view remains an isolated educational contrast.

---

## 3. Architecture: Local Solver Bridge & Offline/Static Compatibility

### 3.1 Mode A — Local Python Solver Bridge (`run_explorer.py`)

Extend `ExplorerHTTPRequestHandler` in `run_explorer.py` (bound strictly to `127.0.0.1` local loopback) with:
- `GET /api/v1/capabilities`: reports active solver status, supported models, grid cap (`n <= 121`), and provenance revision.
- `POST /api/v1/solve`: validates JSON payload against strict schema (`model_id`, finite floats, integer grid `n`, continuous geometry clearance checks from `GroundedBoxConfig`), executes the P0/P1 solver synchronously with bounded runtime, and returns:
  - `epistemic_label`: `"ESTABLISHED MODEL"`
  - `model_id`: `"parallel_plate_1d"` | `"grounded_box_2d"`
  - `parameters`: echoed canonical SI inputs and source units
  - `results`: computed fields, forces, energies, residuals, and optional downsampled 2D slice grid (`V`, `Ex`, `Ey`, `vacuum_mask`) for canvas visualization
  - `force_budget`: complete component + enclosure reaction accounting (`N` for 1D, `N/m` for 2D)
  - `uncertainty_and_limits`: grid spacing `h`, `max_discrete_residual_v`, mesh/discretization sensitivity notes, virtual-work relative discrepancy reference, validity warnings (e.g., fringing or near-wall warning)
  - `provenance`: module/function names, pinned git commit/revision, `whole_body_thrust_status: "NOT MEASURED / NOT ESTABLISHED"`.

### 3.2 Mode B — Static / Offline Fallback (`file://` or `python -m http.server`)

To preserve V0–V0.2's zero-build offline usability when the Python bridge is unavailable:
- **1D Parallel-Plate Analytic:** May run exact closed-form JS evaluation (`E = V/d`, `p = 0.5 * eps0 * E^2`, `F = ±p*A`, `U = 0.5 * eps0 * E^2 * A * d`, `net = 0`) verified by automated unit tests to match Python `parallel_plate_benchmark` within $10^{-12}$ relative error, clearly labeled `ESTABLISHED MODEL (1D ANALYTIC — CLIENT-SIDE EXACT)`.
- **2D Grounded-Box FD Laplace:** **Fails closed** when `/api/v1/solve` is unavailable—**never** approximates a 2D PDE solve in JS. Instead:
  - Ships deterministic precomputed P0/P1 reference snapshots (`explorer/v1_reference_snapshots.json`, generated reproducibly via `scripts/generate_v1_snapshots.py` from `electrostatics_baseline.py` and `electrostatics_numerics.py`) for preset configurations (e.g., symmetric $\pm 500\text{ V}$, asymmetric $-20\text{ kV}$ vs $0\text{ V}$, off-axis enclosure test).
  - Displays a clear banner: `STATIC REFERENCE SNAPSHOT — Launch python run_explorer.py for live arbitrary-parameter 2D Laplace recalculation`.

---

## 4. Interactive Control Bindings & Epistemic UI Contract

### 4.1 Parameter Mapping & Clamping Rules

1. **Applied Voltage (`#slider-voltage`, $0 - 50\text{ kV}$):**
   - Maps to `voltage_v = currentVoltageKV * 1000` in 1D Parallel-Plate, and in 2D Grounded-Box to either:
     - *Asymmetric Grounded-Box Preset* (`left_voltage_v = -V`, `right_voltage_v = 0.0`, matching V0.2's cathode/ground polarity convention), or
     - *Symmetric Bipolar Preset* (`left_voltage_v = +V/2`, `right_voltage_v = -V/2`, matching P0/P1's default `±500 V` benchmark).
   - At `0.0 kV`, all computed fields, pressures, energies, and forces report exact `0` with units (`0.00 kV/m`, `0.00 Pa`, `0.00 N` / `N/m`).
2. **Electrode Gap (`#slider-gap`, $16 - 50\text{ mm}$):**
   - Maps to `gap_m = currentGapMM * 1e-3` in 1D Parallel-Plate and surface-to-surface separation `d_inter` in 2D Grounded-Box (adjusting symmetric `±center_x_m` while validating `abs(cx) + r < box_width_m / 2`).
   - Invalid configurations (e.g., box width smaller than electrode span + wall clearance) return a structured `400` validation error rendered inline without crashing or displaying stale results.
3. **V1 Benchmark Controls (inside dedicated Computed Solver Panel / Tab):**
   - Model selector: `1D Parallel-Plate (Analytic)` vs `2D Cylinders in Grounded Box (FD Laplace)` vs `3D Schematic Only (V0.2 View)`.
   - 1D Plate Area `area_cm2` ($1 - 100\text{ cm}^2$, default $10\text{ cm}^2$).
   - 2D Box Width `box_width_mm` ($40 - 160\text{ mm}$, default `80 mm` or `40 mm` benchmark), Electrode Radius ($1.5 - 6.0\text{ mm}$, default `3.0 mm`), Grid Resolution `n` $\in \{41, 81, 101\}$.
4. **Dielectric Permittivity (`#slider-eps`, $1.0 - 5.0$):**
   - Explicitly locked out of P0/P1 vacuum solver calculations with an inline badge: `VISUAL PROXY ONLY — Vacuum solver uses εᵣ = 1.0`.

### 4.2 Visual Separation of Computed vs. Schematic Overlays

- **3D Viewport Layer Separation:**
  - Optional `Computed 2D Field Slice (z=0)` overlay renders the solved 2D potential/field colormap inside a clearly labeled 2D cross-section frame with circular electrode footprints and grounded-box outline—never disguised as a 3D Exodus knife-edge field map.
  - Persistent viewport epistemic badge distinguishes `SCHEMATIC 3D GEOMETRY` from `COMPUTED 1D/2D P0-P1 BENCHMARK`.
- **Whole-Device Force Ledger Synchronization:**
  - In V1 Computed Mode, the Force Ledger displays a dedicated **Computed Benchmark Force Budget** card with exact units (`N` or `N/m`), showing:
    - Left Electrode Force (`+X` / `-X`), Right Electrode Force, and Grounded Enclosure Reaction (`enclosure_reaction_fx_n_per_m` in 2D), plus Net Modeled Residual (`net_electrostatic_force_fx_n_per_m`) and `is_force_balanced_to_tolerance`.
    - Explicit note whenever asymmetric voltages produce nonzero electrode force: the grounded enclosure absorbs the equal and opposite Maxwell stress reaction, and rigid mechanical supports remain unmodeled.
    - Persistent top-level invariant: `WHOLE-BODY THRUST: NOT MEASURED / NOT ESTABLISHED`.

### 4.3 Preservation of V0.2 Iceberg Learning Model

- All 6 chapters, Surface/Shallow/Deeper/Research disclosures, scene-synchronized camera framing, `Explore Freely`, `syncWaveContrastUI()`, and mobile tab layouts remain intact.
- Entering Chapter 5 mathematical scalar-wave view continues to isolate `scalarWaveGroup` and hide physical/computed field slices cleanly.

---

## 5. Validation Plan & Independent Acceptance Criteria

### 5.1 Automated Verification Suite

1. **Solver Bridge & Parity Unit Tests (`tests/test_v1_solver_bridge.py`):**
   - Verify `/api/v1/solve` matches `parallel_plate_benchmark` and `electrode_pair_in_grounded_box` + `evaluate_whole_apparatus_force_budget` directly.
   - Verify out-of-bounds / penetrating geometries, `n > 121`, and non-finite inputs fail closed with HTTP `400`.
   - Verify JS 1D analytic helper matches Python `parallel_plate_benchmark` to `< 1e-12` relative error.
   - Verify `scripts/generate_v1_snapshots.py` reproduces `explorer/v1_reference_snapshots.json` deterministically.
   - Verify static AST / import guard ensuring zero P2 module imports in `run_explorer.py` or V1 code.
2. **Epistemic Evidence Guard Extension (`tests/test_v0_propulsion_explorer.py`):**
   - Preserve all V0.2 recursive leaf checks and mutation tests on `six_chapters` and `DEFAULT_PROVENANCE_DATA`.
   - Add guard assertions verifying every V1 computed readout template binds explicit units (`N`, `N/m`, `Pa`, `V/m`), `ESTABLISHED MODEL` label, validity/discretization uncertainty, and `NOT MEASURED / NOT ESTABLISHED` whole-body thrust status.
3. **Playwright Browser Regression Tests (`tests/test_v1_browser_smoke.py` + existing `test_v0_browser_smoke.py`):**
   - All 34 existing V0.2 browser smoke tests pass unchanged.
   - Live bridge tests: voltage and gap slider changes trigger `/api/v1/solve`, update computed `E`, `p`, `F`, `N/m` budget, and `0 V` yields exact zero.
   - Asymmetric 2D run verifies nonzero electrode force and balancing enclosure reaction force appear together with `is_force_balanced_to_tolerance` status.
   - Changing `#slider-eps` does **not** alter computed P0/P1 numbers and keeps `VISUAL PROXY ONLY` warning visible.
   - Offline/static mode fails closed for live 2D solves and displays snapshot provenance warning.
   - Mobile `375px` and `390px` viewports render with zero horizontal overflow.

### 5.2 Independent V1 Acceptance Criteria

Before V1 may be marked accepted or ready for owner merge consideration:
1. All existing P0/P1 tests (`test_electrostatics_baseline.py`, `test_p1_numerics.py`, `test_p1_wave_3d.py`) and V0–V0.2 tests pass alongside the new V1 unit and Playwright tests with manifest provenance gate green.
2. Independent review confirms zero P2 calculations were imported, computed vs schematic boundaries are unambiguous in UI and 3D overlays, units/uncertainties/limitations are exposed everywhere, and whole-device force accounting remains closed-system balanced.
3. PR remains draft/unmerged until independent scientific/UX review acceptance and explicit owner merge authorization.
