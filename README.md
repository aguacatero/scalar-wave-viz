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

### Visual Explorer V0 / V0.1 — Available Now in Browser

The interactive 3D Propulsion Explorer is runnable directly in your web browser:
- **Interactive 3D Geometry:** Orbit, zoom, and inspect an Exodus-inspired single-stage electrode assembly (US11511891B2 FIGS. 4–8) featuring a high-voltage blade cathode (-20 kV), a planar ground counter-electrode (0 V), solid dielectric potting block, grounded chamber walls, and structural insulating mount.
- **Visual Atmosphere & Lighting (V0.1):** Studio laboratory lighting with cool cyan fill for electrode undersides, warm specular rim accents, a dual-zone coordinate ground grid, and a razor-sharp knife-edge apex highlight along the active cathode tip.
- **Dynamic 3D Component Labels (V0.1):** Real-time billboard labels tracking component coordinates in 3D camera space, toggleable with the `L` key or HUD toolbar button.
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

## Project progress — verified November 6, 2026

![Scientific roadmap: P0 and P1 accepted and merged; P2 active in draft review; P3 and P4 pending; 2 of 5 gates accepted](assets/research-progress.svg)

**2 of 5 independently reviewed scientific phases are accepted.** This is *not* a percentage of product completion or proof of unusual propulsion. Educational visual milestones (Track A) proceed in parallel with scientific remediation (Track B).

