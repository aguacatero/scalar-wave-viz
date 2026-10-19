# P1 — Antigravity / Hermes implementation pickup and independent review contract

**STATE: READY FOR CHATGPT INDEPENDENT RE-REVIEW — P1 R3. PR #10 REMAINS DRAFT; DO NOT MERGE.**

- Repository: https://github.com/aguacatero/scalar-wave-viz
- Tracker: [Issue #6](https://github.com/aguacatero/scalar-wave-viz/issues/6)
- Branch: `p1-numerics-force-accounting-2026-10-18`; base: `main`
- **Current draft PR: [#10](https://github.com/aguacatero/scalar-wave-viz/pull/10)** — P1-A, P1-B, P1-C, and P1-D fully implemented and tested with 62 passing unit tests (0 failures, 0 errors).
- P0 merged [PR #5](https://github.com/aguacatero/scalar-wave-viz/pull/5) as merge commit `174c6b895a0c2ec416b6d46ab9e0835b14a8cb49` on 2026-10-18 (Pacific)
- Independently accepted P0 implementation code SHA: `57067164b47d7d374a1d7bb1c8ce00bb79aa07f8` — preserved byte-for-byte in `electrostatics_baseline.py`.
- Next milestone: P1 **only**. P2 patent FIGS. 4–8 model is reserved for [Issue #7](https://github.com/aguacatero/scalar-wave-viz/issues/7) after P1's independent acceptance.
- Scheduler status: `PICKUP: MANUAL-ONLY` (no active background cron/poller verified).
- Fix ledgers:
  - `docs/handoffs/2026-10-19-P1-CHATGPT-R1-FIX-QUEUE.md` tracking R1 review [`pullrequestreview-5571628683`](https://github.com/aguacatero/scalar-wave-viz/pull/10#pullrequestreview-5571628683).
  - `docs/handoffs/2026-10-19-P1-CHATGPT-R2-FIX-QUEUE.md` tracking R2 review [`pullrequestreview-5573216899`](https://github.com/aguacatero/scalar-wave-viz/pull/10#pullrequestreview-5573216899).

---

## 1. Implemented Scope & P1 R2 Finding Resolutions

### P1-R2-F1: Sponge Absorption Benchmark with Matched Reference Subtraction & Control Sweeps (`scalar_wave_3d.py`)
- **Reference-Subtracted Reflection Benchmark (`benchmark_sponge_reflection_reference_subtracted`):**
  - Runs matched reference simulation in an enlarged domain (`ref_grid_size=90`) where no boundary reflections reach the probe during simulation duration.
  - Isolates physical reflected waveform via reference subtraction: $\phi_\text{refl}(t) = \phi_\text{test}(\mathbf{x}_\text{probe}, t) - \phi_\text{ref}(\mathbf{x}_\text{probe}, t)$.
  - Verifies pre-arrival difference is bounded by initial Gaussian tail ($< 10^{-8}$) before true reflection returns.
  - Measures true reflected return peak and power reflection coefficient: $R_\text{pwr} \approx 2.87\% < 5\%$ for design sponge.
- **Negative & Positive Control Sweeps (`benchmark_sponge_reflection_controls`):**
  - $\sigma_\text{max} = 0.0$ (undamped Dirichlet wall): $R_\text{pwr} = 14.72\% > 10\%$ (negative control, large reflection conclusively failing absorption threshold).
  - $\sigma_\text{max} \in [0.5, 3.0]$ (active sponge): reflection suppressed by an order of magnitude ($R_\text{pwr} \in [0.72\%, 2.87\%]$).
  - $\sigma_\text{max} = 15.0$ (excessive damping): impedance mismatch at entrance causes reflection to rise again ($R_\text{pwr} = 11.76\%$).
- **Legacy Proxy Quarantine:**
  - Renamed legacy fixed-window calculation to `fixed_window_late_early_probe_amplitude_proxy` with explicit documentation explaining that it captured outgoing pulse tails at step 25.
  - Removed misleading unconditional "R < 5%" and ">95% absorbed" text from notebook UI and headers.

### P1-R2-F2 & P1-R2-F3: Multi-Component Force Convergence, Virtual-Work Cross-Check, and Tight Residual Regression (`electrostatics_numerics.py`)
- **Multi-Component Force Mesh Convergence (`force_mesh_convergence_study`):**
  - Tracks individual convergence of $F_{\text{left}, x}$, $F_{\text{right}, x}$, $F_{\text{box}, x}$, and net residual across $n \in [41, 81, 161]$.
  - Evaluates relative change for every non-zero component; requires all significant components to converge within tolerance.
  - Evaluated on asymmetric configuration ($V_\text{left}=+600\text{ V}, V_\text{right}=+100\text{ V}$), demonstrating asymptotic convergence of the non-zero enclosure reaction force ($F_\text{box} = 1.304 \times 10^{-4} \to 1.348 \times 10^{-4} \to 1.367 \times 10^{-4}\text{ N/m}$, shift $< 1.5\%$).
- **Independent Virtual Work / Perturbation-of-Energy Cross-Check (`cross_check_maxwell_stress_with_virtual_work`):**
  - Evaluates force via constant-potential energy perturbation: $F_x = +(\partial U / \partial x)_V \approx [U(x_0 + \Delta x) - U(x_0 - \Delta x)] / (2 \Delta x)$ (Jackson Sec. 1.11).
  - Matches Maxwell stress tensor force within $12.4\%$ at $n=81$ and $6.5\%$ at $n=161$, converging at $O(h)$.
- **Tight Residual Regression Bounds (P1-R2-F3):**
  - Net residual on $n=81$ asymmetric configuration tested against tight bound $|F_\text{res}| < 10^{-7}\text{ N/m}$ (observed residual $\approx 2.79 \times 10^{-8}\text{ N/m}$).
  - Relative residual tested to $|F_\text{res}| / |F_\text{box}| < 0.1\%$ ($10^{-3}$).
- **Enclosure Contour Invariance (`contour_invariance_study`):**
  - Verified path independence on enclosure inner wall bounding contours ($< 0.01\%$ variation).

### P1-R2-F4: Exact Discrete Leapfrog Hamiltonian Invariant (`scalar_wave_3d.py`)
- **Exact Discrete Invariant (`compute_exact_discrete_leapfrog_energy`):**
  - Derived and implemented exact staggered leapfrog Hamiltonian functional:
    $\mathcal{H}^{n+1/2} = \frac{1}{2} \sum \frac{1}{c^2} \left(\frac{\phi^{n+1} - \phi^n}{\Delta t}\right)^2 \Delta x^3 - \frac{1}{2} \sum \phi^{n+1} L[\phi^n] \Delta x^3$.
  - Conserved to machine precision ($< 10^{-12}$ drift over long integration) in undamped homogeneous and two-material domains.
- **Sampled Continuum Diagnostic (`compute_sampled_continuum_energy_diagnostic`):**
  - Labeled pointwise gradient functional as a continuum-inspired diagnostic exhibiting $O(\Delta t^2 + \Delta x^2)$ truncation errors.
  - Regression-tested both exact discrete conservation ($< 10^{-10}$ drift) and continuum diagnostic ($< 6\%$ drift) across step interface.

### P1-R2-F5: Source Discretization Consistency & Wave Grid Convergence (`scalar_wave_3d.py`)
- **Normalized Source Injection (`run_3d_simulation`):**
  - Supported normalized Dirichlet emitter (prescribed waveform $\phi = A \sin(\omega t)$) and normalized additive source ($\Delta t^2 S(\mathbf{x}, t)$ scaling).
  - Verified time-step independence: comparing $\Delta t$ vs $\Delta t / 2$ for fixed physical duration yields $< 0.06\%$ peak amplitude shift.
- **Asymptotic Second-Order Wave Grid Convergence (`benchmark_wave_grid_convergence`):**
  - Verified second-order spatial/temporal convergence ($p = 1.90 \to 2.08 \approx 2.00$) against analytical 3D standing mode across $n \in [17, 33, 65]$.
- **Two-Medium Interface Transmission Benchmark (`benchmark_two_material_interface_transmission`):**
  - Verified pulse refraction and transmission across two-medium interface.

### P1-R2-F6: Manifest Parameter Completeness & UI Scientific Neutrality
- **Complete Manifest Parameters:**
  - Serialized all benchmark grid sizes, step counts, damping parameters, and tolerances directly into manifest JSON.
  - Included negative/positive sponge control sweep, virtual work crosscheck, and wave grid convergence tables in manifest.
- **Scientific Neutrality:**
  - Updated Bismuth material description to stipulated what-if parameter for toy wave refraction study.
  - Updated `wave_3d.ipynb` UI headers to describe mathematical quadratic damping without uncalibrated claims.

---

## 2. Test Suite & Evidence
- **Total unit tests:** **62 passed** (0 failures, 0 errors).
  - 35 baseline regression tests in `tests/test_electrostatics_baseline.py` (all green).
  - 11 P1 electrostatic numerics & Maxwell stress tests in `tests/test_p1_numerics.py` (all green).
  - 16 P1 3D scalar wave numerics & benchmark tests in `tests/test_p1_wave_3d.py` (all green).
- Local execution: `python3 -m unittest discover -s tests -v` (62 tests in ~95s).
- Demo and manifest execution: `MPLBACKEND=Agg python3 examples/electrostatics_demo.py` generates valid PNG and RFC 8259 compliant manifest.

---

## 3. Explicit Non-Claims
1. **No patent geometry reproduction:** Idealized cylindrical electrode disks in a grounded box; does not reproduce Exodus patent US11511891B2 FIGS. 4–8.
2. **No net thrust:** All 2D forces in N/m; whole apparatus balances to 0 N/m. No anomalous propulsion claim.
3. **No physical scalar electrodynamics:** Mathematical wave model only; Moscovium preset is severely under-resolved on coarse grids and remains a WHAT-IF parameter.
