# Scalar Wave Viz

**A visual laboratory for understanding how fields create forces — and exploring whether proposed propulsion devices could actually work.**

Imagine rotating a 3D device, watching electric fields, changing its voltage or materials, and seeing which parts are pushed or pulled. Then ask: **Does the whole device move, or do its internal forces cancel? What would we need to measure to find out?**

That is the goal of Scalar Wave Viz. We are building for curious nonspecialists as well as engineers and scientists. You do **not** need a physics degree to follow or contribute.

> **Reality check:** This is an educational and experimental research project, **not a working propellantless thruster**. It has not demonstrated anomalous propulsion, electrogravitics, a physical exotic scalar wave, or extraordinary moscovium properties. Patent claims and simulations are not proof of thrust.

## What we're building: a Propulsion Explorer

The planned **interactive 3D lab** lets anyone:

1. **See it:** Rotate an apparatus; show electric fields, charge distribution, force arrows, and surrounding supports and walls.
2. **Change it:** Adjust electrode geometry, spacing, voltage and documented material properties; see what the model predicts.
3. **Understand it:** See the forces on **every component** and where momentum goes. Compare conventional physics with clearly identified alternative hypotheses.
4. **Test it:** Find the source and uncertainty behind each result, and learn which controls would distinguish a real effect from ion wind, nearby surfaces, wires or measurement drift.
5. **Plan it:** Eventually export *provisional* dimensions, material requirements, electrical inputs, missing specifications, a bill-of-materials outline, and a controlled test plan — **not a proven propulsion recipe**.

### Visual Explorer V0 / V0.1 / V0.2 — Available Now in Browser

