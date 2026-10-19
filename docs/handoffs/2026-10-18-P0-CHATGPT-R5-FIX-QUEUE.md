# P0 Scientific Baseline — ChatGPT Independent R5 Findings / Antigravity Fix Queue

**REVIEW DISPOSITION: CHANGES REQUIRED (R5) — RESOLVED FOR R6 RE-REVIEW. PR REMAINS DRAFT.**
Date: 2026-10-18. Persistent handoff and fix ledger resolving independent review findings R5-F1 through R5-F4.

## 1. Immutable Review Baseline (R5)

- **Repository:** https://github.com/aguacatero/scalar-wave-viz
- **Draft PR:** https://github.com/aguacatero/scalar-wave-viz/pull/5
- **Branch:** `scientific-baseline-exodus-2026-10-13`
- **Reviewed Code Baseline (R5):** `4349f4be8d8795459917babcd6e597e2f97a69fe`
- **Independent R5 Review URL:** https://github.com/aguacatero/scalar-wave-viz/pull/5#pullrequestreview-5564775062
- **Owner R6 Pickup Instructions:** https://github.com/aguacatero/scalar-wave-viz/pull/5#issuecomment-6254690883
- **Verified CI at R5 HEAD:** Run 39158143469 (26 tests passed, artifact bundle 12147961595 downloaded and inspected).

---

## 2. Unresolved R5 Findings & Exact Resolutions

### R5-F1 — MED: Approximate tolerance falsely asserted exact antisymmetry

- **Finding:** `np.isclose` in `check_configuration_symmetries` marked $+500\text{ V} / -499.997\text{ V}$ as exact voltage antisymmetry because $|-499.997 - (-500.0)| = 0.003 \le 500 \times 10^{-5}$. The $0.003\text{ V}$ boundary symmetry defect was then misclassified as a numerical solver error in `potential_antisymmetry_error_v`. Near-but-not-identical geometry could also yield asymmetrical raster masks while passing approximate tolerance checks.
- **Resolution:**
  - In `electrostatics_baseline.py`:
    - Replaced `np.isclose` with exact criteria (`==`) on continuous parameters in `check_configuration_symmetries`: requires $r_L == r_R > 0$, $x_R == -x_L \neq 0$, $V_R == -V_L \neq 0$, and $y_R == y_L$ ($x$-reflection) or $y_R == -y_L$ (central inversion).
    - When `solution` is provided, also validates discrete transformed fixed masks and potentials:
      - $x$-reflection: `np.array_equal(fixed_mask, fixed_mask[::-1, :])`, `np.array_equal(conductor_mask, conductor_mask[::-1, :])`, and `np.all(potential_v[fixed_mask] + potential_v[::-1, :][fixed_mask] == 0.0)`.
      - Central inversion: `np.array_equal(fixed_mask, fixed_mask[::-1, ::-1])`, `np.array_equal(conductor_mask, conductor_mask[::-1, ::-1])`, and `np.all(potential_v[fixed_mask] + potential_v[::-1, ::-1][fixed_mask] == 0.0)`.
    - If any symmetry condition fails, fails closed to `None` error and reports `symmetry_status = 'N/A (asymmetric geometry or potentials)'`.
    - Added `check_discrete_symmetries(solution, config)`.
- **Regressions:**
  - `test_r5_f1_exact_antisymmetry_and_near_threshold_geometry`:
    - Tests $+500\text{ V}$ vs $-499.997\text{ V}$: asserts `np.isclose` is True but `check_configuration_symmetries` returns False for both symmetries; asserts mesh study records `None` and `'N/A'`.
    - Tests near-threshold geometry ($x_R = 0.0080001\text{ m}$ vs $x_L = -0.008\text{ m}$): asserts False for both symmetries, errors are `None`, status is `'N/A'`.
    - Tests discrete parity check on exact solution.

### R5-F2 — MED: Unsupported positive convergence assessment

- **Finding:** `probe_convergence_assessment` claimed "converges smoothly" for any study whose probe samples were in vacuum, regardless of actual $E_x, E_y$ values, coordinate drift across resolutions, or number of rows (even a 1-row study received a positive convergence claim). Nearest-grid sampling meant physical coordinates varied for off-grid or even-$n$ runs.
- **Resolution:**
  - Split vacuum validity from quantitative convergence.
  - In `MeshRefinementResult`: added `requested_probe_x_m` and `requested_probe_y_m`.
  - Added `ProbeConvergenceAssessment` dataclass and `assess_probe_convergence(...)`:
    - If any probe point is non-vacuum: `vacuum_status = 'NON_VACUUM'`, `convergence_status = 'NOT_ASSESSED'`.
    - If study has $< 3$ mesh resolutions (e.g. 1-row table): `convergence_status = 'NOT_ASSESSED'`.
    - If sampled coordinates drift across resolutions or deviate from requested point due to nearest-grid sampling: `convergence_status = 'INCONCLUSIVE'`.
    - If quantitative relative field variation across resolutions exceeds tolerance (e.g. wildly drifting fields): `convergence_status = 'INCONCLUSIVE'`.
    - If and only if all samples are in vacuum, $\ge 3$ resolutions, coordinates are stable, and relative drift $\le 5\%$: `convergence_status = 'CONVERGED'`, `is_converged = True`.
  - In `generate_manifest`:
    - Updated `study_table` to include `requested_probe_xy_m` and `sampled_probe_coords`.
    - Added structured `probe_convergence_details` object to `cases.case_1_grounded_box_2d`.
    - Replaced unconditional claim in `epistemic_warning` with requirement for quantitative verification.
