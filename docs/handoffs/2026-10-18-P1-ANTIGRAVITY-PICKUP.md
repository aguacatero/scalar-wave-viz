# P1 — Antigravity / Hermes implementation pickup and independent review contract

**STATE: READY FOR CHATGPT INDEPENDENT RE-REVIEW — P1 R2. PR #10 REMAINS DRAFT; DO NOT MERGE.**

- Repository: https://github.com/aguacatero/scalar-wave-viz
- Tracker: [Issue #6](https://github.com/aguacatero/scalar-wave-viz/issues/6)
- Branch: `p1-numerics-force-accounting-2026-10-18`; base: `main`
- **Current draft PR: [#10](https://github.com/aguacatero/scalar-wave-viz/pull/10)** — P1-A, P1-B, P1-C, and P1-D fully implemented and tested with 56 passing unit tests (0 failures, 0 errors).
- P0 merged [PR #5](https://github.com/aguacatero/scalar-wave-viz/pull/5) as merge commit `174c6b895a0c2ec416b6d46ab9e0835b14a8cb49` on 2026-10-18 (Pacific)
- Independently accepted P0 implementation code SHA: `57067164b47d7d374a1d7bb1c8ce00bb79aa07f8` — preserved byte-for-byte in `electrostatics_baseline.py`.
- Next milestone: P1 **only**. P2 patent FIGS. 4–8 model is reserved for [Issue #7](https://github.com/aguacatero/scalar-wave-viz/issues/7) after P1's independent acceptance.
- Scheduler status: `PICKUP: MANUAL-ONLY` (no active background cron/poller verified).
- Fix ledger: `docs/handoffs/2026-10-19-P1-CHATGPT-R1-FIX-QUEUE.md` tracking all findings from review [`pullrequestreview-5571628683`](https://github.com/aguacatero/scalar-wave-viz/pull/10#pullrequestreview-5571628683).

---

## 1. Implemented Scope & P1 R1 Finding Resolutions

### P1-A: Electrostatic Numerical Convergence & Enclosure Sensitivity (`electrostatics_numerics.py`)
1. **Analytic Harmonic Polynomial Benchmark (`harmonic_polynomial_benchmark`):**
   - Exact potential: $V(x, y) = V_0 (x^3 - 3xy^2) / L^3$. Continuous Laplacian $\nabla^2 V = 0$.
   - 5-point discrete Laplacian has zero truncation error on polynomials of degree $\le 3$.
   - Potential error is zero to machine precision ($\le 1.85 \times 10^{-13}\text{ V} < 10^{-10}\text{ V}$) across all grid resolutions ($n=21, 41, 81, 161$).
   - Central difference gradient has exact analytic truncation error $(V_0 / L^3) h^2$ in $E_x$ and zero error ($< 10^{-9}\text{ V/m}$) in $E_y$.
2. **Smooth Harmonic Transcendental Benchmark (`harmonic_trig_benchmark`):**
   - Exact potential: $V(x, y) = V_0 \sinh(\pi x / W) \sin(\pi y / W) / \sinh(\pi / 2)$.
   - Demonstrates second-order asymptotic convergence rates across $n \in [21, 41, 81, 161]$:
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
2. **Whole-Apparatus Force Balance & Non-trivial Enclosure Reaction (P1-R1-F3):**
   - Evaluates Maxwell stress on left electrode, right electrode, and inner perimeter of grounded enclosure.
   - Evaluated on asymmetric voltage configuration ($V_\text{left}=+600\text{ V}, V_\text{right}=+100\text{ V}$):
     - Net electrode force is non-zero: $F'_\text{elec} = -1.348 \times 10^{-4}\text{ N/m} \ne 0$.
     - Grounded enclosure reaction force is demonstrably non-zero: $F'_\text{box} = +1.348 \times 10^{-4}\text{ N/m} \ne 0$.
     - Full system balances to $< 3 \times 10^{-8}\text{ N/m}$ residual without algebraic cancellation.
   - Grid refinement study (`force_mesh_convergence_study`) on $n \in [41, 81, 161]$ confirms individual electrode and box forces converge monotonically with $< 5\%$ relative change and explicit uncertainty budget ($< 5 \times 10^{-4}\text{ N/m}$).
   - Path independence (`contour_invariance_study`): Concentric contours enclosing the same electrode vary by $< 1\%$, demonstrating discrete Gauss/divergence invariance.
   - Explicitly documents that electrode forces comprise both mutual inter-electrode interaction and grounded-wall image force coupling.

### P1-C: 3D Mathematical Scalar Wave Numerics Repairs (`scalar_wave_3d.py`, `wave_3d.ipynb`)
1. **Production Runner & Notebook Integration (P1-R1-F1):**
   - Connected `wave_3d.ipynb` directly to validated production runner `run_3d_simulation`.
   - Purged periodic wrapping (`np.roll`), multiplicative damping (`*= pml`), and integer-step sine injection from `wave_3d.ipynb`.
   - Updated notebook UI to dynamically display epistemic tags and under-resolution warnings for exotic presets.
   - Added end-to-end regression test `test_notebook_and_runner_end_to_end`.
2. **Direct Reflection Measurement & Smooth Interior Energy (P1-R1-F2):**
   - Formulated discrete energy density across unmasked domain first; integrates local energy density over interior volume without step-edge artifacts ($E_\text{interior} \le E_\text{total}$ strictly guaranteed).
   - Measured reflection coefficient via probe time series (`benchmark_sponge_reflection_probe`), yielding $R_\text{pwr} \approx 3.2\% < 5\%$ power reflection.
   - Retained legacy proxy calculation for audit/reproducibility comparison, confirming reviewer's finding of artificial jump energy.
3. **Conserved Hamiltonian for Non-Divergence Wave Equation (P1-R1-F4):**
   - Derived continuum conserved functional for $\phi_{tt} = c(\mathbf{x})^2 \nabla^2\phi$:
     $\mathcal{H}(\mathbf{x}) = \frac{1}{2} (\phi_t / c)^2 + \frac{1}{2} |\nabla\phi|^2$.
   - Labeled energy in arbitrary energy units (not uncalibrated Joules).
   - Benchmarked two-material undamped wave energy conservation (`benchmark_two_material_energy_conservation`) across $c_1=1.0 \to c_2=0.6$ interface, verifying $< 6\%$ drift during transit.
4. **CFL Stability Enforcement in Stepper API (P1-R1-F5):**
   - Enforced $c_\text{max} \Delta t / \Delta x \le 1 / \sqrt{3}$ directly inside `step_wave_fdtd`.
   - Validates positive/finite parameters and matching field shapes; fails closed on violations.
   - Added explicit unit tests for CFL and input validation.
5. **Spatial Resolution Audit:**
   - Air ($c=1.0$): $N_\lambda = 20.0 \ge 10 \implies$ `ADEQUATELY_RESOLVED` (`ESTABLISHED_MODEL`).
   - Bismuth ($c=0.55$): $N_\lambda = 11.0 \ge 10 \implies$ `ADEQUATELY_RESOLVED` (`WHAT-IF_PARAM`).
   - Moscovium ($c=0.15$): $N_\lambda = 3.0 < 10 \implies$ `NUMERICALLY_UNDER_RESOLVED` (`WHAT-IF_PARAM (UNVERIFIED)`).
   - Metamaterial ($c=0.04$): $N_\lambda = 0.8 < 1.0 \implies$ `NUMERICALLY_UNDER_RESOLVED` (`WHAT-IF_PARAM (UNVERIFIED)`).

### P1-D: Comprehensive Evidence Manifest (P1-R1-F6, `examples/electrostatics_demo.py`)
- Serializes complete 4-level trig convergence table ($n \in [21, 41, 81, 161]$).
- Serializes all 3D wave benchmark metrics (pulse propagation error %, probe reflection coefficient, two-material energy drift %, CFL standards).
- Serializes force mesh convergence study, contour invariance study, and asymmetric box reaction.
- Strict RFC 8259 compliance and git provenance preservation.

---

## 2. Test Suite & Evidence
- **Total unit tests:** **56 passed** (0 failures, 0 errors).
  - 35 baseline regression tests in `tests/test_electrostatics_baseline.py` (all green).
  - 10 P1 electrostatic numerics & Maxwell stress tests in `tests/test_p1_numerics.py` (all green).
  - 11 P1 3D scalar wave numerics & benchmark tests in `tests/test_p1_wave_3d.py` (all green).
- Local execution: `python3 -m unittest discover -s tests -v` (56 tests in ~76s).
- Demo and manifest execution: `MPLBACKEND=Agg python3 examples/electrostatics_demo.py` generates valid PNG and RFC 8259 compliant manifest.

---

## 3. Explicit Non-Claims
1. **No patent geometry reproduction:** Idealized cylindrical electrode disks in a grounded box; does not reproduce Exodus patent US11511891B2 FIGS. 4–8.
2. **No net thrust:** All 2D forces in N/m; whole apparatus balances to 0 N/m. No anomalous propulsion claim.
3. **No physical scalar electrodynamics:** Mathematical wave model only; Moscovium preset is severely under-resolved on coarse grids and remains a WHAT-IF parameter.