The interactive 3D Propulsion Explorer is runnable directly in your web browser:
- **Nonblocking Three-Panel Layout (V0.2):** Dedicated guided learning panel on the left, unobstructed interactive 3D visualization in the center, and simplified parameter controls and component inspector on the right. Replaces the modal overlay to keep the device fully visible and interactive at all times, with responsive mobile tabs preserving 3D visibility at the top of small viewports.
- **Iceberg Learning Model & Progressive Disclosure (V0.2):** Default plain-English explanations and everyday physical analogies in surface/shallow layers, expandable deeper technical Maxwell stress tensor formulas ($\mathbf{T}_{ij} = \varepsilon_0 (E_i E_j - \frac{1}{2} \delta_{ij} |\mathbf{E}|^2)$) and citations, and research-level competing hypotheses (corona ion wind, chamber wall image coupling) and discriminating null controls.
- **3D Mathematical Scalar Wave Contrast (V0.2 R2):** Dedicated interactive 3D visual contrast overlay (`#scalar-wave-badge`, `scalarWaveGroup`), demonstrating the geometric and mathematical difference between isotropic, undulating scalar wavefront shells ($\nabla^2\psi - \frac{1}{c^2}\partial_t^2\psi = 0$) and directed electrostatic vector streamlines ($\mathbf{E} = -\nabla\Phi$), strictly qualified as a toy mathematical illustration not coupled to capacitor thrust or novel propulsion.
- **Accessible Semantic Math & Clickable Primary Citations (V0.2 R2):** Accessible, beautifully formatted equations without raw unescaped LaTeX delimiters, accompanied by trusted, clickable deep links to primary patent sections (US11511891B2), canonical textbooks (Jackson, Griffiths, Feynman), and peer-reviewed literature with verified DOIs (Tajmar & Schreiber 2020, *Journal of Electrostatics* 107, 103477).
- **Bidirectional Mobile Ledger Navigation (V0.2 R2):** Seamless mobile navigation buttons (`#btn-chapter4-open-ledger` and `#btn-ledger-back-to-guide`) and unconstrained scrolling ensuring full accessibility across mobile viewports (375px & 390px) without vertical clipping.
- **Rigorous Boundary A Accounting (V0.2 R2):** Clearly distinguishes internal action-reaction cancellation ($\sum \mathbf{F}_{\text{internal}} \equiv \mathbf{0}$) from unverified external chamber wall coupling across the suspended test article boundary ($\oint_{\partial V_A} \mathbf{T}\cdot\hat{\mathbf{n}}\,dA \neq 0$ pending calibrated geometry).
- **Six-Chapter Synchronized Journey (V0.2):** Guided curriculum stepping through *Meet the Device* (unenergized 0 V state), *Turn on the Electricity* (-20 kV applied), *Follow the Forces*, *Can the Whole Device Move?* (action-reaction balance), *What Are Scalar Waves?*, and *How Could We Test the Hypothesis?* with dynamic camera framing, synchronized component highlights, and nonblocking callout annotations.
- **Exploration & Tour Controls (V0.2):** Next, Back, Pause/Resume, Reset Tour, and Explore Freely mode allowing unconstrained user inspection at any point.
- **Interactive 3D Geometry:** Orbit, zoom, and inspect an Exodus-inspired single-stage electrode assembly (US11511891B2 FIGS. 4–8) featuring a high-voltage blade cathode (-20 kV), a planar ground counter-electrode (0 V), solid dielectric potting block, grounded chamber walls, and structural insulating mount.
- **Visual Atmosphere & Lighting (V0.1):** Studio laboratory lighting with cool cyan fill for electrode undersides, warm specular rim accents, a dual-zone coordinate ground grid, and a razor-sharp knife-edge apex highlight along the active cathode tip.
- **Dynamic 3D Component Labels (V0.1):** Real-time billboard labels tracking component coordinates in 3D camera space, toggleable with the `L` key or HUD toolbar button, with multi-pass screen-space collision relaxation and deterministic fallback.
- **Animated Schematic Direction Markers (V0.1):** Signed electric field streamlines with animated directional markers demonstrating conventional field orientation ($\mathbf{E} = -\nabla\Phi$) pointing from Ground ($0\text{ V}$) to Blade ($-20\text{ kV}$). Strictly qualified as schematic orientation indicators—not physical charge carriers, wave propagation, or computed $|\mathbf{E}|$ magnitude. Completely extinguished at 0 V.
- **Quick-Select Chip Bar & Full-Screen Mode (V0.1):** 1-click component quick-select toolbar for rapid selection on desktop and touch devices, alongside a full-screen laboratory mode toggling the sidebar (`S` key or HUD button).
- **Occlusion-Free Interior Picking:** Click or hover directly on interior components straight through the outer transparent chamber walls via intelligent raycasting priority, verified across default isometric, Side, and Top views with real canvas pointer interactions.
- **Beginner-Friendly Inspector (V0.1):** Plain-language descriptions of electrode roles, dielectric polarization, and mechanical counter-forces replacing raw internal strings, while preserving exact patent citations and Maxwell stress tensor formulas in expandable details.
- **Action-Reaction Force Ledger:** Structured by physical system boundaries, demonstrating that internal electrostatic forces sum identically to zero across the isolated Device Under Test (Boundary A), while clearly separating external lab environment walls (Boundary B) and the closed universe (Boundary C).
- **The Four Questions Tour:** Guided plain-language walkthrough answering *What am I seeing?*, *Why does it happen?*, *What changes it?*, and *How could we test it?*, rendered with accessible HTML math notation.
- **Honest Provenance & Disclaimers:** Explicitly marked `WHOLE-BODY THRUST: NOT MEASURED / NOT ESTABLISHED`. No unverified thrust claims, zero fabricated force numbers, explicit non-modeled tip radius metadata tag, and accurate patent citations (FIGS. 6B, 21, 23A for dielectric potting).
- **What-If Sandbox:** Explore how voltage ($0 - 50\text{ kV}$, scaling $\propto V^2$), dielectric permittivity (visual material proxy $\varepsilon_r \in [1, 5]$), and surface-to-surface electrode gap ($d \ge 16\text{ mm}$ maintaining $\ge 5.0\text{ mm}$ positive clearance from dielectric potting) alter field gradients, with zero GPU memory leaks verified by instrumented prototype disposal.
- **Accessible & Mobile-First Design (V0.1):** Crash-free keyboard navigation, modal focus trapping, and responsive layouts verified on mobile viewports at 375px (iPhone SE) and 390px (iPhone 12/13/14) with zero horizontal overflow.

![Propulsion Explorer 3D V0 Preview](assets/propulsion_explorer_v0_preview.png)

[Read the visual-first product vision](docs/PROPULSION_EXPLORER_VISION.md) and [dual-track roadmap](docs/ROADMAP.md).

## Why Exodus? Why scalar waves?

