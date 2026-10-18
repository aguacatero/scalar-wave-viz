# P0 Scientific Baseline — ChatGPT Independent R6 Findings / Antigravity Fix Queue

**REVIEW DISPOSITION: CHANGES REQUIRED (R6) — RESOLVED FOR R7 RE-REVIEW. PR REMAINS DRAFT.**
Date: 2026-10-18. Persistent handoff and fix ledger resolving independent review findings R6-F1 through R6-F3.

## 1. Immutable Review Baseline (R6)

- **Repository:** https://github.com/aguacatero/scalar-wave-viz
- **Draft PR:** https://github.com/aguacatero/scalar-wave-viz/pull/5
- **Branch:** `scientific-baseline-exodus-2026-10-13`
- **Reviewed Code Baseline (R6):** `28001c385577273fc2a63694a76fa8e8449444ed`
- **Independent R6 Review URL:** https://github.com/aguacatero/scalar-wave-viz/pull/5#pullrequestreview-5565058567
- **Owner R7 Pickup Instructions:** https://github.com/aguacatero/scalar-wave-viz/pull/5#issuecomment-6255397270
- **Verified CI at R6 HEAD:** Run 39164164147 (30 tests passed, artifact bundle 12150370664 downloaded and inspected).

---

## 2. Unresolved R6 Findings & Exact Resolutions

### R6-F1 — MED: Vertical central-inversion geometry falsely classified as N/A

- **Finding:** In `check_configuration_symmetries`, central inversion reused `x_antisym` which required `x_left != 0.0`. A vertical dipole centered at $(0, -0.008\text{ m})$ and $(0, +0.008\text{ m})$ with radii $0.003\text{ m}$, voltages $\pm 500\text{ V}$, and enclosure width $0.04\text{ m}$ satisfies exact physical and discrete central inversion $V(-x, -y) = -V(x, y)$ (numerical inversion error $< 1.1 \times 10^{-12}\text{ V}$), but was falsely disqualified with `symmetry_status = 'N/A'`.
- **Resolution:**
  - In `electrostatics_baseline.py` (`check_configuration_symmetries`):
    - Decoupled central inversion from $x$-reflection antisymmetry.
    - Central-inversion preconditions require $r_L == r_R > 0$, $V_R == -V_L \neq 0$, $x_R == -x_L$, $y_R == -y_L$, and spatial separation `(x_left != 0.0 or y_left != 0.0)` (non-coincident electrodes). Allows $x_L = 0$ when electrodes are separated along $y$.
    - Retained $x_L \neq 0.0$ for $x$-reflection antisymmetry because points on $x=0$ map onto themselves under $x \to -x$.
    - Preserved exact discrete parity checks on fixed masks, conductor masks, and boundary potentials.
- **Regression:**
  - Added `test_r6_f1_vertical_dipole_central_inversion_symmetry` in `tests/test_electrostatics_baseline.py`:
    - Simulates vertical dipole $(0, -0.008\text{ m})$ and $(0, +0.008\text{ m})$, $\pm 500\text{ V}$.
    - Asserts `has_central_inversion_antisymmetry` is True, `has_x_reflection_antisymmetry` is False.
    - Asserts mesh study records `potential_central_inversion_error_v < 1e-10`, `potential_antisymmetry_error_v is None`, and `symmetry_status == 'CENTRAL_INVERSION_ANTISYMMETRIC'`.
    - Negative regression: asserts coincident electrodes at $(0, 0)$ are rejected by continuous geometry validation.

### R6-F2 — MED: Convergence gate accepts duplicate meshes, direction-reversing vectors, and non-finite samples

- **Finding:** In `assess_probe_convergence`:
  1. The row-count guard `len(study_results) < 3` accepted duplicate resolutions (e.g. 3 rows of $n=41$ and $h=1\text{ mm}$).
  2. Scalar magnitude check `hypot(Ex, Ey)` accepted direction-reversing vectors (e.g. $(100, 0), (-100, 0), (100, 0)$ across 3 distinct grids yielded $\Delta |E| = 0$ and false `CONVERGED`).
  3. Non-finite data (NaN or Inf) could bypass drift checks, and calling coarse 3-mesh finite grid sampling `CONVERGED` overclaimed asymptotic mathematical convergence.
