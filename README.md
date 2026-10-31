# Scalar Wave Viz — hypothesis-driven physics visualizations

**Status: educational and exploratory. This project has not demonstrated anomalous propulsion, a physical exotic scalar wave, or special moscovium field properties.**

The goal is to help people understand what **specified physical theories predict**, what is assumed, what is measured, and which experimental observations could discriminate between explanations.

## Research progress

![Scientific roadmap: P0 and P1 scientifically accepted and merged; P2 active; P3 through P4 pending; 2 of 5 review gates accepted](assets/research-progress.svg)

**Scientific milestone progress: 2 of 5 independently accepted (P0 and P1).** This is a count of *scoped scientific review gates*, not an estimate of overall engineering completion, proof of physical validity, anomalous propulsion, or experimental confirmation.

- **P0 — ACCEPTED AND MERGED.** Conventional electrostatics baseline accepted at [R8 on PR #5](https://github.com/aguacatero/scalar-wave-viz/pull/5#pullrequestreview-5566614469) and merged into `main`.
- **P1 — ACCEPTED AND MERGED.** Numerical validation and whole-apparatus 2D force accounting accepted at [R11 on draft PR #10](https://github.com/aguacatero/scalar-wave-viz/pull/10#pullrequestreview-5644613779) for scientific code SHA `2a87abd0f8de873899f541d521d303d0f4462954` ([72 tests passed in CI Run 40198587319](https://github.com/aguacatero/scalar-wave-viz/actions/runs/40198587319)). PR #10 merged to `main` at `8e1fdb32655d073002ae5a794b08e48f19a78a0f` following explicit owner authorization. [Issue #6](https://github.com/aguacatero/scalar-wave-viz/issues/6) closed.
- **P2 — ACTIVE (DRAFT PR PENDING INDEPENDENT RE-REVIEW — R4).** [Exodus patent US11511891B2 FIGS. 4–8 reproduction and H0/H1 hypothesis separation](https://github.com/aguacatero/scalar-wave-viz/issues/7) on [Draft PR #11](https://github.com/aguacatero/scalar-wave-viz/pull/11). Evaluates conventional electrostatics Maxwell-stress baseline (H0, 2D and finite 3D) vs. patent-specific hypothesis (H1, Eq. 11) and programmatic controls with contextual literature audit ([Tajmar & Schreiber 2020](https://doi.org/10.1016/j.elstat.2020.103477)). [R3 review](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6544610778) concluded `CHANGES REQUIRED — P2 R3 SCIENTIFIC BASELINE NOT ACCEPTED` (3 High, 2 Medium findings); R4 remediation implemented independent planar dielectric material reaction benchmark (`benchmark_analytic_planar_dielectric_slab_force`) validating virtual work against contour stress (2.2% agreement), commensurate 3D grid spacings ($1.27\text{ mm}$) ensuring exact 1.0000 geometry ratios without distortion, structured 5-part uncertainty budget, strict 23.7 µN physical discrimination threshold (`physical_scale_discrimination_status = "NOT_RESOLVED_AT_CURRENT_3D_GRID_RESOLUTION"`), 2D observed convergence order $p_{\text{obs}} \approx 0.368$ and tip scaling $\alpha_{\text{tip}} \approx 0.23–0.38 \in [0.2, 0.5]$ (governed by $r^{-1/3}$ corner singularity), version-controlled PR description in `docs/PR_DESCRIPTION.md` mechanically verified by tests, and expanded test suite to 43 P2 tests (115 total tests). Requires independent ChatGPT scientific review before acceptance; do not merge without separate owner authorization.
- **P3 and P4 — PENDING.** Nuclear/scalar-field hypotheses and the interactive research dashboard have not passed their scientific gates.

**Agent update rule:** on every substantive project update and every readiness/completion handoff, verify and refresh this section; update `assets/research-progress.svg` and this image's alt text when gate/status labels change. Follow [AGENTS.md](AGENTS.md#mandatory-readme-progress-synchronization--every-project-update).

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

- [wave_3d.ipynb](wave_3d.ipynb): a 3D *mathematical* scalar wave simulation, with user-selected relative material wave speeds Air=1, Bismuth=0.55, Moscovium=0.15, metamaterial=0.04. **These values are hypothetical presets**, not established material responses. The toy equation has independently reviewed numerical checks, but the more extreme hypothetical material speed presets remain under-resolved and cannot support physical material claims.
- [mc_stability.ipynb](mc_stability.ipynb): exploratory nuclear stability and synthesis charts. Hypothetical Mc-291–299 half-lives and the isotope-mass-to-wave-speed interpolation are **not derived by the software** from measured data or validated model predictions.
- [wave_demo.ipynb](wave_demo.ipynb): educational wave examples; one saved output contains a Matplotlib error.

[Legacy Binder demo](https://mybinder.org/v2/gh/aguacatero/scalar-wave-viz/HEAD?filepath=wave_3d.ipynb) (compatibility and physics not validated).

## Research direction

The [Exodus patents](https://ept.space/patents/) describe proposed forces from asymmetric electrostatic pressure; they do **not** establish the scalar material model above. Next, independently select and reproduce a fully specified patent geometry and compare conventional Maxwell-stress accounting with the explicitly cited patent model and experimental evidence, including external couplings and null controls.

All PRs changing physics must disclose equations, sources, units, boundaries, assumptions, benchmarks and uncertainty. Null results are successful scientific information.
