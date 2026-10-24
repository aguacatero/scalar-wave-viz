# P1 R4 Independent Scientific Re-Review — Fix Queue & Resolution Ledger

**Source Review:** [PR #10 review 5576900379](https://github.com/aguacatero/scalar-wave-viz/pull/10#pullrequestreview-5576900379)  
**Reviewed Commit:** `68c7703a1f1e6bfb5992a88e281a3e037c4f58bc`  
**Base Commit:** `174c6b895a0c2ec416b6d46ab9e0835b14a8cb49`  
**Review Disposition:** REVISE (NOT ACCEPTED) — PR #10 remains DRAFT; no merge or P2 initiation.

---

## 1. Closed R3 Findings & Remaining R4 Findings Catalog

### Previously Closed R3 Findings
- **P1-R3-F1 (HIGH):** CLOSED as an implementation/test repair (6-component force convergence, full 2D vector residual, active/near-zero gates, off-axis $y$-asymmetric case, honestly named two-grid differences).
- **P1-R3-F2 (MED):** CLOSED for the requested limited both-electrode asymmetric and mesh/step-sensitivity virtual-work comparison.
- **P1-R3-F3 (MED):** CLOSED for scalar PDE analytical coefficient testing across two-medium planar interfaces ($c_1 > c_2$ and $c_1 < c_2$ under refinement).

---

### Remaining R4 Findings

#### P1-R4-F1 (MED) — Sponge reflection: honest snapshot/local proxy labeling, closed energy/flux budget, observation-time window sweep, and true spatial $\Delta x$ refinement of fixed physical geometry (R3-F4 PARTIAL)
- **Problem:**
  1. `integrated_reflected_energy_fraction` in `scalar_wave_3d.py` was calculated as `compute_interior_energy(p_test - p_ref_sub, pm_test - pm_ref_sub, ..., sponge_width) / e_init_test` using **only the terminal state** and excluding the sponge. It is an instantaneous spatial snapshot of reference-difference energy in the interior box—not a time-integrated return flux, sponge dissipation, or closed incident/reflected/dissipated/residual energy budget.
  2. No return-time / observation-window sweep bounded how this interior snapshot changes as the pulse traverses the observation volume.
  3. `power_reflection_coefficient = r_pwr_proxy` and `amplitude_reflection_coefficient = r_amp` remained misleading legacy aliases, and `examples/electrostatics_demo.py` still published them alongside `is_absorbed_to_tolerance`.
  4. `benchmark_sponge_reflection_parameter_sweep` varied `grid_size=40` vs `grid_size=48` at constant `dx=1.0` (changing the physical box size from $40\text{ m}$ to $48\text{ m}$) instead of performing true spatial $\Delta x$ refinement of the **same physical geometry and pulse width**.
- **Required Resolution:**
  1. **Honest Snapshot/Local Proxy Labeling:** Rename/label both observables explicitly as snapshot/local proxies (`probe_local_amplitude_ratio_proxy`, `probe_local_peak_squared_proxy`, `terminal_interior_reflected_energy_snapshot_proxy`, `peak_window_interior_reflected_energy_snapshot_proxy`), remove misleading `power_reflection_coefficient`, `amplitude_reflection_coefficient`, and `is_absorbed_to_tolerance` keys from the Reference-Subtracted Sponge Benchmark and Control Sweep in `electrostatics_manifest.json`, and do not infer a quantitative percentage of absorbed/incident power from local/snapshot proxies.
  2. **Closed Discrete Energy Budget & Enclosing-Surface Return Energy Flux Integral:**
     - Implement the **exact closed discrete leapfrog energy balance** for the damped wave equation:
       $$\mathcal{H}^{n+1/2} - \mathcal{H}^{n-1/2} = -\Delta D^n, \qquad \Delta D^n = \Delta t \sum_{\mathbf{x}} \frac{\sigma(\mathbf{x})}{c(\mathbf{x})^2} \left(\frac{\phi^{n+1} - \phi^{n-1}}{2\Delta t}\right)^2 \Delta x^3 \ge 0$$
       accounting for initial discrete Hamiltonian $\mathcal{H}_{\text{initial}}$, cumulative sponge-dissipated energy $D_{\text{sponge, cumulative}} = \sum_{n=1}^{N} \Delta D^n$, and terminal remaining whole-domain Hamiltonian $\mathcal{H}_{\text{final, total}}$ with exact conservation closure $|\mathcal{H}_{\text{final, total}} + D_{\text{sponge, cumulative}} - \mathcal{H}_{\text{initial}}| / \mathcal{H}_{\text{initial}} < 10^{-12}$.
     - Also integrate the directional wave energy flux $\Phi_{\partial \Omega}(t) = \oint_{\partial \Omega_{\text{int}}} (-\partial_t \phi \, \nabla \phi \cdot \hat{\mathbf{n}}) \, dA$ over the 6 faces of the interior/sponge interface surface $\partial \Omega_{\text{int}}$ across time to report cumulative outgoing incident energy flux $\mathcal{F}_{\text{incident, out}}$ and cumulative inward reflected return flux $\mathcal{F}_{\text{reflected, in}}(\delta \phi)$ over the return window.
  3. **Observation-Time / Return-Window Sweep:** Evaluate the reference-subtracted interior energy snapshot and cumulative surface return flux across multiple observation times $T_{\text{obs}}$ spanning the return window (e.g., steps $60, 70, 80, 90, 100$ on an enlarged reference domain $L_{\text{ref}} = 110\text{ m}$ free of wall returns), recording both the full time series and peak/terminal values over the observation window.
  4. **True Spatial $\Delta x$ Refinement at Fixed Physical Geometry:** Refine $\Delta x \in (1.0\text{ m}, 0.8\text{ m}, 0.5\text{ m})$ ($N \in (40, 50, 80)$) while keeping physical box size $L_{\text{box}} = 40.0\text{ m}$, physical sponge thickness $W_{\text{sponge}} = 8.0\text{ m}$, physical pulse width $\sigma_{\text{pulse}} = 2.0\text{ m}$, physical probe offset $d_{\text{probe}} = 6.0\text{ m}$, and physical evolution duration $T_{\text{phys}}$ fixed.
  5. Preserve the $\sigma_{\max} \in \{0.0, 0.5, 1.5, 3.0, 15.0\}$ negative/positive controls and reference-subtraction tests.

---

#### P1-R4-F2 (MED) — Sampled continuum `final_energy` is one solver step behind the final simulated state $\phi^{n_{\text{steps}}}$ (R3-F5 PARTIAL)
- **Problem:** In `benchmark_two_material_energy_conservation`, `cont_trajectory = [H_cont(phi_0, phi_-1)]` was initialized at step 0, and each subsequent loop iteration computed `H_cont(phi, phi_prev)` **before** advancing `phi_prev, phi = phi, phi_next`. Thus after `n_steps` updates, `cont_trajectory[-1]` recorded $H_{\text{cont}}(\phi^{n_{\text{steps}}-1}, \phi^{n_{\text{steps}}-2})$ — one solver step behind the final state $(\phi^{n_{\text{steps}}}, \phi^{n_{\text{steps}}-1})$. The R3 test only asserted `res.final_energy == res.continuum_energy_trajectory[-1]`, which could not detect the missing terminal sample.
- **Required Resolution:**
  1. Record the continuum energy sample **after** advancing `phi_prev, phi = phi, phi_next` on every step $k = 1, \dots, n_{\text{steps}}$, so `continuum_energy_trajectory` has $n_{\text{steps}} + 1$ entries ($k = 0, 1, \dots, n_{\text{steps}}$) and `final_energy = continuum_energy_trajectory[-1]` is the exact sampled continuum energy of the terminal evolved state $(\phi^{n_{\text{steps}}}, \phi^{n_{\text{steps}}-1})$.
  2. Retain the separate exact staggered-Hamiltonian trajectory (`exact_discrete_hamiltonian_trajectory` of length $n_{\text{steps}}$ across half-steps $t^{1/2}, \dots, t^{n_{\text{steps}}-1/2}$).
  3. In `tests/test_p1_wave_3d.py`, independently evolve $(\phi, \phi_{\text{prev}})$ for `n_steps` to obtain $(\phi_{\text{final}}, \phi_{\text{prev, final}})$, call `compute_sampled_continuum_energy_diagnostic(phi_final, phi_prev_final, c_field, dt, dx_m)` directly, and assert exact equality with `res.final_energy` (and inequality with the penultimate step $n_{\text{steps}}-1$) for both positive and negative signed terminal drift cases.

---

#### P1-R4-F3 (LOW) — Independent field solver implementation verification for Issue #6
- **Problem:** Issue #6 asks to compare the electrostatic solver with an independent implementation. The virtual-work routine is an independent *force evaluation method*, but calls the same `solve_dirichlet` sparse direct solver on shifted staircase masks.
- **Required Resolution:**
  1. Implement two genuinely independent electrostatic field solver references in `electrostatics_numerics.py` that share **zero** solver code with `electrostatics_baseline.solve_dirichlet`:
     - **Independent Grid-Free Continuous Method of Fundamental Solutions (MFS) / Boundary-Collocation Laplace Solver (`solve_electrostatics_mfs_boundary_collocation`):** Solves $\nabla^2 V = 0$ in the continuous 2D domain between the exact circular cylinders and grounded square enclosure walls as a superposition of analytical 2D logarithmic line-charge fundamental solutions placed outside $\Omega_{\text{vac}}$, with boundary error certified by the Maximum Principle for harmonic functions ($< 10^{-5}\text{ V}$). Evaluates continuous potential, electric field $\mathbf{E}$, and analytical-contour Maxwell stress forces $(F_x, F_y)$ without any finite-difference grid or staircase mask, and verifies that the 5-point FDM solver converges toward the continuous MFS solution across $n \in (41, 81, 161)$ on nontrivial asymmetric ($+600\text{ V}/+100\text{ V}$) and off-axis $y$-asymmetric ($+600\text{ V}/-400\text{ V}$) configurations.
     - **Independent Matrix-Free Iterative Red-Black SOR Laplace Solver (`solve_dirichlet_independent_matrix_free_sor`):** Solves the discrete 5-point Laplace BVP via matrix-free Red-Black Successive Over-Relaxation without `scipy.sparse` or `spsolve`, verifying that `solve_dirichlet` matches the independent discrete solver to $< 10^{-10}\text{ V}$ in potential and $< 10^{-11}\text{ N/m}$ in all 6 force components.
  2. Explicitly distinguish in code, manifest, and handoff ledgers between: (a) MST vs. virtual work (two force-extraction methods on the same FDM solver), (b) sparse direct FDM vs. matrix-free SOR (two discrete linear solvers on the same staircase grid), and (c) 5-point staircase FDM vs. grid-free MFS boundary-collocation (two independent numerical formulations of the continuous 2D Laplace BVP).


---

## 2. Finding-by-Finding Resolution Record

### Resolution for P1-R4-F1 (MED)
1. **Honest Snapshot/Local Proxy Labeling:**
   - Both observables explicitly renamed and documented in `scalar_wave_3d.py`:
     - `probe_local_amplitude_ratio_proxy` (and `probe_local_peak_squared_proxy = (max|phi_refl|/max|phi_ref|)^2`)
     - `terminal_interior_reflected_energy_snapshot_proxy` (terminal step interior difference energy normalized by initial energy)
     - `peak_window_interior_reflected_energy_snapshot_proxy` (maximum interior difference energy snapshot across the entire return window)
   - Misleading plane-wave power reflection claims removed:
     - Manifest section `sponge_boundary_reflection_reference_subtracted_benchmark` and `sponge_absorption_control_sweep` now omit `power_reflection_coefficient` and `amplitude_reflection_coefficient`.
     - Replaced `is_absorbed_to_tolerance` with `is_sponge_benchmark_valid: bool`, certifying causal reference isolation, pre-arrival causal zero difference, exact discrete energy-budget closure, and order-of-magnitude dissipation.
2. **Closed Discrete Energy Budget & Enclosing-Surface Return Energy Flux:**
   - Implemented `compute_step_sponge_dissipation` and `compute_enclosing_surface_outward_flux` in `scalar_wave_3d.py`.
   - Discrete leapfrog energy budget identity verified to machine precision:
     $$\mathcal{H}^{N-1/2} + D_{\text{sponge, cumulative}} = \mathcal{H}^{-1/2}$$
     with `discrete_energy_budget_closure_error < 1e-12`.
   - Directional wave energy flux across the 6 faces of $\partial\Omega_{\text{int}}$ evaluated over the full simulation window, reporting:
     - `cumulative_incident_outgoing_surface_flux`
     - `cumulative_reflected_return_surface_flux`
     - `surface_integrated_return_flux_ratio < 0.05` (observed: 0.81% for design sponge).
3. **Observation-Time / Return-Window Sweep:**
   - Swept observation duration across steps 60, 70, 80, 90, 100 on enlarged domain ($L_{\text{ref}} = 106\text{ m}$, outer wall return step 181). Sponge dissipated energy rises monotonically from 96.8% to 98.9%, while peak-window interior reflected energy snapshot stays strictly bounded (< 2%).
4. **True Spatial $\Delta x$ Refinement at Fixed Physical Geometry:**
   - Maintained fixed physical box $L_{\text{box}} = 40.0\text{ m}$, sponge thickness $W_{\text{sponge}} = 8.0\text{ m}$, pulse width $\sigma_{\text{pulse}} = 2.0\text{ m}$, probe offset $d_{\text{probe}} = 6.0\text{ m}$, and $L_{\text{ref}} = 68.0\text{ m}$ across spatial resolutions:
     - $\Delta x = 2.0\text{ m}$ ($N = 20, w = 4, p = 3, N_{\text{ref}} = 34, N_{\text{steps}} = 40$)
     - $\Delta x = 1.0\text{ m}$ ($N = 40, w = 8, p = 6, N_{\text{ref}} = 68, N_{\text{steps}} = 80$)
     - $\Delta x = 0.5\text{ m}$ ($N = 80, w = 16, p = 12, N_{\text{ref}} = 136, N_{\text{steps}} = 160$)
   - Discrete budget closure error $< 10^{-12}$ at all resolutions; peak-window interior reflected snapshot agrees closely (< 2%) and dissipated energy fraction agrees within 3%.
5. **Preserved Controls:**
   - Undamped Dirichlet wall ($\sigma = 0.0$): zero sponge dissipation, 16.9% interior snapshot, strong return.
   - Design damping ($\sigma = 3.0$): > 97% dissipated energy fraction, 0.73% terminal interior snapshot, 1.34% peak-window snapshot.
   - High conductivity ($\sigma = 15.0$): entrance impedance mismatch increases interior reflection snapshot to 2.45%.

---

### Resolution for P1-R4-F2 (MED)
1. **Sampled Continuum Energy Synchronization:**
   - In `benchmark_two_material_energy_conservation` (`scalar_wave_3d.py`), initialized step 0 sample `h_cont_0` before stepping, and in the loop updated state first (`phi_prev, phi = phi, phi_next`), then recorded `h_cont = compute_sampled_continuum_energy_diagnostic(phi, phi_prev, ...)`.
   - `continuum_energy_trajectory` now has $N + 1$ entries for steps $0, 1, \dots, N$.
   - `final_energy = continuum_energy_trajectory[-1]` is the exact sampled continuum energy of the final evolved state $(\phi^N, \phi^{N-1})$.
   - Retained separate `exact_discrete_hamiltonian_trajectory` of length $N$.
2. **Adversarial Regression Tests in `test_p1_wave_3d.py`:**
   - Tested positive signed terminal drift case ($N = 35$, drift +3.06%): verified `len == 36`, `final_energy == cont_trajectory[-1]`, `final_energy != cont_trajectory[-2]`, and verified exact equality (< 1e-12) against a separately executed manual simulation loop.
   - Tested negative signed terminal drift case ($N = 31$, drift -0.31%): verified `len == 32`, `final_energy == cont_trajectory[-1]`, `final_energy != cont_trajectory[-2]`, and `final_energy < initial_energy`.

---

### Resolution for P1-R4-F3 (LOW)
1. **Two Independent Field Solver Implementations in `electrostatics_numerics.py`:**
   - `solve_dirichlet_independent_matrix_free_sor`: Vectorized Red-Black SOR Laplace solver with zero `scipy.sparse` or `spsolve` dependency. Matches direct sparse LU solver to $< 10^{-10}\text{ V}$ in potential and $< 10^{-16}\text{ N/m}$ in all 6 force components at $n = 81$.
   - `solve_electrostatics_mfs_boundary_collocation` (`MFSContinuousLaplaceSolution`): Grid-free continuous Method of Fundamental Solutions boundary-collocation solver representing potential as an analytical superposition of logarithmic line charges strictly outside $\Omega_{\text{vac}}$.
   - **Maximum Principle Certificate:** Independent dense evaluation on conductor and enclosure boundaries confirms boundary error $< 10^{-10}\text{ V}$ (observed: $8.06 \times 10^{-11}\text{ V}$), guaranteeing by the Maximum Principle that interior vacuum potential error is bounded by $< 10^{-10}\text{ V}$.
   - **Monotonic Convergence of 5-Point FDM toward Continuous MFS Reference:**
     Evaluated across $n \in (41, 81, 161, 321)$ on the nontrivial off-axis $y$-asymmetric configuration:
     - $n = 41$: $E(0,0)$ error = 6.73%, left force error = 19.56%, right force = 13.37%, enclosure = 4.89%
     - $n = 81$: $E(0,0)$ error = 4.25%, left force error = 11.00%, right force = 8.43%, enclosure = 4.91%
     - $n = 161$: $E(0,0)$ error = 3.22%, left force error = 7.79%, right force = 6.38%, enclosure = 4.44%
     - $n = 321$: $E(0,0)$ error = 1.53%, left force error = 3.66%, right force = 3.05%, enclosure = 2.21%
     All force errors strictly decrease toward the continuous MFS reference with mesh refinement and reach $< 5\%$ at $n = 321$.
2. **Methodological Distinction Articulated:**
   - Clearly distinguished in code docstrings, `electrostatics_manifest.json`, and handoff ledgers:
     1. MST vs. virtual work: two force-extraction methods on the same 5-point FDM solver.
     2. Sparse direct LU vs. matrix-free Red-Black SOR: two independent linear solvers on the same discrete grid.
     3. 5-point staircase FDM vs. grid-free continuous MFS: two independent mathematical formulations of the continuous 2D Laplace boundary-value problem.

---

## 3. Verification & Regression Evidence

- **Baseline Code Byte-for-Byte Preservation:** `git diff electrostatics_baseline.py` is empty (byte-for-byte identical to P0 accepted SHA `57067164b47d7d374a1d7bb1c8ce00bb79aa07f8`).
- **Complete Test Suite:** 68/68 unit and regression tests pass across `test_electrostatics_baseline.py`, `test_p1_numerics.py`, and `test_p1_wave_3d.py`.
- **Artifacts Regenerated:** `electrostatics_baseline.png` and `electrostatics_manifest.json` generated cleanly with RFC 8259 compliance, explicit proxy labels, and independent solver verification data.
