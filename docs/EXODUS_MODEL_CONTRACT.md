# Exodus patent comparison — source-bound research specification

**Status: not yet an implemented patent reproduction.**

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

Integrate stress over closed surfaces around each object and a surface enclosing the **entire apparatus**. Account for field momentum, supports, grounded boundaries and external connections. Asymmetric internal field pressure alone does not imply acceleration of an isolated system.

## Model H1: precisely cited patent proposition

Before writing a patent force calculator, choose an **exact patent figure/claim/embodiment**, transcribe the equation and assumptions independently, specify dimensions and validate dimensional consistency. Implement its predicted force as **separate theoretical output**, never presupposed true, tuned to a measurement or conflated with H0.

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
