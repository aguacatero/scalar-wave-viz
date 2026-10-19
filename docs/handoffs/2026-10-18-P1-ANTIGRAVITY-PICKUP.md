# P1 — Antigravity / Hermes implementation pickup and independent review contract

**STATE: READY FOR CHATGPT INDEPENDENT REVIEW — P1 R1. PR #10 REMAINS DRAFT; DO NOT MERGE.**

- Repository: https://github.com/aguacatero/scalar-wave-viz
- Tracker: [Issue #6](https://github.com/aguacatero/scalar-wave-viz/issues/6)
- Branch: `p1-numerics-force-accounting-2026-10-18`; base: `main`
- **Current draft PR: [#10](https://github.com/aguacatero/scalar-wave-viz/pull/10)** — P1-A, P1-B, P1-C, and P1-D fully implemented and tested with 48 passing unit tests.
- P0 merged [PR #5](https://github.com/aguacatero/scalar-wave-viz/pull/5) as merge commit `174c6b895a0c2ec416b6d46ab9e0835b14a8cb49` on 2026-10-18 (Pacific)
- Independently accepted P0 implementation code SHA: `57067164b47d7d374a1d7bb1c8ce00bb79aa07f8` — preserved byte-for-byte in `electrostatics_baseline.py`.
- Next milestone: P1 **only**. P2 patent FIGS. 4–8 model is reserved for [Issue #7](https://github.com/aguacatero/scalar-wave-viz/issues/7) after P1's independent acceptance.
- Scheduler status: `PICKUP: MANUAL-ONLY` (no active background cron/poller verified).

---

## 1. Implemented Scope (P1-A, P1-B, P1-C, P1-D)

### P1-A: Electrostatic Numerical Convergence & Enclosure Sensitivity (`electrostatics_numerics.py`)
1. **Analytic Harmonic Polynomial Benchmark (`harmonic_polynomial_benchmark`):**
   - Exact potential: $V(x, y) = V_0 (x^3 - 3xy^2) / L^3$. Continuous Laplacian $\nabla^2 V = 0$.
   - 5-point discrete Laplacian has zero truncation error on polynomials of degree $\le 3$.
   - Potential error is zero to machine precision ($\le 1.85 \times 10^{-13}\text{ V} < 10^{-10}\text{ V}$) across all grid resolutions ($n=21, 41, 81$).
   - Central difference gradient has exact analytic truncation error $(V_0 / L^3) h^2$ in $E_x$ and zero error ($< 10^{-9}\text{ V/m}$) in $E_y$.
2. **Smooth Harmonic Transcendental Benchmark (`harmonic_trig_benchmark`):**
   - Exact potential: $V(x, y) = V_0 \sinh(\pi x / W) \sin(\pi y / W) / \sinh(\pi / 2)$.
   - Demonstrates rigorous second-order asymptotic convergence rates across $n \in [21, 41, 81, 161]$:
     - Potential convergence rate: $p_\text{pot} = 1.97 \to 1.998 \to 1.999 \approx 2.00$.
     - Field convergence rate: $p_\text{field} = 1.89 \to 1.92 \to 1.95 \approx 2.00$.
3. **Enclosure Size Sensitivity Sweep (`enclosure_size_sensitivity_study`):**
   - Sweeps grounded outer box width $W \in [0.03, 0.04, 0.06, 0.08]\text{ m}$ at fixed physical resolution $h \approx 0.5\text{ mm}$.
   - Demonstrates that peak electric field on the grounded outer enclosure drops monotonically from $100.6\text{ kV/m}$ to $7.19\text{ kV/m}$ as the box expands.
   - Proves the grounded box is an active boundary condition, not open space.

### P1-B: Maxwell Stress Closed-Contour Integration & Force Balance (`electrostatics_numerics.py`)
1. **Vacuum Closed-Contour Stress Integration (`compute_maxwell_stress_contour`):**
   - $T_{ij} = \varepsilon_0 (E_i E_j - \frac{1}{2} |E|^2 \delta_{ij})$.
   - All integrated forces in 2D are strictly force per unit depth (**N/m**), never Newtons or 3D thrust.
   - Empty vacuum loop around origin integrates to zero force ($< 10^{-10}\text{ N/m}$).
   - Validates that non-vacuum contour penetration raises `ValueError` in strict mode.
2. **Whole-Apparatus Force Bookkeeping (`evaluate_whole_apparatus_force_budget`):**
   - Integrates Maxwell stress around left electrode, right electrode, and inner perimeter of grounded enclosure.
   - Symmetric electrode pair experiences equal and opposite mutual attraction ($F'_\text{left} = +3.68 \times 10^{-3}\text{ N/m}$, $F'_\text{right} = -3.68 \times 10^{-3}\text{ N/m}$).
   - Grounded enclosure reaction force balances the field traction: $F'_\text{left} + F'_\text{right} + F'_\text{enclosure} \approx 0\text{ N/m}$.
   - Discloses missing mechanical reactions: rigid standoffs and feedthroughs exert equal-and-opposite mechanical reaction forces holding the electrodes in place; net mechanical force on the isolated system is strictly zero.

### P1-C: 3D Mathematical Scalar Wave Numerics Repairs (`scalar_wave_3d.py`)
1. **Source Relocation:**
   - Moved point source strictly outside the boundary sponge damping layer ($x_\text{source} > w_\text{sponge}$).
   - Rejects configuration if source is inside sponge layer.
2. **Physical Absorbing Sponge Boundary:**
   - Formulated quadratic damping conductivity layer: $\sigma(d) = \sigma_0 (d / w_\text{sponge})^2$.
   - Symmetrically discretized damped wave equation avoiding heuristic roll/multiplication artifacts.
3. **CFL Stability & Grid-Points-Per-Wavelength Audit:**
   - Enforces 3D Courant condition $c_\text{max} \Delta t / \Delta x \le 1 / \sqrt{3}$.
   - Audits spatial resolution $N_\lambda = \lambda / \Delta x$:
     - Air ($c=1.0$): $N_\lambda = 20.0 \ge 10 \implies$ `ADEQUATELY_RESOLVED` (`ESTABLISHED_MODEL`).
     - Bismuth ($c=0.55$): $N_\lambda = 11.0 \ge 10 \implies$ `ADEQUATELY_RESOLVED` (`WHAT-IF_PARAM`).
     - Element 115 / Moscovium ($c=0.15$): $N_\lambda = 3.0 < 10 \implies$ `NUMERICALLY_UNDER_RESOLVED` (`WHAT-IF_PARAM (UNVERIFIED)`). Flags that extreme wave slowing causes severe numerical dispersion and grid pinning.
     - Exotic metamaterial ($c=0.04$): $N_\lambda = 0.8 < 1.0 \implies$ `NUMERICALLY_UNDER_RESOLVED` (`WHAT-IF_PARAM (UNVERIFIED)`).
4. **Benchmarks:**
   - Pulse propagation velocity: centroid tracks physical speed $c$ within $3.4\%$ (consistent with theoretical FDTD dispersion).
   - Boundary sponge absorption: absorbs $> 98\%$ of spherical wave energy, with remaining interior energy ratio $< 2\%$.
   - Discrete energy conservation: field Hamiltonian is conserved to $< 5\%$ over 15 steps in undamped medium prior to boundary arrival.

### P1-D: Reproducibility & Scientific UI (`examples/electrostatics_demo.py`)
- Serializes P1 Maxwell stress force budget, analytic convergence benchmarks, and 3D wave numerics audits directly into `electrostatics_manifest.json` (schema 1.2.0 compliant).
- Preserves full provenance (`pr_source_head_sha`, `tested_checkout_sha`, `pr_base_sha`, git commit).

---

## 2. Test Suite & Evidence

- **Total unit tests:** **48 passed** (0 failures, 0 errors).
  - 35 baseline regression tests in `tests/test_electrostatics_baseline.py` (all green).
  - 7 P1 electrostatic numerics & Maxwell stress tests in `tests/test_p1_numerics.py` (all green).
  - 6 P1 3D scalar wave numerics & benchmark tests in `tests/test_p1_wave_3d.py` (all green).
- Local execution: `python3 -m unittest discover -s tests -v` (48 tests in ~21s).
- Demo and manifest execution: `MPLBACKEND=Agg python3 examples/electrostatics_demo.py` generates valid PNG and RFC 8259 compliant manifest.

---

## 3. Explicit Non-Claims

1. **No patent geometry reproduction:** Modeled electrode cross-sections are idealized cylindrical disks in a grounded box; they do not reproduce Exodus patent US11511891B2 FIGS. 4–8.
2. **No anomalous thrust:** All 2D forces are force per unit depth (**N/m**). The modeled electrode-enclosure system strictly balances to 0 N/m. No net mechanical propulsion is established.
3. **No physical scalar electrodynamics:** 3D wave solver is a mathematical scalar toy model; Element 115 / Moscovium preset is severely under-resolved on coarse grids and remains an unverified "WHAT-IF" parameter.

---

## 4. Reviewer Acceptance Checklist (P1 R1)

- [x] All 35 existing P0 regression tests green and 13 new P1 independent cross-checks green (48 total).
- [x] Explicit analytic harmonic polynomial ($< 10^{-10}\text{ V}$) and sine/sinh ($O(h^2)$ rate) benchmarks implemented.
- [x] Enclosure sensitivity sweep demonstrates boundary field drop as $W$ expands.
- [x] Vacuum Maxwell stress closed-contour integration evaluates forces in N/m and balances whole-system reactions ($F'_\text{left} + F'_\text{right} + F'_\text{enclosure} \approx 0$).
- [x] 3D wave solver relocates source outside sponge layer, enforces CFL stability, audits points-per-wavelength, and benchmarks pulse propagation and boundary absorption.
- [x] Manifest provenance and strict RFC 8259 JSON serialization verified.
