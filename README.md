# Scalar Wave Viz — hypothesis-driven physics visualizations

**Status: educational and exploratory. This project has not demonstrated anomalous propulsion, a physical exotic scalar wave, or special moscovium field properties.**

The goal is to help people understand what **specified physical theories predict**, what is assumed, what is measured, and which experimental observations could discriminate between explanations.

## Research progress

![Scientific roadmap: P0 accepted, P1 through P4 pending; 1 of 5 review gates accepted](assets/research-progress.svg)

**P0 — ACCEPTED (independent R8 review, [PR #5](https://github.com/aguacatero/scalar-wave-viz/pull/5)).** The conventional electrostatics scientific baseline passed its scoped acceptance gate. **Next:** [P1 numerical validation and whole-apparatus force accounting](https://github.com/aguacatero/scalar-wave-viz/issues/6), followed by [P2 source-bound patent-geometry reproduction](https://github.com/aguacatero/scalar-wave-viz/issues/7). This bar tracks review milestones, **not** physical validity, anomalous propulsion, or experimental confirmation.

## First reproducible conventional-electrostatics baseline

This new code deliberately separates an **analytic ideal parallel-plate benchmark** from a **2D field calculation for cylindrical electrodes inside a grounded outer enclosure**. The examples do **not** reproduce a particular Exodus patent embodiment, do not calculate device thrust and do not show any anomalous propulsion.

Run from repository root:

    python -m pip install -r requirements.txt
    python -m unittest discover -s tests -v
    python examples/electrostatics_demo.py

The exported electrostatics_baseline.png displays (A) potential in V, (B) electric field in kV/m, and (C) signed local opposing forces in µN for a **separate ideal parallel-plate case**. In that ideal case net pair force is **0 N**. The grounded box in the 2D example is an **external conductor**; it does not approximate an isolated device with free-space boundaries.

Read: [Scientific charter](docs/SCIENCE_CHARTER.md) · [Exodus comparison contract](docs/EXODUS_MODEL_CONTRACT.md) · [Roadmap](docs/ROADMAP.md).


### Preview without opening Jupyter

Open the latest successful [Physics baseline tests workflow](https://github.com/aguacatero/scalar-wave-viz/actions/workflows/physics-tests.yml), then download the artifact named **conventional-electrostatics-preview**. The file `electrostatics_baseline.png` contains three labeled panels, and it is **not** a measurement or a patent-specific thrust prediction. GitHub retains the generated CI artifact for 30 days.

## Existing notebooks — illustrative, not experimentally verified

- [wave_3d.ipynb](wave_3d.ipynb): a 3D *mathematical* scalar wave simulation, with user-selected relative material wave speeds Air=1, Bismuth=0.55, Moscovium=0.15, metamaterial=0.04. **These values are hypothetical presets**, not established material responses. Important numerical resolution/boundary issues remain.
- [mc_stability.ipynb](mc_stability.ipynb): exploratory nuclear stability and synthesis charts. Hypothetical Mc-291–299 half-lives and the isotope-mass-to-wave-speed interpolation are **not derived by the software** from measured data or validated model predictions.
- [wave_demo.ipynb](wave_demo.ipynb): educational wave examples; one saved output contains a Matplotlib error.

[Legacy Binder demo](https://mybinder.org/v2/gh/aguacatero/scalar-wave-viz/HEAD?filepath=wave_3d.ipynb) (compatibility and physics not validated).

## Research direction

The [Exodus patents](https://ept.space/patents/) describe proposed forces from asymmetric electrostatic pressure; they do **not** establish the scalar material model above. Next, independently select and reproduce a fully specified patent geometry and compare conventional Maxwell-stress accounting with the explicitly cited patent model and experimental evidence, including external couplings and null controls.

All PRs changing physics must disclose equations, sources, units, boundaries, assumptions, benchmarks and uncertainty. Null results are successful scientific information.