Our first detailed case study is [Exodus Propulsion Technologies](https://ept.space/) and its proposed **asymmetric electrostatic-pressure** effect, especially [patent US11511891B2](https://patents.google.com/patent/US11511891B2/en). An uneven electric field can cause impressive local electrode forces. But **a force on one electrode is not necessarily propulsion**: forces on the supports, other electrodes, power supply, enclosure and environment must be counted too.

This repo also explores **mathematical scalar waves**. That is a *separate* inquiry: a scalar-valued simulation does not demonstrate a new physical scalar field or scalar-wave propulsion. A proposed physical connection needs equations, measurable predictions and an independent test. Known mechanisms such as ion propulsion and ion wind will provide useful visual comparisons.

The question driving the project is **not "How do we prove Exodus is right?"** It is **"What could the effect be, what does established physics already explain, and what experiment could tell the difference?"**

## Two tracks, one goal

| Visual learning experience | Scientific engine |
| --- | --- |
| 3D selectable geometry; field and force layers | Reproducible equations and source-based geometry |
| Intuitive sliders, plain-language explanations | Reliable numerics, uncertainties and boundaries |
| Whole-device momentum illustrations; H0/H1 comparison | Whole-body force ledger, rival hypotheses and controls |
| Provisional prototype and experiment planner | Traceable material properties, missing inputs and safety review |

**Build a useful, clearly labeled educational visualizer early; never describe unverified physics as demonstrated thrust.** Passing tests and attractive plots do not replace physical measurement.

## Project progress — verified November 9, 2026

![Scientific roadmap: P0 and P1 accepted and merged; P2 active in draft review; P3 and P4 pending; 2 of 5 gates accepted](assets/research-progress.svg)

**2 of 5 independently reviewed scientific phases are accepted.** This is *not* a percentage of product completion or proof of unusual propulsion. Educational visual milestones (Track A) proceed in parallel with scientific remediation (Track B).

- **Track A (Interactive 3D Explorer) — V0.2 R2 REMEDIATED & READY FOR INDEPENDENT RE-REVIEW:**
  - **V0 — BASELINE ACCEPTED (ROUND 5):** Complete standalone browser application delivered on branch `v0-propulsion-explorer-3d` ([Issue #13](https://github.com/aguacatero/scalar-wave-viz/issues/13), [Draft PR #14](https://github.com/aguacatero/scalar-wave-viz/pull/14)), accepted by ChatGPT independent review V0 R5 at commit `5d8b822e8771dc19a4bf2a27bfc013e3662e03ea`.
  - **V0.1 — VISUAL EXPERIENCE & UX POLISH (ACCEPTED):** Stacked feature branch `feat/v0-1-visual-ux-polish` ([Draft PR #15](https://github.com/aguacatero/scalar-wave-viz/pull/15)). Remediated all findings from ChatGPT independent reviews V0.1 R1 through R4 at accepted commit `55da03af781dbc1470a2bd22a7b9dfc93bbf0950` (140 repository tests passing).
  - **V0.2 — LEARN PHYSICS BACKWARDS (ROUND 2 REMEDIATION):** Stacked feature branch `feat/v0-2-learn-physics-backwards` ([Issue #17](https://github.com/aguacatero/scalar-wave-viz/issues/17), [Draft PR #18](https://github.com/aguacatero/scalar-wave-viz/pull/18)). Remediated all 6 findings from ChatGPT independent review V0.2 R1 (`issuecomment-6748609227`):
    - `V0.2-R1-F1`: Completely purged unsourced device-specific force numbers and supposed observed uncertainties from all 6 chapters and JS fallback; backed by automated negative regex scanner in `test_v0_propulsion_explorer.py`.
    - `V0.2-R1-F2`: Corrected physical system boundary formulations for Boundary A; distinguished internal action-reaction cancellation ($\sum \mathbf{F}_{\text{internal}} \equiv \mathbf{0}$) from unverified external chamber coupling ($\oint_{\partial V_A} \mathbf{T}\cdot\hat{\mathbf{n}}\,dA \neq 0$ pending calibrated geometry); preserved strict momentum conservation across the complete universe (Boundary C).
    - `V0.2-R1-M1`: Delivered clean semantic HTML math without raw LaTeX delimiters and provided trusted, clickable deep links to primary patent sections and DOI citations across all deeper disclosures.
    - `V0.2-R1-M2`: Corrected Tajmar & Schreiber (2020) citation (*Journal of Electrostatics* 107, 103477, DOI: [10.1016/j.elstat.2020.103477](https://doi.org/10.1016/j.elstat.2020.103477)) and reported null limits ($\pm 0.3\text{ mg} \approx \pm 3\ \mu\text{N}$); explicitly parameterized ion wind relations ($d = 20\text{ mm}$, $I = 50\ \mu\text{A}$, $\mu = 2\times 10^{-4}\text{ m}^2/(\text{V}\cdot\text{s})$, $F \approx 5\text{ mN}$); qualified high-vacuum reduction and sharp tip field gradients.
    - `V0.2-R1-M3`: Eliminated mobile layout overflow constraints (`overflow-y: auto !important; height: auto !important; max-height: none !important;`) ensuring full vertical scrollability down to the footer on 375px & 390px viewports; added bidirectional navigation between guided learning content and the Action-Reaction Force Ledger (`#btn-chapter4-open-ledger` and `#btn-ledger-back-to-guide`).
    - `V0.2-R1-M4`: Implemented a dedicated 3D mathematical scalar-wave contrast visualizer (`scalarWaveGroup`, `#scalar-wave-badge`) demonstrating the difference between isotropic undulating scalar wavefronts ($\nabla^2\psi - \frac{1}{c^2}\partial_t^2\psi = 0$) and directional electrostatic vector streamlines ($\mathbf{E} = -\nabla\Phi$), strictly labeled as an illustrative toy not coupled to capacitor thrust.
    - *Verification:* 50 V0 unit tests passing; 33 browser smoke tests passing; 155 total repository tests passing across repo. Preserves unmerged PR #14, PR #15, and accepted P0/P1 baselines.
- **Track B (Scientific Acceptance Gates) — 2 OF 5 ACCEPTED:**
  - **P0 — ACCEPTED AND MERGED:** Conventional electrostatics baseline, [PR #5](https://github.com/aguacatero/scalar-wave-viz/pull/5).
  - **P1 — ACCEPTED AND MERGED:** Numerical validation and force accounting, [PR #10](https://github.com/aguacatero/scalar-wave-viz/pull/10). Accepted R11 scientific SHA `2a87abd0f8de873899f541d521d303d0f4462954`; **merged** in main commit `8e1fdb32655d073002ae5a794b08e48f19a78a0f`.
  - **P2 — ACTIVE DRAFT, NOT SCIENTIFICALLY ACCEPTED:** Exodus geometry and H0/H1 comparison in [Issue #7](https://github.com/aguacatero/scalar-wave-viz/issues/7), [Draft PR #11](https://github.com/aguacatero/scalar-wave-viz/pull/11). The [independent R9 review](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6566089334) concluded `CHANGES REQUIRED — P2 R9 SCIENTIFIC BASELINE NOT ACCEPTED` (findings tracked for R10: full-length FIG. 21 refinement, domain sensitivity bounds, 3D dielectric virtual work benchmark, multi-body discretization extrapolation, and missing-term reporting). P2 remains separate from V0, draft and unmerged.
  - **P3 — PENDING:** Physical scalar-field and nuclear hypotheses with traceable evidence and falsifiable predictions.
  - **P4 — PENDING SCIENTIFIC GATE:** Final validated research dashboard.

**Next user-facing milestone:** independent review of V0.2 Learn Physics Backwards, then V1 solver integration. **Next scientific milestone:** resolve P2's independent R10 findings. Neither is claimed complete.

**Standing Antigravity rule:** At the start and end of every substantive implementation session, inspect and synchronize the README with live GitHub status. Any substantive repository change must carry its README update in the **same branch/PR**, including plain-English status and next steps. A no-change review should still explicitly verify the README without fabricating an update. Follow [AGENTS.md](AGENTS.md#mandatory-readme-progress-synchronization--every-project-update). This rule does not itself run a background scheduler.

## How you can support the project

**Curious learners:** tell us which images or explanations would help you understand the forces. **Frontend and 3D developers:** contribute interactive scenes, sliders, accessibility and diagrams. **Physicists and numerical researchers:** check assumptions, force accounting and convergence. **Experimentalists and hardware engineers:** critique material specifications, confounding effects, uncertainty and safe measurement designs.

Start with the [visual product vision](docs/PROPULSION_EXPLORER_VISION.md) and [open GitHub issues](https://github.com/aguacatero/scalar-wave-viz/issues); open an issue to ask a question, suggest a feature, challenge a claim or offer expertise. Null results and constructive criticism are welcome.

## What already runs

### 3D Propulsion Explorer (V0 / V0.1) — Browser Laboratory

Run the zero-friction local launcher from repository root:

    python run_explorer.py

This starts a lightweight local HTTP server and automatically opens `http://127.0.0.1:8000` in your default browser. No build steps, Node packages, or Jupyter notebooks required.

Alternatively, serve with Python's standard library:

    python -m http.server 8000 --directory explorer

Or open `explorer/index.html` directly in any modern browser (offline capability with vendored Three.js).

### First reproducible conventional-electrostatics baseline

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

## Scientific standards and project references

[Scientific charter](docs/SCIENCE_CHARTER.md) · [Exodus comparison contract](docs/EXODUS_MODEL_CONTRACT.md) · [Visual product vision](docs/PROPULSION_EXPLORER_VISION.md) · [Roadmap](docs/ROADMAP.md) · [Agent operating rules](AGENTS.md).

Every scientific output must distinguish **established models**, **published hypotheses**, **what-if inputs**, **experimental measurements** and **unverified numerical results**, with sources, units, boundary conditions, and uncertainty. **A scientifically sound null result is progress.**
