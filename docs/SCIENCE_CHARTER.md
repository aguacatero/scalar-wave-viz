# Scientific charter — Scalar Wave Viz

Status: research and engineering contract (2026-10-13).

## Purpose and epistemic labels

Show what a clearly specified theory predicts, which parameters are assumptions, what has been measured, and how a proposed effect could be falsified. This repository has **not demonstrated scalar electromagnetic propulsion, anomalous thrust, stable moscovium or modified gravity**.

Every graph must distinguish:

- **ESTABLISHED MODEL** — numerical solution to accepted equations, not itself an experiment.
- **PUBLISHED HYPOTHESIS** — a published, cited mathematical claim awaiting independent validation.
- **WHAT-IF PARAMETER** — an assumed coefficient used for exploration, not measured material response.
- **EXPERIMENTAL MEASUREMENT** — sourced apparatus/data/units with uncertainty and control conditions.
- **UNVERIFIED NUMERICAL OUTPUT** — not yet adequately benchmarked or converged.

Supply units, model boundaries, equation, parameter provenance, uncertainties, source revision, and distinguish measurements from simulations.

## Current notebooks: corrected interpretation

- wave_3d.ipynb solves a **mathematical scalar wave** equation with hardcoded relative speeds 1.00, 0.55, 0.15, 0.04. These are WHAT-IF coefficients, **not measured scalar propagation in Bismuth, Moscovium, or an exotic metamaterial**. Its scalar variable is not validated as physical pressure, electromagnetic potential, or gravity.
- With source angular frequency 2π×0.05 per numerical step and dt ≈ 0.502, the idealized wavelengths are approximately 10, 5.5, 1.5 and 0.4 cells respectively. The latter two are under-resolved; no reliable trapping inference follows. Multiplicative boundary damping is not formal PML, and the source lies inside the damping region.
- mc_stability.ipynb hardcodes nuclear half-lives and extrapolates hypothetical mass-number-to-wave-speed interpolation; it **does not compute those properties from published nuclear theory**. Increased nuclear lifetime does not imply extraordinary field interactions.
- wave_demo.ipynb contains introductory demonstrations; one cell retains a Matplotlib callback error.

## What the first baseline establishes

electrostatics_baseline.py implements (a) **separate ideal parallel-plate analytic reference**, with opposing plate forces and zero net force for the pair; and (b) 2D finite-difference Laplace potential and electric field for circular electrode cross-sections inside a **grounded external enclosure**. A fixed-voltage outer box is not empty free space. The solver calculates **no thrust** and is **not an Exodus geometry**. The three-panel figure juxtaposes two different calculations with separate labels.

## Required scientific gates

1. Analytic reference test, independent cross-check, grid convergence, boundary sensitivity.
2. Complete force accounting for electrodes, supports, power supplies, enclosure and environment.
3. Explicit rival hypotheses and controls, detection limits and testable observables.
4. Published experimental sources identified by dataset, uncertainty and apparatus.
5. No anomalous force term simply assumed to generate an exciting result.
6. Each figure reproducible from saved source revision and parameters.
7. Patent issuance is not proof of the patent's physical claims.

## Non-goals

Do not infer a real exotic scalar mode from mathematical scalar notation; infer propagation changes from atomic mass alone; or infer net thrust from colorful electrostatic pressure maps.
