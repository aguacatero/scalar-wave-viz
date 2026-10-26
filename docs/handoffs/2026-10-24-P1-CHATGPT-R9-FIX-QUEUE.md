# P1 R9 Independent Review Fix Queue & Remediation Ledger

**Repository:** `aguacatero/scalar-wave-viz`  
**PR:** [#10](https://github.com/aguacatero/scalar-wave-viz/pull/10) (DRAFT)  
**Branch:** `p1-numerics-force-accounting-2026-10-18`  
**Canonical R9 Review:** [pullrequestreview-5641310092](https://github.com/aguacatero/scalar-wave-viz/pull/10#pullrequestreview-5641310092)  
**Reviewed HEAD SHA:** `2fb54dad222f08f0fb333ed544ef2c5e48247a73`  
**Target Review Round:** R10  
**Disposition:** REVISE / NOT ACCEPTED (All findings addressed herein)

---

## Executive Summary

ChatGPT's independent scientific R9 review on PR #10 evaluated the remediations from R8. R9 confirmed that the exact discrete leapfrog interior Hamiltonian theorem closes to machine precision ($< 10^{-12}$) across $dt$ and $dx$ refinements, non-unity material speed $c(x)$, nonzero damping $\sigma(x)$, and nonzero source work $W_{\text{source}}$.

R9 identified two findings requiring remediation before acceptance:
1. **P1-R9-F1 (MED):** Fail-closed interior validator accepts empty subvolumes on rectangular grids, and `source_field=None` bypasses validation in `compute_interior_source_work_step`.
2. **P1-R9-F2 (LOW):** Public `compute_sampled_continuum_energy_diagnostic` docstring still asserts unsupported $O(\Delta t^2 + \Delta x^2)$ drift.

Additionally, R9 provided a nonblocking recommendation to serialize both an undriven/undamped case and a driven+damped case in the standalone science manifest (`electrostatics_manifest.json`).

All findings and the nonblocking recommendation have been completely remediated and tested.

---

## Finding-by-Finding Remediation Ledger

### P1-R9-F1 (MED): Fail-Closed Interior Validator on Rectangular Grids & Fail-Closed Source Work

- **Finding Details:**
  1. `validate_interior_sponge_width(sponge_width, grid_dim)` checked `2 * sw >= grid_dim` using only `phi.shape[0]`. On non-cubic rectangular grids (e.g., shape `(12, 6, 12)` with `sw=3`), dimension 1 has length 6, yielding $6 - 2 \times 3 = 0$ interior nodes. Slicing `phi[3:-3, 3:-3, 3:-3]` produces a degenerate array of shape `(6, 0, 6)` with 0 total nodes, causing interior energy, boundary transfer, dissipation, and flux to silently return 0.0 without failing closed.
  2. In `compute_interior_source_work_step`, the early return `if source_field is None: return 0.0` was executed *before* `validate_interior_sponge_width`. An unphysical or invalid `sponge_width` (such as `0`, `-1`, or `True`) escaped validation whenever `source_field` was `None`.

- **Root Cause Analysis:**
  The validator assumed isotropic cubic domains ($N_x = N_y = N_z$) and callers passed only `phi.shape[0]`. The source work helper placed input validation after a short-circuit return.

- **Remediation:**
  1. Generalized `validate_interior_sponge_width` to accept `grid_dim: int | tuple[int, ...] | list[int] | np.ndarray`. It extracts `min_dim = min(int(d) for d in grid_dim)` and strictly requires `1 <= 2 * sw < min_dim`. This guarantees that every Cartesian dimension $d$ has at least $d - 2 \cdot sw \ge 1$ interior nodes, rejecting any configuration that yields an empty interior subvolume.
  2. Updated all interior accounting callers in `scalar_wave_3d.py`:
     - `compute_interior_exact_discrete_leapfrog_energy(..., phi.shape)`
     - `compute_exact_discrete_interior_boundary_transfer(..., phi_cur.shape)`
     - `compute_interior_sponge_dissipated_energy(..., phi_next.shape)`
     - `compute_interior_source_work_step(..., phi_next.shape)`
     - `compute_enclosing_surface_outward_flux(..., phi.shape)`
  3. Reordered `compute_interior_source_work_step` so that `validate_interior_sponge_width` executes unconditionally at function entry before checking `if source_field is None:`.

- **Adversarial Regression Tests Added in `tests/test_p1_wave_3d.py`:**
  - `test_exact_discrete_interior_control_volume_hamiltonian_and_boundary_transfer` Section H & I:
    - Bypassed source check: `compute_interior_source_work_step(p, pm, None, c_field, dt, dx, sw)` raises `ValueError` for `sw in (0, -2, 20, True)`.
    - Empty rectangular subvolume: on invalid non-cubic grid `(12, 6, 12)` with `sw=3`, `validate_interior_sponge_width` and all 5 interior accounting functions raise `ValueError`.
    - Valid non-cubic rectangular grid: shape `(16, 10, 14)` with `sw=3` (interior shape `(10, 4, 8)`) succeeds and verifies exact discrete Hamiltonian local continuity with boundary transfer, damping, and source to machine precision:
      $$\left|\frac{\Delta H_{\text{int}} + \sum \Delta B + \sum \Delta D_{\text{int}} - \sum \Delta W_{\text{source}}}{H_{\text{init}}}\right| < 10^{-12}.$$

---

### P1-R9-F2 (LOW): Public `compute_sampled_continuum_energy_diagnostic` Docstring Discretization Drift

- **Finding Details:**
  The docstring for `compute_sampled_continuum_energy_diagnostic` previously stated:
  `Exhibits O(dt^2 + dx^2) truncation drift on finite grids.`
  Because the kinetic energy component uses backward difference in time $(\phi^n - \phi^{n-1})/\Delta t$, it is only first-order accurate at grid-node time $t^n$. The assertion of broad second-order temporal drift was unsupported.

- **Remediation:**
  Updated docstring in `scalar_wave_3d.py` (lines 507-522) to remove the unsupported $O(\Delta t^2 + \Delta x^2)$ claim and accurately specify:
  `Evaluated via backward differences in time for velocity and central spatial differences for spatial gradients. Acts as a continuum-inspired diagnostic proxy with finite-grid discretization drift, rather than an exact discrete invariant for the staggered leapfrog equation.`

---

### Nonblocking Enhancement: Serialization of Driven + Damped Interior Control-Volume Budget

- **Recommendation Details:**
  The serialized representative case for `exact_discrete_interior_control_volume_budget` in `electrostatics_manifest.json` was source-free and undamped ($D=0, W=0$). Enhancing this to serialize both an undriven/undamped case and a driven+damped case makes the standalone science manifest self-contained and demonstrative of the full theorem.

- **Remediation:**
  1. Extended `InteriorControlVolumeBudgetResult` with fields `interior_sigma: float = 0.0` and `source_amplitude: float = 0.0`.
  2. Extended `benchmark_interior_control_volume_budget` to accept `interior_sigma` and `source_amplitude`, applying them to `sig_field` and `source_field` in the interior.
  3. Updated `examples/electrostatics_demo.py` (`_get_cached_wave_audit`) to execute:
     - `undriven_undamped_case`: `grid_size=40, sw=8, dx=1.0, interior_sigma=0.0, source_amplitude=0.0`
     - `driven_damped_case`: `grid_size=40, sw=8, dx=1.0, interior_sigma=0.5, source_amplitude=0.1`
  4. Serialized both cases under `exact_discrete_interior_control_volume_budget` in `electrostatics_manifest.json`.
  5. Added unit test in `tests/test_p1_wave_3d.py` asserting that both undriven and driven+damped cases satisfy machine precision closure ($< 10^{-12}$) and achieve non-zero dissipation ($> 10^{-4}$) and non-zero source work ($> 10^{-4}$).

---

## Baseline Integrity

- `electrostatics_baseline.py` was preserved byte-for-byte (`git diff electrostatics_baseline.py` is empty).
- All P0 conventional electrostatics models, 2D boundary elements / finite-difference baseline, and 1D parallel plate checks remain unmodified.
- PR #10 remains in **DRAFT** status; merge is strictly prohibited until independent review acceptance.
