# P1 R2 Independent Scientific Re-Review — Fix Queue & Resolution Plan

**Source Review:** [PR #10 review 5573216899](https://github.com/aguacatero/scalar-wave-viz/pull/10#pullrequestreview-5573216899)  
**Reviewed Commit:** `14d58442a18b52b20dadde520c78a51df14d6105`  
**Review Disposition:** REVISE (NOT ACCEPTED) — PR #10 remains DRAFT.

---

## 1. Findings Catalog & Requirements

### P1-R2-F1 (HIGH) — False-positive outgoing-wave tail in sponge reflection benchmark (R1-F2 not closed)
- **Problem:** Splitting one probe trace at fixed step 25 without an unreflected reference measured outgoing pulse content, not sponge reflection. The metric was identical across $\sigma_\text{max} \in [0.0, 0.2, 3.0, 10.0]$ because the peak was the outgoing tail at step 25.
- **Required:**
  1. Implement matched reference simulation (enlarged domain or no-return boundary) with identical source, mesh, and time stepping.
  2. Isolate reflected wave via reference subtraction: $\phi_\text{refl}(t) = \phi_\text{test}(t) - \phi_\text{ref}(t)$.
  3. Include negative controls ($\sigma_\text{max}=0$, undamped Dirichlet wall producing large reflection) and positive controls ($\sigma_\text{max}=3.0$).
  4. Rename legacy fixed-window calculation to `fixed_window_late_early_probe_amplitude_proxy`.
  5. Remove misleading "R_power < 5%" and ">95% absorbed" claims from notebook UI and code documentation.

### P1-R2-F2 (HIGH) — Force convergence acceptance checks only left electrode (R1-F3 partial)
- **Problem:** `force_mesh_convergence_study` checked convergence only for `left_electrode_fx`, ignoring right electrode, enclosure reaction, and net residual. Tests only evaluated symmetric $\pm 500\text{ V}$ where enclosure reaction is zero by symmetry. No virtual-work or traction cross-check.
- **Required:**
  1. Refactor mesh convergence to track and assess all components: $F_{\text{left}, x}, F_{\text{left}, y}, F_{\text{right}, x}, F_{\text{right}, y}, F_{\text{box}, x}, F_{\text{box}, y}$, and net residual across $\ge 3$ mesh levels ($n \in [41, 81, 161]$).
  2. Test asymmetric $+600\text{ V} / +100\text{ V}$ configuration across mesh levels, demonstrating convergence of the non-zero enclosure reaction.
  3. Implement independent virtual-work / perturbation-of-energy force cross-check ($F_x = +(\partial U / \partial x)_V$ at constant potentials) and compare with Maxwell stress tensor integral.

### P1-R2-F3 (MED) — Asymmetric force-balance regression tolerances weaker than signal
- **Problem:** `test_asymmetric_voltage_geometry_produces_nonzero_enclosure_reaction` used tolerance $2 \times 10^{-4}\text{ N/m}$, larger than net electrode force ($\sim 1.35 \times 10^{-4}\text{ N/m}$), and `places=4` permitted $37\%$ error.
- **Required:**
  1. Regression-test tight bound on actual vector residual ($< 1 \times 10^{-7}\text{ N/m}$ on $n=81$, matching observed $\sim 3 \times 10^{-8}\text{ N/m}$).
  2. Verify relative residual $|F_\text{residual}| / |F_\text{elec}| < 0.1\%$ ($10^{-3}$).

### P1-R2-F4 (MED) — Sampled continuum energy diagnostic vs exact discrete leapfrog invariant
- **Problem:** Staggered half-time velocity alongside same-level central differences has $O(\Delta t^2 + \Delta x^2)$ truncation errors and drifts on high-frequency modes.
- **Required:**
  1. Label pointwise gradient functional as `compute_sampled_continuum_energy_diagnostic` and document truncation error.
  2. Derive and implement exact discrete leapfrog Hamiltonian invariant $\mathcal{H}^{n+1/2} = \frac{1}{2} \sum \frac{1}{c^2} (v^{n+1/2})^2 \Delta x^3 + \frac{1}{2} \langle \phi^{n+1}, -L \phi^n \rangle \Delta x^3$, conserving energy to machine precision in undamped media.
  3. Add regression tests for exact discrete conservation on eigenmodes and two-material interfaces.

### P1-R2-F5 (MED) — Production harmonic source normalization and time-step independence
- **Problem:** Direct additive injection `phi[source] += sin(omega * t)` lacks $\Delta t^2$ factor, making effective source strength dependent on $\Delta t$. Wave tests checked only 8 steps without frequency/refinement verification.
- **Required:**
  1. Discretize consistently: provide normalized prescribed Dirichlet emitter and normalized additive source with $\Delta t^2$ scaling.
  2. Verify time-step independence across grid refinements ($\Delta t$ vs $\Delta t / 2$) for fixed physical duration.
  3. Benchmark wave pulse transmission and reflection at two-medium step interface against analytical Fresnel coefficients.

### P1-R2-F6 (LOW) — Manifest parameter completeness and UI scientific neutrality
- **Problem:** Benchmark parameters omitted from manifest case dictionary. Notebook header claimed "Physical ... absorbing boundaries (R < 5%)". Material description for bismuth claimed empirical wave refraction.
- **Required:**
  1. Serialize all benchmark inputs, grid parameters, and control data into manifest.
  2. Tone down UI and notebook text: identify toy scalar wave model, mathematical damping layer, and stipulated wave speeds (WHAT-IF parameters).
