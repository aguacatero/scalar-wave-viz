# P1 R1 Independent Scientific Review Fix Queue & Ledger

**Reference Review:** [`pullrequestreview-5571628683`](https://github.com/aguacatero/scalar-wave-viz/pull/10#pullrequestreview-5571628683)  
**Submitted at:** 2026-10-19T12:37:18Z  
**PR:** [#10](https://github.com/aguacatero/scalar-wave-viz/pull/10) (DRAFT)  
**Reviewed Baseline SHA:** `da196b432b53c19516576883c573804dddcb7634`  
**Review Disposition:** `REVISE (NOT ACCEPTED)`  

---

## 1. Findings and Resolution Matrix

| Finding ID | Severity / Priority | Summary | Target Module | Resolution Strategy | Regression Test |
|---|---|---|---|---|---|
| **P1-R1-F1** | HIGH / P1 | Legacy 3D simulator (`wave_3d.ipynb`) still runs flawed method (`sx=6` inside sponge, `np.roll` periodic, `*= pml` multiplicative damping, integer step sine). | `wave_3d.ipynb`, `scalar_wave_3d.py` | Connect notebook directly to validated production runner `run_3d_simulation`; update UI with epistemic labels and resolution warnings; eliminate periodic roll and multiplicative damping. | `test_notebook_and_runner_end_to_end` |
| **P1-R1-F2** | HIGH / P1 | Masked 'interior energy' zeroes $\phi$ before gradient computation, creating artificial mask-edge gradient energy ($E_\text{int} > E_\text{total}$). Reflection coefficient not physically measured. | `scalar_wave_3d.py` | Compute local energy density across whole domain first without masking $\phi$, then integrate over interior; measure true reflection coefficient via probe time-series against unreflected reference; rename proxy. | `test_sponge_boundary_reflection_probe`, `test_interior_energy_density_no_boundary_jump` |
| **P1-R1-F3** | HIGH / P1 | Whole-apparatus force balance has no nontrivial convergence proof; symmetric $\pm 500\text{ V}$ case forces cancellation; "mutual attraction" label ignores grounded walls. | `electrostatics_numerics.py` | Add asymmetric/off-axis geometry producing demonstrably nonzero enclosure reaction ($F'_\text{box} \ne 0$); perform mesh convergence study on individual forces; verify contour invariance across concentric vacuum contours. | `test_asymmetric_geometry_nonzero_enclosure_reaction`, `test_force_mesh_convergence`, `test_contour_invariance_in_vacuum` |
| **P1-R1-F4** | MED / P2 | Variable-speed wave Hamiltonian inconsistent with evolved non-divergence PDE $\phi_{tt} = c(x)^2 \nabla^2 \phi$; units labeled in unjustified Joules ("J"). | `scalar_wave_3d.py` | Derive and implement consistent discrete continuum functional $\mathcal{H} = \frac{1}{2} \phi_t^2 / c(x)^2 + \frac{1}{2} \vert\nabla\phi\vert^2$; use arbitrary/toy energy units; test two-material undamped long-time conservation. | `test_two_material_undamped_energy_conservation` |
| **P1-R1-F5** | MED / P2 | CFL enforcement only in `WaveGridConfig`, not checked inside `step_wave_fdtd` API. Unstable inputs not rejected. | `scalar_wave_3d.py` | Add strict parameter validation and CFL check `max(c)*dt/dx <= 1/sqrt(3)` inside `step_wave_fdtd`; fail closed on invalid/unstable inputs. | `test_step_wave_fdtd_rejects_cfl_violation_and_invalid_inputs` |
| **P1-R1-F6** | MED / P3 | Evidence manifest underreports central P1 validations (missing $n=161$, missing 3D benchmark numerical values, force convergence); PR description outdated. | `examples/electrostatics_demo.py`, GitHub PR | Include full $n \in [21, 41, 81, 161]$ levels in manifest; record all 3D wave benchmarks and asymmetric force budget; refresh PR description. | `test_manifest_serializes_p1_r2_benchmarks_and_sweeps` |

---

## 2. Mathematical Derivations

### Non-Divergence Wave Equation Conserved Hamiltonian
The wave equation with spatially varying wave speed $c(\mathbf{x})$ in non-divergence form is:
$$\partial_{tt}\phi = c(\mathbf{x})^2 \nabla^2\phi - \sigma(\mathbf{x})\partial_t\phi$$

In the undamped regime ($\sigma = 0$):
$$\frac{1}{c(\mathbf{x})^2} \partial_{tt}\phi = \nabla^2\phi$$

Multiplying both sides by $\partial_t\phi$:
$$\frac{\partial_t\phi}{c(\mathbf{x})^2} \partial_{tt}\phi = \partial_t\phi \nabla^2\phi = \nabla \cdot (\partial_t\phi \nabla\phi) - \nabla(\partial_t\phi) \cdot \nabla\phi$$

Using the identities:
$$\frac{\partial_t\phi \partial_{tt}\phi}{c(\mathbf{x})^2} = \partial_t \left( \frac{1}{2} \frac{(\partial_t\phi)^2}{c(\mathbf{x})^2} \right)$$
$$\nabla(\partial_t\phi) \cdot \nabla\phi = \partial_t \left( \frac{1}{2} |\nabla\phi|^2 \right)$$

We obtain the local continuity relation:
$$\partial_t \left[ \frac{1}{2} \frac{(\partial_t\phi)^2}{c(\mathbf{x})^2} + \frac{1}{2} |\nabla\phi|^2 \right] = \nabla \cdot (\partial_t\phi \nabla\phi)$$

Integrating over a domain $V$ with Dirichlet boundary conditions ($\partial_t\phi = 0$ on $\partial V$):
$$\frac{d}{dt} \int_V \left[ \frac{1}{2} \frac{(\partial_t\phi)^2}{c(\mathbf{x})^2} + \frac{1}{2} |\nabla\phi|^2 \right] dV = 0$$

Therefore, the exact conserved Hamiltonian density is:
$$\mathcal{H}(\mathbf{x}) = \frac{1}{2} \frac{(\partial_t\phi)^2}{c(\mathbf{x})^2} + \frac{1}{2} |\nabla\phi|^2$$

### Whole-Apparatus Force Balance & Nonzero Enclosure Reaction
For an asymmetric configuration with voltages $V_\text{left} \ne V_\text{right}$ or asymmetric electrode positions:
$$F'_\text{left} + F'_\text{right} \ne 0$$
The grounded shielding enclosure carries surface charges induced by the asymmetric internal field, resulting in a net electrostatic force on the box:
$$F'_\text{box} = -\oint_{\partial \text{vacuum}} \mathbf{T} \cdot \mathbf{n}\, dl = -(F'_\text{left} + F'_\text{right})$$
Total force balance across all components:
$$F'_\text{net} = F'_\text{left} + F'_\text{right} + F'_\text{box} = 0$$
This provides a non-trivial, non-canceling validation of momentum conservation and Maxwell stress integration.
