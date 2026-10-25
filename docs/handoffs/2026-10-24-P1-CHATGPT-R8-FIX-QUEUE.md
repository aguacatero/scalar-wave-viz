# P1 R8 Finding-by-Finding Fix Queue & Resolution Ledger

- **Repository:** https://github.com/aguacatero/scalar-wave-viz
- **PR:** #10 (Draft)
- **Review Identifier:** [`pullrequestreview-5640656794`](https://github.com/aguacatero/scalar-wave-viz/pull/10#pullrequestreview-5640656794)
- **Reviewed Source HEAD SHA:** `236dd751203efa1d551c9d2b26e490793b95a799`
- **Disposition:** REVISE / NOT ACCEPTED
- **Pickup Mode:** `MANUAL-ONLY`
- **Target Review Round:** R9

---

## 1. Finding-by-Finding Breakdown & Root-Cause Analysis

### P1-R8-F1 (HIGH) — Exact local continuity theorem omits source work for an input supported by the production FDTD stepper
- **Finding:**
  The production stepper `step_wave_fdtd` accepts `source_field` and evolves $\frac{\phi^{n+1} - 2\phi^n + \phi^{n-1}}{c^2 \Delta t^2} + \frac{\sigma}{c^2} \frac{\phi^{n+1} - \phi^{n-1}}{2\Delta t} = \nabla^2 \phi + \frac{S}{c^2}$.
  However, the discrete local continuity identity introduced in R7 omitted source-work accounting and did not explicitly restrict the identity to source-free updates or account for source work.
- **Root-Cause Analysis:**
  Multiplying the discrete wave equation by the centered velocity $\frac{\phi_i^{n+1} - \phi_i^{n-1}}{2\Delta t} \Delta x^3$ produces an exact source power density $(S_i / c_i^2) \frac{\phi_i^{n+1} - \phi_i^{n-1}}{2\Delta t} \Delta x^3$. Over time step $\Delta t$, the source work done on $\Omega_\text{int}$ is:
  $$\Delta W_{\text{source, int}}^n = \Delta t \Delta x^3 \sum_{i \in \Omega_\text{int}} \frac{S_i^n}{c_i^2} \left( \frac{\phi_i^{n+1} - \phi_i^{n-1}}{2\Delta t} \right)$$
  The complete discrete local continuity theorem on any Cartesian subvolume $\Omega_\text{int}$ is therefore:
  $$H_\text{int}^{N-1/2} - H_\text{int}^{-1/2} + \sum_{n=0}^{N-1} \Delta B_\text{boundary}^n + \sum_{n=0}^{N-1} \Delta D_\text{int}^n = \sum_{n=0}^{N-1} \Delta W_{\text{source, int}}^n$$
- **Resolution:**
  1. Implemented `compute_interior_source_work_step` in `scalar_wave_3d.py`.
  2. Updated public docstrings of `compute_interior_exact_discrete_leapfrog_energy` and `compute_exact_discrete_interior_boundary_transfer` to state the complete theorem including source work.
  3. Added adversarial test in `tests/test_p1_wave_3d.py` (`test_exact_discrete_interior_control_volume_hamiltonian_and_boundary_transfer`, Part C) with active sinusoidal source inside $\Omega_\text{int}$, verifying closure to machine precision ($< 10^{-12}$, observed $\approx 10^{-16}$).

### P1-R8-F2 (MED) — Continuum-proxy residual growth is mischaracterized as an asymptotic O(dt) truncation law
- **Finding:**
  The R7 docstrings and fix ledger characterized the residual between `compute_interior_energy` and the centered flux proxy as exhibiting an "$O(\Delta t)$ truncation residual growth" under temporal refinement. Extended independent refinement through $\Delta t_0/16$ showed that the residual levels off at a nonzero bound (~5.57%) rather than continuing to grow or vanishing.
- **Root-Cause Analysis:**
  The continuum comparison reflects two structural differences: differing velocity time-staggering ($(\phi^n - \phi^{n-1})/\Delta t$ vs $(\phi^{n+1} - \phi^{n-1})/(2\Delta t)$) and discretely inconsistent spatial energy/flux formulations (finite-difference continuum gradient density vs discrete leapfrog boundary bonds). At fixed spatial grid spacing $\Delta x$, taking $\Delta t \to 0$ eliminates only time-staggering errors, leaving a finite spatial discretization mismatch (~5.57% for this Gaussian pulse).
- **Resolution:**
  1. Removed unproven asymptotic $O(\Delta t)$ and $O(\Delta t^2 + \Delta x^2)$ language from `scalar_wave_3d.py` docstrings (`compute_enclosing_surface_outward_flux`, `compute_discrete_energy_density`, `metric_definition_note`).
  2. Described the metric plainly as a finite-grid diagnostic mismatch that levels off around ~5.57% under temporal refinement at fixed $\Delta x$.
  3. Updated `test_interior_control_volume_flux_continuity_and_residual` in `tests/test_p1_wave_3d.py` to evaluate the complete refinement sequence: $\Delta t_0$ (0.3233%), $\Delta t_0/2$ (4.0432%), $\Delta t_0/4$ (5.1173%), $\Delta t_0/8$ (5.4505%), $\Delta t_0/16$ (5.5656%), verifying that the residual levels off at ~5.57% rather than vanishing.

### P1-R8-F3 (MED) — Newly certified local identity is not covered by the claimed spatial/material suite or serialized as a reconstructable local budget
- **Finding:**
  1. The R7 test evaluated only $dx=1$, uniform $c=1$, centered Gaussian. It lacked tests for $dx=0.5$, variable $c(x)$, off-center wave crossings, and independent bond enumeration.
  2. The interior H/B/D budget was not serialized into the evidence manifest.
  3. Invalid `sponge_width` values silently fell back to whole-domain or 0.0 rather than failing closed.
- **Resolution:**
  1. **Fail-Closed Validation:** Implemented `validate_interior_sponge_width(sponge_width, grid_dim)` enforcing $1 \le sponge\_width < grid\_dim // 2$ with strict integer checks (rejecting booleans and out-of-range values with `ValueError`) across all interior functions (`compute_interior_exact_discrete_leapfrog_energy`, `compute_exact_discrete_interior_boundary_transfer`, `compute_interior_sponge_dissipated_energy`, `compute_interior_source_work_step`, `compute_enclosing_surface_outward_flux`). Added unit tests asserting `ValueError`.
  2. **Comprehensive Test Coverage:** In `tests/test_p1_wave_3d.py`, added:
     - Spatial refinement test at $dx=0.5\text{ m}$ ($80^3$ grid, $sw=16$) at fixed physical geometry and duration ($< 10^{-12}$ closure).
     - Nonuniform variable wave speed $c(x) = 1.0 + 0.2\sin(2\pi x / L)$ ($< 10^{-12}$ closure).
     - Off-center asymmetric wave pulse crossing ($< 10^{-12}$ closure).
     - Independent bond-by-bond graph enumeration matching the face-slice implementation to machine precision ($< 10^{-14}$).
  3. **Manifest Serialization:** Implemented `InteriorControlVolumeBudgetResult` and `benchmark_interior_control_volume_budget()`, and serialized `exact_discrete_interior_control_volume_budget` into `p1_3d_scalar_wave_numerics_audit` in `electrostatics_manifest.json`.

### P1-R8-F4 (LOW) — Pre-existing fix ledger still publishes wrong units and obsolete <1% continuity criterion
- **Finding:**
  `docs/handoffs/2026-10-24-P1-CHATGPT-R6-FIX-QUEUE.md` still contained `0.025 J`, `7.81 J` and `<1%` continuum local continuity language after the R7 counterexample.
- **Resolution:**
  Added an explicit superseded/correction warning notice at the top of `docs/handoffs/2026-10-24-P1-CHATGPT-R6-FIX-QUEUE.md`, linking to the R7 and R8 ledgers, correcting units to `0.02483 E_arb / 7.67857 E_arb` for the sampled continuum diagnostic, noting that `< 1%` was a single-dt coincidental proxy agreement, and updating Section 3.1.

---

## 2. Verification and Invariant Checks
- **P0 Baseline Preservation:** `git diff electrostatics_baseline.py` is 100% empty (byte-for-byte preserved).
- **Unit Test Suite:** All 72 unit tests passed locally (`Ran 72 tests in 276.577s OK`).
- **Artifacts:** Regenerated `electrostatics_manifest.json` and `electrostatics_baseline.png` via `MPLBACKEND=Agg python3 examples/electrostatics_demo.py`.
- **PR Status:** PR #10 remains in **DRAFT** status; no self-merging or approval.
- **P2 Hold:** Phase 2 (Issue #7 / Exodus patent geometry) has not been initiated.