- **Track A (Interactive 3D Explorer) — V0.1 R4 REMEDIATED & READY FOR INDEPENDENT RE-REVIEW:**
  - **V0 — BASELINE ACCEPTED (ROUND 5):** Complete standalone browser application delivered on branch `v0-propulsion-explorer-3d` ([Issue #13](https://github.com/aguacatero/scalar-wave-viz/issues/13), [Draft PR #14](https://github.com/aguacatero/scalar-wave-viz/pull/14)), accepted by ChatGPT independent review V0 R5 at commit `5d8b822e8771dc19a4bf2a27bfc013e3662e03ea`.
  - **V0.1 — VISUAL EXPERIENCE & UX POLISH (ROUND 4 REMEDIATION):** Stacked feature branch `feat/v0-1-visual-ux-polish` ([Draft PR #15](https://github.com/aguacatero/scalar-wave-viz/pull/15)). Remediated all findings from ChatGPT independent reviews V0.1 R1 (`pullrequestreview-5808774072`), V0.1 R2 (`pullrequestreview-5809773862`), and V0.1 R3 (`pullrequestreview-5813174089`):
    - `V0.1-R3-F1`: Clamped single-pin layout before early-return guard in `resolveLabelCollisions`, ensuring single visible chamber pin (when Component Geometry is toggled OFF) is strictly clamped within canvas bounds and below `.view-preset-hud` toolbar (`y >= topMargin`, `y <= maxY`) across mobile viewports (375px/390px) and desktop; backed by Playwright browser regression test and screenshot `assets/propulsion_explorer_v0_single_pin.png`.
    - `V0.1-R3-M1`: Expanded cross-preset interaction verification in `test_v0_browser_smoke.py`: asserts exact 5-pin ID set and zero bounding-box overlap across all 4 camera presets (`isometric`, `side`, `front`, `top`) and viewports (`1280x800`, `390x844`, `375x812`), with direct button identity assertions `document.elementFromPoint(cx, cy) === pinElement` (validating `.label-pin * { pointer-events: none; }`) and real pointer clicks driving inspector updates.
    - `V0.1-R3-M2`: Removed formal/unconditional guarantee claims across code comments, tests, and documentation (re-qualified as *multi-pass screen-space collision relaxation with vertical staggering and bounded clearance fallback*); added vertical capacity shortfall check with dynamic margin compression, secondary horizontal staggering fallback, and dynamic clearance measurement for HUD preset toolbar and bottom component chip bar.
    - `V0.1-R2-F1`: Repositioned scientific-legend HUD (`.layer-legend-hud`) below camera preset HUD with constrained max-width (290px), preventing visual overlap across desktop and tablet viewports.
    - `V0.1-R2-F2`: Screen-space label collision relaxation with transparent child pointer events (`.label-pin * { pointer-events: none; }`), distinct 3D anchor points, and 1D layout sweep on mobile/desktop, ensuring 100% reliable center pointer hit-testing (`elementFromPoint`) and selection clicks on all 5 components with zero visual overlap across viewports (1280x800 desktop, 390x844 iPhone 12/13/14, 375x812 iPhone SE) and camera presets (Isometric, Side, Front, Top).
    - `V0.1-R2-M1`: Synchronized PR #15 body and documentation with current 138-test suite (40 V0 unit + 26 browser smoke + 35 P0 + 16 P1 numerics + 21 P1 wave) and schematic-only direction marker semantics.
    - `V0.1-R1-F1`: Billboard labels made fully interactive (`pointer-events: auto`, `type="button"`, `aria-label`, `aria-pressed`); container made accessible region (`role="region" aria-label="3D Component Labels"`) without contradictory `aria-hidden`; interior pins cleanly hide when geometry layer is toggled off; verified with real `page.mouse.click` and keyboard `Enter` activation.
    - `V0.1-R1-F2`: Streamline direction markers explicitly qualified as schematic orientation indicators only ($\mathbf{E} = -\nabla\Phi$), removing all claims of physical particles, charge transport, wave propagation, or computed $|\mathbf{E}|$ magnitude across UI, legend, and documentation.
    - `V0.1-R1-M1`: Quick-select chip bar dynamically synchronizes with voltage slider across sweeps (`Blade (0 V OFF)`, `Blade (-20 kV)`, `Blade (-50 kV)`), verified in browser smoke tests.
    - `V0.1-R1-M2`: Inspector card dynamically separates unenergized 0 V state (`Field OFF at 0 V — Zero Electrostatic Traction`) from energized state, avoiding unsupported pairwise equality claims on the two electrodes alone and qualifying multi-body forces with dielectric and chamber coupling.
    - Verification: 40 V0 unit tests passing; 26 browser smoke tests passing; 138 total tests passing across repo. Preserves unmerged PR #14 and accepted P0/P1 baselines.
- **Track B (Scientific Acceptance Gates) — 2 OF 5 ACCEPTED:**
  - **P0 — ACCEPTED AND MERGED:** Conventional electrostatics baseline, [PR #5](https://github.com/aguacatero/scalar-wave-viz/pull/5).
  - **P1 — ACCEPTED AND MERGED:** Numerical validation and force accounting, [PR #10](https://github.com/aguacatero/scalar-wave-viz/pull/10). Accepted R11 scientific SHA `2a87abd0f8de873899f541d521d303d0f4462954`; **merged** in main commit `8e1fdb32655d073002ae5a794b08e48f19a78a0f`.
  - **P2 — ACTIVE DRAFT, NOT SCIENTIFICALLY ACCEPTED:** Exodus geometry and H0/H1 comparison in [Issue #7](https://github.com/aguacatero/scalar-wave-viz/issues/7), [Draft PR #11](https://github.com/aguacatero/scalar-wave-viz/pull/11). The [independent R9 review](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6566089334) concluded `CHANGES REQUIRED — P2 R9 SCIENTIFIC BASELINE NOT ACCEPTED` (findings tracked for R10: full-length FIG. 21 refinement, domain sensitivity bounds, 3D dielectric virtual work benchmark, multi-body discretization extrapolation, and missing-term reporting). P2 remains separate from V0, draft and unmerged.
  - **P3 — PENDING:** Physical scalar-field and nuclear hypotheses with traceable evidence and falsifiable predictions.
  - **P4 — PENDING SCIENTIFIC GATE:** Final validated research dashboard.

**Next user-facing milestone:** independent review of V0.1 UX polish, then V1 solver integration. **Next scientific milestone:** resolve P2's independent R10 findings. Neither is claimed complete.

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
