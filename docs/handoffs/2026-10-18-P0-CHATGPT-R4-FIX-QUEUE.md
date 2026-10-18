# P0 Scientific Baseline — ChatGPT Independent R4 Findings / Antigravity Fix Queue

**REVIEW DISPOSITION: CHANGES REQUESTED (R4) — RESOLVED FOR R5 RE-REVIEW. PR REMAINS DRAFT.**
Date: 2026-10-18. Persistent handoff and fix ledger resolving independent review findings R4-F1 through R4-F3.

## 1. Immutable Review Baseline (R4)

- **Repository:** https://github.com/aguacatero/scalar-wave-viz
- **Draft PR:** https://github.com/aguacatero/scalar-wave-viz/pull/5
- **Branch:** `scientific-baseline-exodus-2026-10-13`
- **Reviewed Code Baseline (R4):** `ccfc9a06e7dd0eecfe0f2f9ea155562e6f221c03`
- **Independent R4 Review URL:** https://github.com/aguacatero/scalar-wave-viz/pull/5#pullrequestreview-5564482626
- **Owner R5 Pickup Instructions:** https://github.com/aguacatero/scalar-wave-viz/pull/5#issuecomment-6253925857
- **Verified CI at R4 HEAD:** Run 38947657929 (23 tests passed, artifact bundle downloaded and inspected).

---

## 2. Unresolved R4 Findings & Exact Resolutions

### R4-F1 — MED: False negative symmetry error on asymmetric or vertically offset electrode configurations

- **Finding:** `potential_antisymmetry_error_v` in `electrode_pair_mesh_study` was calculated as $\max |V(x, y) + V(-x, y)|$, unconditionally assuming $V$ satisfies $x$-reflection antisymmetry. For custom configurations with vertical offsets ($y_{\text{left}} \neq y_{\text{right}}$) or asymmetric voltages ($V_{\text{left}} \neq -V_{\text{right}}$), this reflection antisymmetry does not physically hold for Laplace's equation. The solver was computing hundreds of volts of non-error as a failure diagnostic. Furthermore, configurations with central inversion symmetry ($x_R = -x_L, y_R = -y_L, V_R = -V_L$) were falsely flagged as lacking symmetry.
- **Resolution:**
  - Implemented `check_configuration_symmetries(config: GroundedBoxConfig) -> dict[str, bool]` to test exact geometric and Dirichlet boundary symmetry preconditions:
    1. $x$-reflection antisymmetry ($V(-x, y) = -V(x, y)$): requires $r_L = r_R$, $x_R = -x_L \neq 0$, $y_R = y_L$, and $V_R = -V_L \neq 0$.
    2. Central-inversion antisymmetry ($V(-x, -y) = -V(x, y)$): requires $r_L = r_R$, $x_R = -x_L \neq 0$, $y_R = -y_L$, and $V_R = -V_L \neq 0$.
  - In `electrode_pair_mesh_study`:
    - Evaluates `potential_antisymmetry_error_v` only when $x$-reflection preconditions hold; otherwise records `None` (`null` in JSON).
    - Evaluates `potential_central_inversion_error_v` only when central-inversion preconditions hold; otherwise records `None`.
    - Reports explicit `symmetry_status` string: `'X_REFLECTION_AND_CENTRAL_INVERSION_ANTISYMMETRIC'`, `'X_REFLECTION_ANTISYMMETRIC'`, `'CENTRAL_INVERSION_ANTISYMMETRIC'`, or `'N/A (asymmetric geometry or potentials)'`.
- **Regressions:**
  - `test_symmetry_preconditions_and_central_inversion`: exercises all four symmetry regimes (both hold, central-inversion only for opposite vertical offsets, $x$-reflection only for identical vertical offsets, and neither for unequal voltages), asserting errors are $< 10^{-10}\text{ V}$ when valid and `None` when preconditions fail.
  - `test_mesh_study_uses_custom_configuration`: asserts vertically offset custom run correctly reports `potential_antisymmetry_error_v is None` and `potential_central_inversion_error_v < 1e-10`.

### R4-F2 — MED: Probe inside conductor produced NaN and non-standard JSON serialization

- **Finding:** In custom electrode configurations where an electrode covers the mesh study probe location $(0, 0)$, sampling electric field components on conductor cells yielded `NaN` (as `ex_v_per_m` is intentionally masked to `NaN` on conductor voxels). Python's default `json.dump` serializes `float('nan')` as bare `NaN`, violating RFC 8259 standard JSON syntax and breaking strict JSON parsers.
- **Resolution:**
  - In `electrode_pair_mesh_study`:
    - Check whether probe cell is in vacuum: `probe_in_vac = bool(sol.vacuum_mask[ix, iy])`.
    - If `require_vacuum_probe=True` and probe is not in vacuum, raise an explicit `ValueError`.
    - If `probe_in_vac` is False, record `probe_ex = None`, `probe_ey = None` (`null` in JSON) and record an explanatory `probe_status` string detailing conductor/boundary placement.
    - Store `probe_in_vacuum: bool` and `probe_status: str` on `MeshRefinementResult`.
  - In `generate_manifest`:
    - Serialize `probe_in_vacuum`, `probe_status`, `potential_central_inversion_error_v`, and `symmetry_status` for each mesh study row.
    - Include high-level `probe_convergence_assessment` verifying whether all probe points were in vacuum across resolutions.
    - Bump manifest `schema_version` to `'1.2.0'`.
  - In `render`:
    - Enforce strict RFC 8259 JSON serialization: `json.dump(manifest, f, indent=2, allow_nan=False)`.
  - In `examples/electrostatics_demo.py` main printer:
    - Safely format `probe_ex_v_per_m` when `None`.
- **Regressions:**
  - `test_mesh_study_probe_inside_conductor_and_strict_json`: tests electrode covering probe point $(0, 0)$; asserts `require_vacuum_probe=True` raises `ValueError`; asserts `require_vacuum_probe=False` records `probe_in_vacuum=False`, `probe_ex_v_per_m=None`, and `probe_status` containing `'NON_VACUUM'`; generates manifest and validates strict RFC 8259 compliance via `json.loads(..., parse_constant=...)` rejecting `NaN` and `Infinity`.

### R4-F3 — LOW: Figure title assumed symmetric electrode voltages

- **Finding:** In `render()`, Panel A title was hardcoded as `f'A · Case 1: Grounded Box (±{abs(cfg.left_electrode.voltage_v):.0f} V)\nDirichlet Potential (V)'`. If run on custom configurations with unequal electrode voltages (e.g. $+800\text{ V}$ and $-350\text{ V}$), the title misleadingly printed `±800 V`.
- **Resolution:**
  - Evaluated voltage relationship dynamically: if $V_L = -V_R \neq 0$, display `±|V_L| V`; otherwise display explicit individual voltages: `V_left=..., V_right=...`.
- **Regression:**
  - `test_render_unequal_voltages_title_and_manifest`: verifies custom configuration with unequal voltages ($+800\text{ V}$ vs $-350\text{ V}$) renders properly with correct title and serializes valid manifest.

---

## 3. Test Suite Summary

- Total unit tests: **26 passed** (0 failures, 0 errors).
- All previous regression gates (F1–F6, R2-F1–R2-F5, R3-F1–R3-F3) remain green.
- Local command: `python3 -m unittest discover -s tests -v`