- **Resolution:**
  - In `electrostatics_baseline.py`:
    - Validates `max_relative_drift_tol` is finite and $> 0$.
    - Requires $\ge 3$ unique, distinct mesh resolutions ($n$) and grid spacings ($h$): `len({r.n for r in study_results}) >= 3` and `len({r.grid_spacing_m for r in study_results}) >= 3`; fails closed to `NOT_ASSESSED`.
    - Validates all field components $(E_x, E_y)$ are finite; any `NaN` or `Inf` fails closed to `NOT_ASSESSED`.
    - Evaluates pairwise vector distance variation relative to scale $E_{\text{scale}} = \max \|\vec{E}\|$, relative component spans $(\Delta E_x / E_{\text{scale}}, \Delta E_y / E_{\text{scale}})$, and relative magnitude variation. Vector direction reversals yield relative drift $\ge 200\% \gg 5\%$ and fail closed to `INCONCLUSIVE`.
    - Uses scientifically honest status `STABLE_WITHIN_TESTED_GRID_TOLERANCE` (with `is_converged = True` and `is_stable = True`).
- **Regressions:**
  - Added `test_r6_f2_probe_convergence_guardrails_and_counterexamples` in `tests/test_electrostatics_baseline.py`:
    - Counterexample 1 (repeated meshes): 3 rows of $n=41 \implies$ `NOT_ASSESSED` (asserts `Insufficient distinct mesh resolutions`).
    - Counterexample 2 (direction reversals): $(+100, 0), (-100, 0), (+100, 0) \implies$ `INCONCLUSIVE` (relative drift $\ge 2.0 = 200\%$).
    - Counterexample 3 (non-finite data): row with `probe_ex_v_per_m = np.nan` $\implies$ `NOT_ASSESSED` (asserts `Non-finite electric field components`).
    - Counterexample 4 (invalid tolerance): negative or NaN tolerances raise `ValueError`.

### R6-F3 — MED: Manifest hardcodes requested probe (0, 0) for non-midpoint studies

- **Finding:** In `examples/electrostatics_demo.py`, `generate_manifest` unconditionally called `assess_probe_convergence(study_results or [], requested_probe_xy_m=(0.0, 0.0))`. A valid on-grid study at $(0.001\text{ m}, 0.0\text{ m})$ was assessed against $(0, 0)$, triggering a false `INCONCLUSIVE` coordinate drift warning.
- **Resolution:**
  - In `examples/electrostatics_demo.py` (`generate_manifest`):
    - Dynamically derives and validates common requested probe coordinates from `study_results`: `{(float(r.requested_probe_x_m), float(r.requested_probe_y_m)) for r in study_results}`.
    - Passes the derived target to `assess_probe_convergence`.
    - Added `'mesh_study_probe': study_table` alongside backward-compatible `'mesh_study_probe_midpoint': study_table`.
    - Recorded `is_midpoint = (target_probe_xy == (0.0, 0.0))` and `is_stable` in `probe_convergence_details`.
  - In `render()`: allowed optional `study_probe_xy_m` and `study_n_list` arguments.
- **Regression:**
  - Added `test_r6_f3_manifest_derives_common_requested_probe_for_non_midpoint_studies` in `tests/test_electrostatics_baseline.py`:
    - Executes on-grid non-midpoint study at $(0.001\text{ m}, 0.0\text{ m})$ across $n=(41, 81, 161)$ where $x=0.001\text{ m}$ is an exact lattice node for all 3 resolutions.
    - Verifies manifest records `requested_probe_xy_m: [0.001, 0.0]`, `is_midpoint: False`, `coords_stable: True`, `relative_field_drift < 0.05`, and `STABLE_WITHIN_TESTED_GRID_TOLERANCE`.

---

## 3. Test Suite Summary

- Total unit tests: **33 passed** (0 failures, 0 errors; up from 30 in R6).
- All previous regression gates (F1–F6, R2-F1–R2-F5, R3-F1–R3-F3, R4-F1–R4-F3, R5-F1–R5-F4) remain green.
- Local command: `python3 -m unittest discover -s tests -v`
