# P1 R5 Independent Scientific Re-Review — Fix Queue & Resolution Ledger

**Source Review:** [PR #10 review 5635660867](https://github.com/aguacatero/scalar-wave-viz/pull/10#pullrequestreview-5635660867)  
**Reviewed Commit:** `485d8c6f805bd03841ca7d385b0df4dc8cf5658a`  
**Base Commit:** `174c6b895a0c2ec416b6d46ab9e0835b14a8cb49`  
**Review Disposition:** REVISE (NOT ACCEPTED) — PR #10 remains DRAFT; no merge or P2 initiation.

---

## 1. Closed Findings & Remaining R5 Findings Catalog

### Previously Closed Findings
- **P1-R3-F1 (HIGH):** CLOSED in R4 (6-component force convergence, full 2D vector residual, active/near-zero gates, off-axis $y$-asymmetric case, honestly named two-grid differences).
- **P1-R3-F2 (MED):** CLOSED in R4 (limited both-electrode asymmetric and mesh/step-sensitivity virtual-work comparison).
- **P1-R3-F3 (MED):** CLOSED in R4 (scalar PDE analytical coefficient testing across two-medium planar interfaces $c_1 > c_2$ and $c_1 < c_2$ under refinement).
- **P1-R4-F2 (MED):** CLOSED in R5 (continuum energy sampled *after* state advance, covering steps $0..N$, with positive/negative signed drift independent terminal checks and separate staggered Hamiltonian trajectory).

---

### Remaining R5 Findings Requiring Pickup

#### P1-R5-F1 (HIGH) — Sponge validity gate can pass with zero absorption and no reflection observation window (R4-F1 follow-up)
- **Problem:**
  In `scalar_wave_3d.py#L857-L874`, `is_sponge_benchmark_valid` checked reference isolation, pre-arrival difference, energy closure, and two *proxy* tolerances, but did **not** check:
  1. Return-time observation window sufficiency: `n_steps >= geometric_peak_return_step` (or a window adequate to observe boundary return).
  2. Demonstrated sponge absorption: `sponge_dissipated_energy_fraction >= min_sponge_dissipated_fraction` (e.g. $\ge 90\%$).
  3. Inward return flux tolerance: `surface_integrated_return_flux_ratio <= tolerance_return_flux_ratio`.
  4. Nonzero incident flux denominator: `cumulative_incident_outgoing_surface_flux > 0.0`. If incident flux is zero, the ratio defaulted to `0.0`.
  - *Adversarial Counterexample:* `max_sigma=0.0, n_steps=1` with a large reference domain. Fields have had no time for a wall return and match reference in the observation volume to negligible Gaussian tail error (< 1e-8), difference proxies are essentially zero, Hamiltonian closes with **zero** dissipation, yet `is_sponge_benchmark_valid=True`, falsely certifying an undamped simulation as valid sponge absorption!
  - *Gate Hygiene:* In `benchmark_sponge_reflection_parameter_sweep`, `dx_refinement_consistent` checked only that two snapshots fall below 2% rather than evaluating actual inter-grid relative difference or return-flux consistency.
- **Required Resolution:**
  1. Separate setup/identity validity (`is_simulation_setup_valid: bool`) from demonstrated absorption (`is_sponge_absorbed_to_tolerance: bool`).
  2. `is_simulation_setup_valid` verifies causal reference isolation (`reference_domain_free_of_wall_return`), pre-arrival causal zero difference (`pre_arrival_difference_max < 1e-8`), exact discrete energy-budget closure (`discrete_energy_budget_closure_error < 1e-12`), and observation window sufficiency (`n_steps >= geometric_peak_return_step`).
  3. `is_sponge_absorbed_to_tolerance` requires `is_simulation_setup_valid` **plus**:
     - Nonzero incident flux denominator: `cumulative_incident_outgoing_surface_flux > 0.0`.
     - High sponge energy dissipation: `sponge_dissipated_energy_fraction >= min_dissipated_fraction` (default 0.90; design sponge achieves >97%).
     - Low surface-integrated return flux: `surface_integrated_return_flux_ratio <= tolerance_return_flux_ratio` (default 0.05; design sponge achieves 0.81%).
     - Low proxy reflection: `probe_local_peak_squared_proxy <= tolerance_proxy_max` and `peak_window_interior_reflected_energy_snapshot_proxy <= tolerance_proxy_max`.
  4. In spatial refinement parameter sweep, evaluate actual inter-grid relative differences between well-resolved grids ($\Delta x = 1.0\text{ m}$ vs $0.5\text{ m}$), and accurately label the boundedness screen.
  5. Add adversarial regression tests:
     - Undamped Dirichlet wall (`max_sigma=0.0, n_steps=80`) must fail `is_sponge_absorbed_to_tolerance` (dissipation = 0%).
     - Insufficient duration (`n_steps=1` or `n_steps < geometric_peak_return_step`) must fail setup validity and absorption certification.
     - Zero incident flux case must not trivially pass return-flux ratio.

#### P1-R5-F2 (MED) — Sampled MFS boundary residual is mislabeled a rigorous continuous maximum-principle certificate
- **Problem:**
  `electrostatics_numerics.py` computed the maximum error over 720 sampled boundary angles per circular electrode and 400 sampled points per enclosure side. This is a finite discrete point sample, **not** the supremum over the continuous boundary. The Maximum Principle for harmonic functions states:
  $$\sup_{\Omega_{\text{vac}}} |V_{\text{MFS}} - V_{\text{exact}}| \le \sup_{\partial \Omega_{\text{vac}}} |V_{\text{MFS}} - V_{\text{exact}}|$$
  Evaluating a discrete sample of points does not mathematically guarantee the continuous interior supremum without an analytical or interval bound on the unsampled gaps. Calling this a "rigorous continuous certificate" or "guaranteeing interior error < 1e-10 V" overclaims the mathematical result. Furthermore, the gate defaulted to `tolerance_mfs_boundary_v=1e-3`, which was inconsistent with a claimed $10^{-10}\text{ V}$ guarantee.
- **Required Resolution:**
  1. Relabel all references honestly as an independent dense **sampled-boundary diagnostic** (`max_sampled_boundary_error_v`, `sampled_boundary_residual_diagnostic`), explicitly noting that while dense sampling ($N_{\text{sample}} = 720$ points/electrode, $\Delta s \approx 26\,\mu\text{m}$) gives strong numerical confidence, it is a discrete check rather than a continuous supremum certificate.
  2. In docstrings, dataclasses, diagnostics, and test comments, remove language claiming a mathematical guarantee of continuous interior supremum from discrete boundary evaluations.
  3. Align acceptance tolerances: use explicit sampled-boundary tolerance `tolerance_mfs_sampled_boundary_v = 1e-6` (observed: $8.06 \times 10^{-11}\text{ V}$).

#### P1-R5-F3 (LOW) — Claimed strictly monotonic FDM-to-MFS force convergence contradicts the data and gate
- **Problem:**
  Published enclosure force errors across $n \in (41, 81, 161, 321)$ are **4.89%, 4.91%, 4.44%, 2.21%**. The first refinement step ($41 \to 81$) slightly increases enclosure error from 4.89% to 4.91% due to discrete Cartesian grid pixelation/staircasing of circular boundaries. However, `electrostatics_numerics.py` tested only `rows[-1] < rows[0]` under the name `errors_decrease_toward_mfs_with_refinement`, and tests claimed "monotonic convergence".
- **Required Resolution:**
  1. Rename gate to `endpoint_errors_improve` (or `errors_decrease_coarsest_to_finest`).
  2. State honestly in docstrings, dataclass, diagnostics, and test comments that staircase boundary approximations on Cartesian grids do not necessarily exhibit strict monotonicity at every intermediate resolution step, while the overall trend improves and the finest-grid agreement meets the stated $< 5\%$ tolerance across all components (left 3.66%, right 3.05%, enclosure 2.21%, midpoint E 1.53%).
  3. Add regression tests asserting finest-vs-coarsest improvement and verifying that non-monotonic intermediate steps are accurately recognized without false strict-monotonicity claims.

#### P1-R5-F4 (LOW) — Independent SOR solver silently returns nonconverged states
- **Problem:**
  In `solve_dirichlet_independent_matrix_free_sor` (`electrostatics_numerics.py`), the loop ran up to `max_iterations`, and if `max_res > tolerance_v` when the loop ended, it silently returned `FieldSolution` with no error, presenting an unconverged iterate as an independently solved field.
- **Required Resolution:**
  1. Validate iteration and tolerance inputs (`max_iterations >= 1`, `tolerance_v > 0`).
  2. Track whether convergence was achieved (`is_converged: bool` and `iterations_completed: int`).
  3. If residual exceeds `tolerance_v` upon loop completion, raise a descriptive `RuntimeError(f"SOR solver failed to converge within {max_iterations} iterations...")` (or fail closed in verification).
  4. Add an adversarial regression test: `max_iterations=1` on the off-axis configuration must fail closed with a `RuntimeError`.

---

## 2. Implementation Plan

1. **`scalar_wave_3d.py` (P1-R5-F1):**
   - Update `SpongeReflectionReferenceSubtractedResult` and `benchmark_sponge_reflection_reference_subtracted`:
     - Expose `is_simulation_setup_valid: bool` and `is_sponge_absorbed_to_tolerance: bool`.
     - Explicitly verify `n_steps >= geometric_peak_return_step`.
     - If `cumulative_incident_outgoing_surface_flux <= 0.0`, set `surface_integrated_return_flux_ratio = float('nan')` (or fail closed).
     - Gate absorption on `sponge_dissipated_energy_fraction >= min_dissipated_fraction` (default 0.90), `surface_integrated_return_flux_ratio <= tolerance_return_flux_ratio` (default 0.05), and proxy bounds.
   - Update `benchmark_sponge_reflection_parameter_sweep`:
     - Evaluate inter-grid relative difference between $\Delta x = 1.0\text{ m}$ and $\Delta x = 0.5\text{ m}$ on interior snapshots and return-flux ratios, accurately characterizing the boundedness screen.
2. **`electrostatics_numerics.py` (P1-R5-F2, P1-R5-F3, P1-R5-F4):**
   - **P1-R5-F4:** In `solve_dirichlet_independent_matrix_free_sor`, validate inputs, track convergence, and raise `RuntimeError` if unconverged.
   - **P1-R5-F2:** In `solve_electrostatics_mfs_boundary_collocation` and `MFSContinuousLaplaceSolution`, rename `max_independent_boundary_error_v` to `max_sampled_boundary_error_v`. Clarify in docstrings and diagnostics that boundary evaluations are discrete point samples ($N_{\text{sample}} = 720$), not an analytical supremum certificate. Set `tolerance_mfs_sampled_boundary_v = 1e-6`.
   - **P1-R5-F3:** In `IndependentSolverVerificationStudy`, rename `errors_decrease_toward_mfs_with_refinement` to `endpoint_errors_improve` and document non-strict intermediate behavior honestly.
3. **`examples/electrostatics_demo.py` & Manifest:**
   - Reflect updated fields (`is_simulation_setup_valid`, `is_sponge_absorbed_to_tolerance`, `max_sampled_boundary_error_v`, `endpoint_errors_improve`).
4. **Adversarial Regression Tests:**
   - `tests/test_p1_wave_3d.py`: Test `max_sigma=0.0` fails absorption; test `n_steps=1` fails setup validity; test insufficient duration fails absorption.
   - `tests/test_p1_numerics.py`: Test `max_iterations=1` on SOR raises `RuntimeError`; test MFS sampled boundary diagnostic; test endpoint error improvement and intermediate non-monotonicity.
5. **Full Test Suite & Artifact Regeneration:**
   - Run complete suite (68 tests + new adversarial regressions).
   - Verify `git diff electrostatics_baseline.py` is empty.
   - Commit, push, verify CI, and post timestamped R6 handoff.

---

## Implementation & Verification Ledger (R5 -> R6)

### 1. Finding Resolution Details
- **`P1-R5-F1` (HIGH / Sponge validity gate separation & absorption demonstration):**
  - Updated `SpongeReflectionReferenceSubtractedResult` and `benchmark_sponge_reflection_reference_subtracted` in `scalar_wave_3d.py`:
    - Separated `is_simulation_setup_valid: bool` and `is_sponge_absorbed_to_tolerance: bool` (with `@property is_sponge_benchmark_valid` and `@property is_absorbed_to_tolerance` returning `is_sponge_absorbed_to_tolerance` for backwards compatibility).
    - `is_simulation_setup_valid` verifies causal reference isolation, pre-arrival causal zero difference, machine-precision energy-budget closure (< 1e-12), and observation window duration: `n_steps >= geometric_peak_return_step`.
    - Added physical incident flux threshold `min_incident_flux = 1e-6 * h_init_disc` to distinguish physical pulse boundary crossings from Gaussian tail floating-point underflow noise; when `cum_inc_out_flux < min_incident_flux`, `surface_integrated_return_flux_ratio` returns `float('nan')` instead of defaulting to `0.0`.
    - `is_sponge_absorbed_to_tolerance` strictly requires `is_simulation_setup_valid`, `cum_inc_out_flux >= min_incident_flux`, `sponge_dissipated_energy_fraction >= 0.90`, `surface_integrated_return_flux_ratio <= 0.05`, and proxy tolerances.
    - Updated `benchmark_sponge_reflection_parameter_sweep` to evaluate actual inter-grid relative differences between well-resolved grids ($\Delta x = 1.0\text{ m}$ vs $0.5\text{ m}$) on snapshots (8.1% < 15%), surface return flux (7.2% < 15%), and dissipation (0.012% < 1%), while accurately characterizing the bounded snapshot levels (< 2%).
    - Added adversarial unit tests in `tests/test_p1_wave_3d.py`: undamped wall (`max_sigma=0.0, n_steps=80`) has valid setup but fails absorption (`sponge_dissipated_energy_fraction == 0.0`); short window (`n_steps=1`) fails setup validity and returns `NaN` for return-flux ratio; adversarial undamped 1-step run fails closed.

- **`P1-R5-F2` (MED / Sampled MFS boundary diagnostic):**
  - Updated `MFSContinuousLaplaceSolution` and `solve_electrostatics_mfs_boundary_collocation` in `electrostatics_numerics.py`:
    - Renamed `max_independent_boundary_error_v` to `max_sampled_boundary_error_v: float` (with `@property max_independent_boundary_error_v` alias).
    - Updated docstrings and diagnostics to remove claims of an analytical supremum guarantee and clearly state it is an independent dense sampled-boundary diagnostic (720 angles/electrode, 400 points/wall).
    - In `benchmark_independent_electrostatic_solver_verification`, set congruent tolerance `tolerance_mfs_sampled_boundary_v: float = 1e-6`.
    - Added regression test asserting `mfs.max_sampled_boundary_error_v < 1e-6` and `< 1e-9` (observed ~8.06e-11 V).

- **`P1-R5-F3` (LOW / Monotonicity vs endpoint improvement):**
  - Updated `IndependentSolverVerificationStudy` and `benchmark_independent_electrostatic_solver_verification` in `electrostatics_numerics.py`:
    - Renamed gate to `endpoint_errors_improve: bool` (with `@property errors_decrease_toward_mfs_with_refinement` alias).
    - Added `strict_intermediate_monotonicity: bool = False`.
    - Updated diagnostic note to state honestly that endpoint errors improve coarsest-to-finest while intermediate staircase rasterization errors are non-monotonic due to grid-boundary pixelation shifts.
    - Added regression tests verifying `endpoint_errors_improve` is True, `strict_intermediate_monotonicity` is False, and intermediate staircase enclosure error increases slightly from $n=41$ (4.89%) to $n=81$ (4.91%).

- **`P1-R5-F4` (LOW / SOR nonconvergence fails closed):**
  - In `solve_dirichlet_independent_matrix_free_sor`:
    - Added input validation for `max_iterations >= 1` and `tolerance_v > 0` (raising `ValueError`).
    - Added convergence tracking; if the discrete residual does not reach `tolerance_v` within `max_iterations`, raises `RuntimeError` with residual and tolerance details.
    - Added adversarial regression tests asserting `max_iterations=1` raises `RuntimeError("SOR solver failed to converge...")` and invalid parameters raise `ValueError`.

### 2. Evidence & Baseline Verification
- **Test Suite:** 69 unit tests passed across `test_electrostatics_baseline.py`, `test_p1_numerics.py`, and `test_p1_wave_3d.py`.
- **P0 Baseline Preservation:** `git diff electrostatics_baseline.py` is byte-for-byte empty.
- **Manifest & Figures:** Regenerated via `MPLBACKEND=Agg python3 examples/electrostatics_demo.py` and validated against schema.

