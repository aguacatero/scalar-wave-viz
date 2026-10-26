# P1 R10 Independent Review Fix Queue & Remediation Ledger

**Repository:** `aguacatero/scalar-wave-viz`  
**PR:** [#10](https://github.com/aguacatero/scalar-wave-viz/pull/10) (DRAFT)  
**Branch:** `p1-numerics-force-accounting-2026-10-18`  
**Canonical R10 Review:** [pullrequestreview-5643309076](https://github.com/aguacatero/scalar-wave-viz/pull/10#pullrequestreview-5643309076)  
**Reviewed HEAD SHA:** `68bb011a28b0a4ea0f80c92540fd791591925cf4`  
**Target Review Round:** R11  
**Disposition:** REVISE / NOT ACCEPTED (All findings addressed herein)

---

## Executive Summary

ChatGPT's independent scientific R10 review on PR #10 verified that findings P1-R9-F1 and P1-R9-F2 were closed, and that the R9 manifest serialization was implemented. An independent mathematical re-derivation in NumPy confirmed the exact discrete interior Hamiltonian theorem ($H + B + D - W$) closing to machine precision ($\approx 1.89 \times 10^{-16}\text{ E\_arb}$, relative closure $\approx 3.56 \times 10^{-17}$).

R10 identified one medium-severity finding requiring remediation before unconditional acceptance, and one nonblocking reproducibility recommendation:
1. **P1-R10-F1 (MED):** Configurable local-budget benchmark silently ignores invalid physical settings and can claim success without integration.
2. **P1-R10-R1 (LOW / Nonblocking Recommendation):** Record simulation protocol reproducibility metadata (source spatial form, Gaussian width, previous-step prescription) in `exact_discrete_interior_control_volume_budget`.

Both findings have been completely remediated, validated, and tested with adversarial regressions.

---

## Finding-by-Finding Remediation Ledger

### P1-R10-F1 (MED): Configurable Local-Budget Benchmark Fail-Closed Parameter Validation

- **Finding Details:**
  In `benchmark_interior_control_volume_budget` (`scalar_wave_3d.py`), `interior_sigma` and `source_amplitude` were applied only when strictly positive (`> 0.0`). If negative values were passed (such as `interior_sigma = -0.5` or `source_amplitude = -0.1`), the benchmark silently ran the undamped, unforced system while reporting the invalid negative parameters in the result object and claiming `is_exact_to_machine_precision = True`. Non-finite values (`NaN`, `inf`) also bypassed the `> 0.0` guards. Furthermore, `n_steps = 0` or negative integers executed zero evolution steps and returned a vacuous machine-precision pass without simulation.

- **Root Cause Analysis:**
  The benchmark function lacked comprehensive entry parameter guards for its newly added configuration parameters, relying on strict positivity checks rather than explicit validation and physical handling.

- **Remediation:**
  1. **Strict Non-Negative Damping:** Enforced that `interior_sigma` must be a finite numerical value (rejecting bools, `NaN`, `inf`) and must satisfy $\sigma_{\text{int}} \ge 0.0$.
  2. **Genuine Signed Source Amplitude:** Enforced that `source_amplitude` must be a finite numerical value (rejecting bools, `NaN`, `inf`). When `source_amplitude != 0.0` (positive or negative), the benchmark genuinely constructs and injects the spatial source field $S(x) = A \sin(x)$ into the FDTD stepper and evaluates exact source work.
  3. **Strict Positive Step Count:** Enforced that `n_steps` must be a strict integer (rejecting bools and floats) satisfying $N_{\text{steps}} \ge 1$.
  4. **Strict Grid & Physical Parameters:** Enforced that `grid_size \ge 3` (int, not bool), `sponge_width` is validated via `validate_interior_sponge_width`, `dx_m > 0` (finite, not bool), `c_m_per_s > 0` (finite, not bool), and `courant_factor > 0` with `courant_factor <= 1.0` (finite, not bool).
  5. Any invalid configuration raises `ValueError` before simulation setup or result construction.

- **Adversarial Regression Tests Added in `tests/test_p1_wave_3d.py`:**
  - `interior_sigma in (-0.5, NaN, inf, True)` raises `ValueError`.
  - `source_amplitude in (NaN, inf, True)` raises `ValueError`.
  - Genuine negative source drive (`source_amplitude = -0.1`) executes, satisfies machine-precision closure ($< 10^{-12}$), records $-0.1$ in metadata, and yields non-zero source work ($|W| > 10^{-4}$) distinct from positive drive.
  - `n_steps in (0, -1, True, 2.5)` raises `ValueError`.
  - `grid_size in (2, True)`, `sponge_width in (0, 20)`, `dx_m in (0.0, -1.0)`, `c_m_per_s in (0.0)`, `courant_factor in (0.0, 1.2)` raise `ValueError`.

---

### P1-R10-R1 (LOW): Nonblocking Simulation Protocol Metadata

- **Finding Details:**
  The serialized evidence artifact in `electrostatics_manifest.json` recorded the parameter values but did not explicitly document the mathematical prescriptions for initial field conditions, time-stepping previous-step initialization, and spatial source/conductivity profiles.

- **Remediation:**
  In `examples/electrostatics_demo.py`, added `simulation_protocol` metadata under `exact_discrete_interior_control_volume_budget`:
  - `initial_field_form`: `'Gaussian pulse centered at domain midpoint: phi^0 = exp(-r^2 / (2 * (2 * dx)^2))'`
  - `staggered_previous_step_prescription`: `'phi^{-1} = phi^0 + 0.5 * dt^2 * c^2 * lap(phi^0)'`
  - `source_spatial_protocol`: `'Time-independent spatial waveform restricted to Cartesian interior Omega_int: S(x, y, z) = source_amplitude * sin(x)'`
  - `interior_conductivity_form`: `'Uniform damping conductivity restricted to Cartesian interior Omega_int: sigma(x, y, z) = interior_sigma'`

---

## Baseline Integrity

- `electrostatics_baseline.py` was preserved byte-for-byte (`git diff electrostatics_baseline.py` is empty).
- All P0 conventional electrostatics models, 2D boundary elements / finite-difference baseline, and 1D parallel plate checks remain unmodified.
- PR #10 remains in **DRAFT** status; merge is strictly prohibited until independent review acceptance.