- **Regressions:**
  - `test_r5_f2_probe_convergence_assessment_split_and_regressions`:
    - 1-row study returns `NOT_ASSESSED` and `is_converged = False`.
    - Wildly drifting all-vacuum rows ($100, 5000, 25000\text{ V/m}$) return `INCONCLUSIVE` and `is_converged = False`.
    - Off-grid target with moving sampled nodes returns `INCONCLUSIVE` and `coords_stable = False`.
    - Standard on-grid baseline returns `CONVERGED`, `coords_stable = True`, and relative drift $< 3\%$.
    - Probe in conductor returns `NON_VACUUM` and `NOT_ASSESSED`.

### R5-F3 — MED: Physical conductor intersection or wall penetration passes coarse-grid mask checks

- **Finding:** Disjoint lattice masks on coarse grids do not imply disjoint continuous disks ($n=11, W=0.04\text{ m}$, centers $-0.004\text{ m}$ and $0\text{ m}$, radii $0.0021\text{ m}$ each intersect continuously since $0.004 < 0.0042$, yet lattice masks had disjoint nodes). Similarly, off-grid disks protruding beyond the grounded enclosure wall (e.g. centered at $(0.0177, 0.001)$ with radius $0.0025\text{ m}$ in $W=0.04\text{ m}$ box where wall is at $0.02\text{ m}$) escaped boundary node checks.
- **Resolution:**
  - Implemented continuous geometry validation before rasterization in both `GroundedBoxConfig.__post_init__` and `electrode_pair_in_grounded_box`:
    1. Continuous enclosure containment: $|c_x| + r \ge W/2$ or $|c_y| + r \ge W/2$ raises `ValueError`.
    2. Continuous disk disjointness: $\sqrt{(x_R - x_L)^2 + (y_R - y_L)^2} \le (r_L + r_R)$ raises `ValueError`.
- **Regressions:**
  - `test_r5_f3_continuous_conductor_disjointness_and_enclosure_containment`:
    - Negative regression on $n=11, W=0.04\text{ m}$, centers $-0.004\text{ m}$ and $0\text{ m}$, radii $0.0021\text{ m}$: asserts `ValueError('Electrodes intersect or touch in continuous space')` in both `GroundedBoxConfig` and `electrode_pair_in_grounded_box`.
    - Negative regression on disk $(0.0177, 0.001)$ with radius $0.0025\text{ m}$ in $W=0.04\text{ m}$ enclosure: asserts `ValueError('penetrates or touches grounded enclosure boundary')` in both entry points.

### R5-F4 — LOW: Claimed figure-title regression does not inspect title

- **Finding:** The R4-F3 regression `test_render_unequal_voltages_title_and_manifest` checked manifest voltages and symmetry status, but never inspected Panel A's actual title text.
- **Resolution:**
  - Extracted `format_voltage_title(v_l, v_r) -> str` and `format_panel_a_title(cfg) -> str`.
  - Replaced ad-hoc `np.isclose` formatting in `render()` with `format_panel_a_title(cfg)`.
  - Formats non-integer symmetric voltages cleanly (e.g. $\pm 250.5\text{ V}$) and preserves full precision for near-symmetric inputs without rounding (e.g. $V_{\text{left}}=+500\text{ V}, V_{\text{right}}=-499.997\text{ V}$).
- **Regressions:**
  - `test_r5_f4_panel_a_title_formatter_and_figure_inspection`: tests symmetric ($\pm 500\text{ V}$), non-integer symmetric ($\pm 250.5\text{ V}$), asymmetric ($V_{\text{left}}=+800\text{ V}, V_{\text{right}}=-350\text{ V}$), near-symmetric ($V_{\text{left}}=+500\text{ V}, V_{\text{right}}=-499.997\text{ V}$ — asserts explicitly not formatted as $\pm 500\text{ V}$), and zero voltages.
  - `test_render_unequal_voltages_title_and_manifest`: asserts `format_panel_a_title(cfg_asym)` produces explicit unequal voltage label.

---

## 3. Test Suite Summary

- Total unit tests: **30 passed** (0 failures, 0 errors; up from 26 in R5).
- All previous regression gates (F1–F6, R2-F1–R2-F5, R3-F1–R3-F3, R4-F1–R4-F3) remain green.
- Local command: `python3 -m unittest discover -s tests -v`
