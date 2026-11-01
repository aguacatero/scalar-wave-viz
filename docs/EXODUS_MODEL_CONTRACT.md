# Exodus patent comparison — source-bound research specification

**Status (2026-10-25): Phase P2 active on branch p2-patent-geometry-exodus-2026-10-25 (draft PR pending independent ChatGPT scientific review). Implements source-bound FIGS. 4–8 embodiment, parameter audit, H0 Maxwell-stress momentum accounting, H1 Eq. (11) transcription, and Tajmar & Schreiber (2020) null benchmark.**

## Primary sources

- [US11511891B2](https://patents.google.com/patent/US11511891B2/en) — issued November 2022, asymmetrical electrostatic pressure.
- [US20230121805A1](https://patents.google.com/patent/US20230121805A1/en) — continuation application.
- [US20240011469A1](https://patents.google.com/patent/US20240011469A1/en) — further published application.
- [Official Exodus patent list](https://ept.space/patents/).
- [Tajmar & Schreiber, Journal of Electrostatics 107, 103477 (2020)](https://doi.org/10.1016/j.elstat.2020.103477) — experiments assessing capacitor-thrust claims.

These patents concern electric fields/electrostatic pressure and electrode geometry, not empirically characterized exotic-material scalar-wave-speed coefficients. The claims are **hypotheses requiring independent verification**.

## Model H0: conventional electrodynamics

For homogeneous vacuum electrostatics, Laplace's equation ∇²V=0 holds outside charges and conductors; E = −∇V. Maxwell stress is

Tᵢⱼ = ε₀ (Eᵢ Eⱼ − ½ |E|² δᵢⱼ).

On a flat conductor surface in vacuum, the local electrostatic outward traction is T_n = ½ ε₀ E_n². Integrate stress over closed surfaces around each object and a bounding surface enclosing the **entire apparatus** (electrodes, mounts, wiring, power source, and enclosure). In any static, closed electrostatic system, momentum conservation guarantees that the total Maxwell stress integrated over an external bounding surface vanishes: ∮ T · da = 0. Asymmetric internal field pressure on opposing electrode faces is mechanically balanced by forces on mounts, casing, and external leads/ground unless momentum is transferred to an external medium (e.g. ion emission, radiation) or field momentum changes (d/dt ∫ ε₀(E×B) dV ≠ 0).

## Model H1: precisely cited patent proposition and proof-obligation ledger

Before writing a patent force calculator, choose an **exact patent figure/claim/embodiment**, transcribe the equation and assumptions independently, specify dimensions and validate dimensional consistency. Implement its predicted force as **separate theoretical output**, never presupposed true, tuned to a measurement or conflated with H0.

### Derivation ledger: US11511891B2 (Eq. 4–11 audit)

The mathematical derivation in US11511891B2 relies on specific formal steps that must be treated as unverified proof obligations, not established physics:

1. **Eq. (4) assertion of d(Ut) = 0 from stationary action:**
   - *Patent text:* The patent asserts that total energy variation d(Ut) = 0 follows by analogy with the principle of stationary action δS = 0.
   - *Physical critique:* Stationary action δS = δ ∫ L dt = 0 is a variational principle along a dynamical path over time yielding equations of motion (Euler-Lagrange). It does NOT imply the pointwise identity d(Ut) = 0 across spatial configurations or arbitrary coordinate increments, nor does it justify neglecting battery work (voltage source bookkeeping dW = V dQ) or intermediate reaction forces.
   - *Status:* **Contested derivational assumption / proof obligation**.

2. **Eq. (11) net force expression ε₀ (E₂² A₂ − E₁² A₁):**
   - *Patent text:* The patent infers a net unidirectional force F = ε₀ (E₂² A₂ − E₁² A₁) acting on the capacitor.
   - *Discrepancy with Maxwell stress:* Standard electrostatic surface traction is ½ ε₀ E², carrying an essential factor of ½ that is absent in Eq. (11).
   - *System boundary omission:* Eq. (11) evaluates difference in electrostatic pressure across two electrode faces while omitting:
     (a) Maxwell stress on electrode lateral edges, rear faces, and feedthroughs;
     (b) Reaction stress on mechanical supports, vacuum chamber walls, or surrounding ground conductors;
     (c) Return electric flux in the exterior domain.
   - *Status:* **Unverified hypothesis (H1)**. Patent issuance by the USPTO is an administrative legal grant of novelty, NOT physical or mathematical validation.

### Proof obligations for Phase P2 gate

Resolving these derivational steps is a mandatory gate for Phase P2 (patent reproduction), NOT a completed validation in Phase P0:
- Maintain strict numerical separation between H0 (closed-surface Maxwell stress integration) and H1 (Eq. 11 patent formula).
- Define whole-system momentum balance: F_net = F_electrodes + F_supports + F_enclosure + dP_field/dt.
- Document any non-zero predicted net thrust as an unverified H1 hypothesis requiring experimental control tests.

## Model H2: known systematic effects

Consider corona/ion wind, field coupling to external surfaces, cable and support forces, leakage, trapped charges, vibrations, thermal drift, outgassing, material dielectric effects and instrument errors. Vary pressure, polarity, electrode symmetry, orientation and voltage with predeclared comparisons.

## Acceptance gates for patent-specific PR

1. Source-bound geometry with dimensions, material, electrode potentials and missing specification explicitly recorded.
2. Converged FEM/BEM/finite-difference field model, with proper 2D-versus-3D interpretation.
3. Independently reproduced analytic capacitor test case.
4. Closed-surface Maxwell-stress force accounting for **all** objects and external boundaries.
5. Numerical residuals and sensitivity to mesh, integration contour and boundary distance.
6. Separate citation-bound H1 prediction; **no inferred residual thrust** in the absence of measurements.
7. Experimental data only with traceable apparatus, raw or accessible readings, uncertainty and controls.

## Present limit

The first 2D grounded-box demonstration is **not patent geometry, not an isolated thruster, not a 3D force calculation, not an experimental result, and not evidence for anomalous propulsion**.
