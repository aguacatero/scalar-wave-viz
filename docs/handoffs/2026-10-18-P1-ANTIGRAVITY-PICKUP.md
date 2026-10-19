# P1 — Antigravity / Hermes implementation pickup and independent review contract

**STATE: READY FOR CHATGPT INDEPENDENT RE-REVIEW — P1 R4. PR #10 REMAINS DRAFT; DO NOT MERGE.**

- Repository: https://github.com/aguacatero/scalar-wave-viz
- Tracker: [Issue #6](https://github.com/aguacatero/scalar-wave-viz/issues/6)
- Branch: `p1-numerics-force-accounting-2026-10-18`; base: `main`
- **Current draft PR: [#10](https://github.com/aguacatero/scalar-wave-viz/pull/10)** — P1-A, P1-B, P1-C, and P1-D fully implemented and tested with 65 passing unit tests (0 failures, 0 errors).
- P0 merged [PR #5](https://github.com/aguacatero/scalar-wave-viz/pull/5) as merge commit `174c6b895a0c2ec416b6d46ab9e0835b14a8cb49` on 2026-10-18 (Pacific)
- Independently accepted P0 implementation code SHA: `57067164b47d7d374a1d7bb1c8ce00bb79aa07f8` — preserved byte-for-byte in `electrostatics_baseline.py`.
- Next milestone: P1 **only**. P2 patent FIGS. 4–8 model is reserved for [Issue #7](https://github.com/aguacatero/scalar-wave-viz/issues/7) after P1's independent acceptance.
- Scheduler status: `PICKUP: MANUAL-ONLY` (no active background cron/poller verified).
- Fix ledgers:
  - `docs/handoffs/2026-10-19-P1-CHATGPT-R1-FIX-QUEUE.md` tracking R1 review [`pullrequestreview-5571628683`](https://github.com/aguacatero/scalar-wave-viz/pull/10#pullrequestreview-5571628683).
  - `docs/handoffs/2026-10-19-P1-CHATGPT-R2-FIX-QUEUE.md` tracking R2 review [`pullrequestreview-5573216899`](https://github.com/aguacatero/scalar-wave-viz/pull/10#pullrequestreview-5573216899).
  - `docs/handoffs/2026-10-19-P1-CHATGPT-R3-FIX-QUEUE.md` tracking R3 review [`pullrequestreview-5575193859`](https://github.com/aguacatero/scalar-wave-viz/pull/10#pullrequestreview-5575193859).

---

## 1. Implemented Scope & P1 R3 Finding Resolutions

### P1-R3-F1 (HIGH): Full-Vector 6-Component Force Convergence, Near-Zero Component Gating, Off-Axis $F_y$ Benchmark, and Honest Discretization Difference Reporting (`electrostatics_numerics.py`)
- **Full 6-Component Force & 2D Residual Tracking (`ForceMeshConvergenceRow`, `evaluate_force_convergence_from_rows`, `force_mesh_convergence_study`):**
  - Carries all 6 conductor force components (`left_electrode_fx_n_per_m`, `left_electrode_fy_n_per_m`, `right_electrode_fx_n_per_m`, `right_electrode_fy_n_per_m`, `enclosure_reaction_fx_n_per_m`, `enclosure_reaction_fy_n_per_m`) and full 2D net residual (`net_residual_fx_n_per_m`, `net_residual_fy_n_per_m`, `net_residual_magnitude_n_per_m`) across every mesh resolution $n$.
  - Active components ($\max(|F_\text{curr}|, |F_\text{prev}|) > 10^{-6}\text{ N/m}$) are gated on both relative change ($\le 5\%$) and absolute change ($\le 5\times 10^{-4}\text{ N/m}$); near-zero components ($\le 10^{-6}\text{ N/m}$) are gated on absolute change ($\le 10^{-6}\text{ N/m}$) and magnitude ($\le 10^{-6}\text{ N/m}$) so no component is silently skipped.
  - Replaced `uncertainty_budget_n_per_m` with `per_component_last_step_diff_n_per_m`, `max_component_last_step_diff_n_per_m`, `max_vector_last_step_diff_n_per_m`, `left_fx_last_step_diff_n_per_m`, and `discretization_error_note` explicitly stating these are two-grid finite-difference shifts rather than a probabilistic uncertainty budget.
  - Added off-axis $y$-asymmetric configuration (`left=(-8, +4) mm, +600 V`; `right=(+8, -2) mm, -400 V`) where all 6 $F_x, F_y$ components are active and converge across $n \in (41, 81, 161)$ with 2D vector residual $< 10^{-7}\text{ N/m}$, plus adversarial negative-control tests verifying that corrupting any active or near-zero $F_y$ component or $y$-residual fails closed.

### P1-R3-F2 (MED): Multi-Resolution & Asymmetric Virtual-Work Cross-Check with Step-Size Sensitivity (`electrostatics_numerics.py`)
- **Exact Integer Lattice Translation (`compute_virtual_work_force_x`):**
  - Eliminated IEEE-754 floating-point tie-breaking on $(x - c_x)^2 + (y - c_y)^2 \le r^2$ when $\Delta x = k \cdot h$ by translating the discrete electrode mask by exact integer lattice steps ($\pm k$), preserving discrete circle pixel counts across shifts.
- **Multi-Resolution & Step-Size Study (`virtual_work_convergence_and_sensitivity_study`):**
  - Evaluates both `left` and `right` electrode shifts at $\Delta x \in (1h, 2h)$ across $n \in (81, 161)$ for both symmetric ($\pm 500\text{ V}$: $8.62\% \to 4.49\%$, step sensitivity $0.09\%$) and asymmetric ($+600\text{ V}/+100\text{ V}$: left $11.84\% \to 6.00\%$, right $18.68\% \to 9.61\%$, net electrode pair pull $13.08\% \to 6.67\%$).
  - Explicitly attributes the $O(h)$ discrepancy to staircase boundary truncation of central-gradient energy near circular electrode masks.

### P1-R3-F3 (MED): Analytical Two-Material Interface Reflection & Transmission Benchmark (`scalar_wave_3d.py`)
- **Analytical Derivation & Multi-Resolution Convergence (`benchmark_two_material_interface_transmission`):**
  - Derived exact normal-incidence continuity conditions ($\phi$ and $\partial_x \phi$ continuous) for the non-divergence wave PDE $\phi_{tt} = c(x)^2 \nabla^2 \phi$:
    $$R_\text{amp} = \frac{c_2 - c_1}{c_1 + c_2}, \qquad T_\text{amp} = \frac{2 c_2}{c_1 + c_2} = 1 + R_\text{amp}, \qquad \mathcal{R}_E + \mathcal{T}_E = |R_\text{amp}|^2 + \frac{c_1}{c_2}|T_\text{amp}|^2 = 1$$
  - Added `boundary_mode='planar_x'` and evaluated across $\Delta x \in (1.0, 0.5, 0.25)$ with matched homogeneous reference subtraction.
  - Verified both high-to-low speed ($c_1=1.0 \to c_2=0.6$: $R_\text{exact}=-0.25, T_\text{exact}=+0.75$; finest $R_\text{meas}=-0.2516, T_\text{meas}=+0.7507, \mathcal{R}_E+\mathcal{T}_E=1.0026$) and low-to-high speed ($c_1=0.6 \to c_2=1.0$: $R_\text{exact}=+0.25, T_\text{exact}=+1.25 > 1.0$; finest $R_\text{meas}=+0.2506, T_\text{meas}=+1.2490, \mathcal{R}_E+\mathcal{T}_E=1.0020$), with monotonically decreasing errors under refinement.

### P1-R3-F4 (MED): Single-Probe Proxy Labeling, 3D Integrated Reflected Energy, Geometric Travel-Time Gating, and Parameter Sweep (`scalar_wave_3d.py`)
- **Honest Metric Labeling & 3D Volume-Integrated Energy (`benchmark_sponge_reflection_reference_subtracted`):**
  - Labeled the single-probe ratio as `probe_peak_squared_reflection_proxy` ($2.875\%$) and `probe_amplitude_reflection_ratio` ($16.96\%$) with `metric_definition_note` explaining $1/r$ spherical spreading.
  - Added 3D volume-integrated interior reflected energy fraction `integrated_reflected_energy_fraction` ($E_\text{interior}(\phi_\text{test} - \phi_\text{ref}) / E_\text{initial} = 0.730\%$ at $\sigma_\text{max}=3.0$ vs $16.89\%$ at $\sigma_\text{max}=0.0$).
  - Computed `geometric_pre_arrival_step = 10` and `reference_wall_return_step = 154 > n_steps = 80` from physical travel distances.
- **Parameter Sweep & Adversarial Reference-Domain Check (`benchmark_sponge_reflection_parameter_sweep`):**
  - Verified reference-domain size invariance (`ref=90` vs `106` diff $= 0.0 < 10^{-10}$), $\Delta t$ refinement stability ($1.30\%$ shift), monotonic reflection reduction across sponge widths $w \in (6, 8, 10)$ ($1.414\% \to 0.730\% \to 0.257\%$), and adversarial failure when `ref_grid_size=50` is contaminated by wall return.

### P1-R3-F5 (MED): Actual Terminal Sampled Continuum Energy vs Maximum Trajectory Drift (`scalar_wave_3d.py`)
- **True Terminal Sampled Energy (`benchmark_two_material_energy_conservation`):**
  - Replaced fabricated `h_cont_0 * (1.0 + max_cont_drift)` (`13.861270`) with actual terminal sampled continuum energy `cont_trajectory[-1]` (`13.375565`), alongside `terminal_continuum_signed_drift_ratio` (`+2.01%`), `max_continuum_diagnostic_drift_ratio` (`5.71%`), and `continuum_energy_trajectory`.
  - Added adversarial regression test at `n_steps=32` where terminal continuum drift is negative (`13.071842 < 13.112037`, signed drift $-0.31\%$).

---

## 2. Test Suite & Evidence
- **Total unit tests:** **65 passed** (0 failures, 0 errors).
  - 35 baseline regression tests in `tests/test_electrostatics_baseline.py` (all green).
  - 13 P1 electrostatic numerics & Maxwell stress tests in `tests/test_p1_numerics.py` (all green).
  - 17 P1 3D scalar wave numerics & benchmark tests in `tests/test_p1_wave_3d.py` (all green).
- Local execution: `python3 -m unittest discover -s tests -v`.
- Demo and manifest execution: `MPLBACKEND=Agg python3 examples/electrostatics_demo.py` generates valid PNG and RFC 8259 compliant manifest.

---

## 3. Explicit Non-Claims
1. **No patent geometry reproduction:** Idealized cylindrical electrode disks in a grounded box; does not reproduce Exodus patent US11511891B2 FIGS. 4–8.
2. **No net thrust:** All 2D forces in N/m; whole apparatus balances to 0 N/m. No anomalous propulsion claim.
3. **No physical scalar electrodynamics:** Mathematical wave model only; Moscovium preset is severely under-resolved on coarse grids and remains a WHAT-IF parameter.

