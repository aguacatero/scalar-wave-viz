# P1 R7 Finding-by-Finding Fix Queue & Resolution Ledger

- **Repository:** https://github.com/aguacatero/scalar-wave-viz
- **PR:** #10 (Draft)
- **Review Identifier:** [`pullrequestreview-5638960951`](https://github.com/aguacatero/scalar-wave-viz/pull/10#pullrequestreview-5638960951)
- **Reviewed Source HEAD SHA:** `85bf32d2fc3f5b12f1b27da11e1a67328f600590`
- **Disposition:** REVISE / NOT ACCEPTED
- **Pickup Mode:** `MANUAL-ONLY`
- **Target Review Round:** R8

---

## 1. Finding-by-Finding Breakdown & Root-Cause Analysis

### P1-R7-F1 (HIGH / CRITICAL) — Local energy continuity fails temporal refinement
- **Finding:**
  The R7 test `test_interior_control_volume_flux_continuity_and_residual` evaluated only a single time-step configuration ($\Delta t_0$, 25 steps, $\Delta t\text{-factor}=0.85$) where the continuum diagnostic `compute_interior_energy` happened to match the centered symmetric flux proxy to within 0.3233% ($0.02483\text{ E}_\text{arb}$ residual on $E_\text{init} = 7.67857\text{ E}_\text{arb}$).
  When independently reproduced under temporal refinement holding physical geometry and duration fixed:
  - $\Delta t_0$ (25 steps): relative residual = $0.3233\%$
  - $\Delta t_0 / 2$ (50 steps): relative residual = $4.0432\%$ (~12.5-fold increase, failing the $< 1\%$ threshold)
  - $\Delta t_0 / 4$ (100 steps): relative residual = $5.1173\%$
  This defeated the claim of a general time-refinement-validated local conservation law between the continuum diagnostic and the surface flux proxy.
- **Root-Cause Analysis:**
  The continuum diagnostic `compute_interior_energy` uses a backward-difference velocity at node time $t^n$: $v^n = (\phi^n - \phi^{n-1})/\Delta t$, coupled with central-difference spatial gradients. In contrast, `compute_enclosing_surface_outward_flux` evaluates symmetric crossing-face fluxes using centered velocity $v^n = (\phi^{n+1} - \phi^{n-1})/(2\Delta t)$. The two quantities have differing time-staggering and truncation errors ($O(\Delta t^2)$ vs $O(\Delta t)$), causing their finite-difference residual to grow under temporal refinement.
- **Resolution:**
  1. **Exact Discrete Control-Volume Theorem (Option A):**
     Derived and implemented the exact discrete local continuity identity for the staggered leapfrog 7-point Hamiltonian on any Cartesian subvolume $\Omega_\text{int} = [sw, N-sw)^3$:
     $$H_\text{int}^{n+1/2} - H_\text{int}^{n-1/2} + \Delta B_\text{boundary}^n + \Delta D_\text{int}^n = 0$$
     where:
     - $H_\text{int}^{n+1/2} = \frac{1}{2} \sum_{i \in \Omega_\text{int}} [ ((\phi_i^{n+1} - \phi_i^n)/(c_i \Delta t))^2 - \phi_i^{n+1} (\nabla_7^2 \phi^n)_i ] \Delta x^3$ (`compute_interior_exact_discrete_leapfrog_energy`).
     - $\Delta B_\text{boundary}^n = \frac{1}{2} \Delta x \sum_{i \in \Omega_\text{int}, j \notin \Omega_\text{int}} (\phi_i^{n-1} \phi_j^n - \phi_i^n \phi_j^{n-1})$ (`compute_exact_discrete_interior_boundary_transfer`). Internal bonds cancel identically via summation by parts, leaving only interface crossing bonds.
     - $\Delta D_\text{int}^n = \Delta t \sum_{i \in \Omega_\text{int}} \frac{\sigma_i}{c_i^2} [ (\phi_i^{n+1} - \phi_i^{n-1})/(2\Delta t) ]^2 \Delta x^3$ (`compute_interior_sponge_dissipated_energy`).
     Added test `test_exact_discrete_interior_control_volume_hamiltonian_and_boundary_transfer` verifying this identity closes to machine precision ($< 10^{-12}$, observed $\approx 10^{-16}$) across $\Delta t_0$, $\Delta t_0/2$, $\Delta t_0/4$, and with internal damping $\sigma=0.5$.
  2. **Continuum Proxy Scoping & Adversarial Refinement Characterization (Option B):**
     In `scalar_wave_3d.py`, updated docstrings for `compute_enclosing_surface_outward_flux` and `metric_definition_note` to explicitly state that the continuum diagnostic comparison is a finite-difference proxy comparison that exhibits $O(\Delta t)$ truncation residual growth under temporal refinement (~0.32% at $\Delta t_0$, ~4.04% at $\Delta t_0/2$, ~5.12% at $\Delta t_0/4$).
     In `tests/test_p1_wave_3d.py`, updated `test_interior_control_volume_flux_continuity_and_residual` to adversarially test and enforce these exact quantitative bounds under temporal refinement.
  3. **Whole-Domain Certification Fact:**
     Clearly stated that physical conservative energy closure and sponge absorption are certified separately by the exact discrete whole-domain leapfrog identity ($H_\text{final} + D_\text{sponge} = H_\text{init}$ to $< 10^{-12}$) and whole-domain dissipation $\ge 90\%$.

### P1-R7-F2 (MED) — Live PR #10 description still publishes a known-invalid reflection claim
- **Finding:**
  The live PR #10 description remained frozen at "P1 R2 Implementation Complete", cited 56 tests, and stated `probe reflection benchmark measures power reflection R_pwr ≈ 3.2% < 5%` under P1-C. This contradictory outward-facing claim advertised a known-invalid metric.
- **Resolution:**
  - Updated PR #10 body using `gh pr edit 10`.
  - Updated title/status to P1 R8 preparation / R7 remediation.
  - Quoted accurate test count (71 passing tests), exact commit SHA, and green CI runs.
  - In P1-C reflection section: removed the invalid 3.2% reflection claim, explicitly documented that the legacy fixed-window proxy measures the outgoing pulse tail at step 25 without reference subtraction (~3.2% power ratio regardless of $\sigma$, including $\sigma=0$), is permanently marked `legacy_metric_invalid_for_absorption: True`, and cannot certify absorption.
  - Documented that reference-subtracted reflection with closed discrete energy budget is used, with `surface_flux_return_ratio_proxy` explicitly scoped as an approximate surface-flux proxy.
  - Restated exact whole-domain leapfrog discrete energy closure ($< 10^{-12}$) and $\ge 90\%$ dissipation.
  - Preserved all explicit non-claims (no patent geometry, no net thrust, no physical scalar electrodynamics).
  - Maintained DRAFT status.

### P1-R7-F3 (LOW) — Unit and source hygiene
- **Finding:**
  1. Fix ledger and handoff referenced $0.025\text{ J}$ on a $7.81\text{ J}$ pulse. Wave energy routines explicitly use arbitrary energy units ($\text{E}_\text{arb}$), not Joules ($\text{J}$).
  2. In `SpongeReflectionReferenceSubtractedResult` in `scalar_wave_3d.py`, 9 annotated fields were redundantly repeated after the compatibility property `@property def surface_integrated_return_flux_ratio`.
  3. In `solve_dirichlet_independent_matrix_free_sor`, `isinstance(max_iterations, (int, np.integer))` permitted `bool` inputs (`isinstance(True, int) == True`).
- **Resolution:**
  1. Corrected all documentation to use strict `E_arb` units. Clarified initial energy values:
     - Initial discrete leapfrog Hamiltonian: $H^{-1/2} = 7.80852\text{ E}_\text{arb}$ (`compute_exact_discrete_leapfrog_energy`).
     - Initial sampled continuum diagnostic: $E_\text{init} = 7.67857\text{ E}_\text{arb}$ (`compute_interior_energy`).
     - Residual at $\Delta t_0$: $0.02483\text{ E}_\text{arb}$ on $E_\text{init} = 7.67857\text{ E}_\text{arb}$ ($0.3233\%$).
  2. Removed the 9 redundant field lines in `SpongeReflectionReferenceSubtractedResult` in `scalar_wave_3d.py`.
  3. In `electrostatics_numerics.py`, updated validation to `if isinstance(max_iterations, bool) or not isinstance(max_iterations, (int, np.integer)) or max_iterations < 1:`, rejecting boolean inputs. Added unit tests for `max_iterations=True` and `max_iterations=False` in `tests/test_p1_numerics.py`.

---

## 2. Verification and Invariant Checks
- **P0 Baseline Preservation:** `git diff electrostatics_baseline.py` is 100% empty (byte-for-byte preserved).
- **Unit Test Suite:** All 71 unit tests passed locally (`Ran 71 tests in 272.248s OK`).
- **Artifacts:** Regenerated `electrostatics_manifest.json` and `electrostatics_baseline.png` via `MPLBACKEND=Agg python3 examples/electrostatics_demo.py`.
- **PR Status:** PR #10 remains in **DRAFT** status; no self-merging or approval.
- **P2 Hold:** Phase 2 (Issue #7 / Exodus patent geometry) has not been initiated.
