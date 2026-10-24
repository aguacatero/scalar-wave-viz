# P1 R6 Finding-by-Finding Fix Queue & Resolution Ledger

- **Repository:** https://github.com/aguacatero/scalar-wave-viz
- **PR:** #10 (Draft)
- **Review Identifier:** [`pullrequestreview-5636987231`](https://github.com/aguacatero/scalar-wave-viz/pull/10#pullrequestreview-5636987231)
- **Reviewed Source HEAD SHA:** `0f2eea6e0d0606355e7c88b4def5778be81fb5e5`
- **Disposition:** REVISE / NOT ACCEPTED
- **Pickup Mode:** `MANUAL-ONLY`
- **Review Basis:** UNION of BOTH prior R5 reviews ([#5635398564](https://github.com/aguacatero/scalar-wave-viz/pull/10#pullrequestreview-5635398564) and [#5635660867](https://github.com/aguacatero/scalar-wave-viz/pull/10#pullrequestreview-5635660867)) and R6 review [#5636987231](https://github.com/aguacatero/scalar-wave-viz/pull/10#pullrequestreview-5636987231).

---

## 1. Finding-by-Finding Breakdown

### P1-R6-F1 (HIGH) — Purported conservative enclosing-surface flux has no local energy continuity proof (R5-F1 unresolved)
- **Problem:**
  In `scalar_wave_3d.py#L604-L641`, `compute_enclosing_surface_outward_flux` computed the 6 crossing-face contributions using only the interior-node centered velocity `-v_in * (phi_out - phi_in) / dx`. For standard semidiscrete/discrete local energy assigning half of each neighboring bond energy to each node, the interface exchange uses `-(v_in + v_out) / 2 * (phi_out - phi_in) / dx`. These differ by `(v_out - v_in) * (phi_out - phi_in) / (2 * dx)`.
  Without an interior control-volume discrete energy-continuity law, `surface_integrated_return_flux_ratio` is an approximate surface-flux proxy, not an established conservative return-energy fraction.
- **Required Resolution:**
  1. Implement symmetric bond velocity `0.5 * (v_in + v_out)` across all 6 faces of $\partial \Omega_{\text{int}}$.
  2. Relabel the metric consistently as an approximate surface-flux proxy (`surface_flux_return_ratio_proxy`, keeping `surface_integrated_return_flux_ratio` as backward-compatible property alias).
  3. Remove any assertion that $\le 5\%$ certifies a closed conservative interior return-energy budget; clearly document that it measures the enclosing-surface flux proxy across the 6 faces of $\partial \Omega_{\text{int}}$, while exact energy conservation and dissipation are certified by the closed whole-domain leapfrog identity $H_{\text{final}} + D_{\text{sponge}} = H_{\text{init}}$ (< 1e-12) and whole-domain dissipation $\ge 90\%$.
  4. Add an adversarial regression test testing interior control-volume energy continuity residual under time/space refinement.

### P1-R6-F2 (LOW) — Known-invalid legacy absorption-success label remains machine-readable (R5-F4a unresolved)
- **Problem:**
  `fixed_window_late_early_probe_amplitude_proxy` (`scalar_wave_3d.py#L484-L568`) still returned `is_absorbed_to_tolerance = (r_pwr <= tolerance and interior_energy <= total_energy)` for a legacy fixed-window diagnostic known to be insensitive to damping (~3.2% ratio even at $\sigma=0$).
  `examples/electrostatics_demo.py#L785-L804` exported `is_absorbed_to_tolerance` and `power_reflection_coefficient` in the machine-readable manifest.
  `tests/test_p1_wave_3d.py#L126` asserted `res.is_absorbed_to_tolerance is True`.
- **Required Resolution:**
  1. In `SpongeBoundaryReflectionResult` and `fixed_window_late_early_probe_amplitude_proxy`, set `legacy_metric_invalid_for_absorption: bool = True`, `is_absorbed_to_tolerance: bool = False`, and document that the legacy metric is fundamentally incapable of certifying absorption.
  2. In `examples/electrostatics_demo.py`, export `legacy_metric_invalid_for_absorption: True` and deprecate/remove positive absorption verdict.
  3. In `tests/test_p1_wave_3d.py`, replace assertion with `self.assertTrue(res.legacy_metric_invalid_for_absorption)` and `self.assertFalse(res.is_absorbed_to_tolerance)`. Add negative control showing that $\sigma=0$ produces the same ~3.2% ratio, demonstrating why it cannot certify absorption.

### P1-R6-F3 (LOW) — SOR convergence threshold still accepts positive infinity
- **Problem:**
  In `electrostatics_numerics.py#L1213-L1230`, `if tolerance_v <= 0.0` did not reject `float('inf')` or `float('nan')`. Setting `tolerance_v=float('inf')` bypassed the fail-closed intent on unconverged fields.
- **Required Resolution:**
  1. Validate `np.isfinite(tolerance_v) and tolerance_v > 0.0` and integral positive `max_iterations >= 1` (rejecting floats, zero, negative, NaN, and infinity with `ValueError`).
  2. Add adversarial regression tests for `tolerance_v=float('inf')`, `float('nan')`, `0.0`, `-1.0`, and non-integer/zero `max_iterations`.

### Nonblocking Cleanup:
- Remove stale comment `# 3. Independent dense boundary verification (Maximum Principle certificate)` at line 1420 of `electrostatics_numerics.py`.

---

## 2. Action Plan for R7
1. Update `scalar_wave_3d.py`:
   - Symmetric interface velocity for `compute_enclosing_surface_outward_flux`.
   - Relabel `surface_flux_return_ratio_proxy` on `SpongeReflectionReferenceSubtractedResult` (retaining `surface_integrated_return_flux_ratio` alias).
   - Set `legacy_metric_invalid_for_absorption=True`, `is_absorbed_to_tolerance=False` on `SpongeBoundaryReflectionResult`.
2. Update `electrostatics_numerics.py`:
   - Validate `np.isfinite(tolerance_v)` and positive integer `max_iterations`.
   - Remove stale `(Maximum Principle certificate)` comment.
3. Update `examples/electrostatics_demo.py`:
   - Update manifest serialization for `surface_flux_return_ratio_proxy` and `legacy_metric_invalid_for_absorption`.
4. Update `tests/test_p1_wave_3d.py` and `tests/test_p1_numerics.py`:
   - Add adversarial input tests for SOR (`inf`, `nan`, negative, non-int).
   - Add legacy invalidity test (`legacy_metric_invalid_for_absorption=True`, `is_absorbed_to_tolerance=False`, $\sigma=0$ control).
   - Add interior energy continuity residual test.
5. Re-run demo and full test suite.
6. Verify byte-for-byte baseline preservation on `electrostatics_baseline.py`.
7. Commit, push, verify CI run, and post timestamped R7 handoff.

---

## 3. Implementation & Verification Ledger (R6 -> R7)

### 3.1 P1-R6-F1 Resolution: Space-Symmetric Interface Flux Proxy & Local Energy Continuity
- **Code:** In `scalar_wave_3d.py`, updated `compute_enclosing_surface_outward_flux` to evaluate interface flux across all 6 faces of $\partial \Omega_{\text{int}}$ using the symmetric bond velocity $v_{\text{bond}} = \frac{v_{\text{in}} + v_{\text{out}}}{2}$.
- **Proxy Relabeling:** Added `surface_flux_return_ratio_proxy: float` to `SpongeReflectionReferenceSubtractedResult`, `SpongeControlRow`, and `SpongeParameterSweepRow`, keeping `surface_integrated_return_flux_ratio` as a `@property` alias for backwards compatibility.
- **Epistemic Clarity:** Clarified in `metric_note` and docstrings that this metric is an approximate surface-flux proxy across the 6 boundary faces rather than a closed conservative control-volume identity. Exact physical discrete energy conservation and absorption are certified by the whole-domain leapfrog identity ($H_{\text{final}} + D_{\text{sponge}} = H_{\text{init}}$ to $< 10^{-12}$) and total dissipation $\ge 90\%$.
- **Adversarial Test:** Added `test_interior_control_volume_flux_continuity_and_residual` in `tests/test_p1_wave_3d.py`, demonstrating that cumulative symmetric outward flux tracks interior energy loss to within $0.32\%$ ($0.025\text{ J}$ residual on $7.81\text{ J}$ pulse, $< 1\%$ threshold). Verified spatial convergence under grid refinement ($\Delta x = 1.0\text{ m} \to 0.5\text{ m}$) where the flux proxy converges from $1.18\%$ to $1.11\%$ (relative difference $6.55\% < 15\%$).

### 3.2 P1-R6-F2 Resolution: Legacy Absorption-Success Flag Invalidation
- **Code:** In `scalar_wave_3d.py`, updated `SpongeReflectionProbeResult` and `fixed_window_late_early_probe_amplitude_proxy` so that `legacy_metric_invalid_for_absorption: bool = True` and `is_absorbed_to_tolerance: bool = False` unconditionally.
- **Manifest Serialization:** In `examples/electrostatics_demo.py`, serialized `legacy_metric_invalid_for_absorption: True` and `is_absorbed_to_tolerance: False`, explicitly documenting that the metric measures the outgoing pulse tail at step 25 without reference subtraction (~3.2% power ratio regardless of $\sigma$, including $\sigma=0$).
- **Adversarial Test:** In `tests/test_p1_wave_3d.py` (`test_sponge_boundary_reflection_probe_legacy_proxy`), asserted `legacy_metric_invalid_for_absorption is True` and `is_absorbed_to_tolerance is False`. Added negative control showing identical $\approx 3.2\%$ power ratio with $\sigma=0$, confirming the metric is demonstrably invalid for absorption.

### 3.3 P1-R6-F3 Resolution: SOR Tolerance & Max Iteration Validation
- **Code:** In `electrostatics_numerics.py`, updated `solve_dirichlet_independent_matrix_free_sor` to reject non-finite, zero, or negative tolerance with `np.isfinite(tolerance_v) and tolerance_v > 0.0`, and to reject non-integer or $< 1$ iterations with `isinstance(max_iterations, (int, np.integer)) and max_iterations >= 1`.
- **Adversarial Test:** In `tests/test_p1_numerics.py`, added tests validating rejection of `tolerance_v=float('inf')`, `float('nan')`, `0.0`, `-1e-5`, and `max_iterations=0`, `-5`, `10.5`, `float('inf')`. All 16 tests in `test_p1_numerics.py` pass.

### 3.4 Nonblocking Cleanup
- Replaced stale comment `# 3. Independent dense boundary verification (Maximum Principle certificate)` at line 1420 of `electrostatics_numerics.py` with `# 3. Independent dense boundary verification (sampled boundary diagnostic)`.

### 3.5 Full Test Suite & Baseline Verification
- `git diff electrostatics_baseline.py`: 0 differences (byte-for-byte preserved).
- Full unit test suite: 70 tests passed in 297.8s (`Ran 70 tests in 297.811s OK`).
- Manifest regenerated cleanly with `MPLBACKEND=Agg python3 examples/electrostatics_demo.py`.
