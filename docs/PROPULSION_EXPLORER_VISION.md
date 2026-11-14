# Propulsion Explorer — visual-first product vision

## For anyone curious about propulsion

**Scalar Wave Viz** aims to become a visual laboratory where people can explore electric and proposed scalar-field phenomena, understand where forces act and how momentum is exchanged, and see what would be required to test an unusual propulsion claim.

Imagine a 3D device you can rotate and look inside. You can turn electric field lines on and off, see arrows on each electrode, change the voltage, inspect materials, and ask why the whole device might — or might not — move. A physicist can inspect the equations and numerical limits behind the same visual.

**Status:** This is a product plan, not a finished app, a certified engineering drawing or a demonstrated propellantless thruster.

## Four questions every view must answer

1. **What am I seeing?** Identify parts, fields, forces, units and whether a scene is illustrative, computed or measured.
2. **Why is it happening?** Explain the governing conventional physics, and separate it from alternative hypotheses.
3. **What would change it?** Provide documented parameters and clearly indicate what is genuinely recalculated.
4. **How could we test it?** Show the required observable, opposing explanation, controls, uncertainty and missing information.

## First user journey: a documented Exodus geometry

The visitor opens a simplified, sourced representation of an Exodus patent electrode assembly and:

- Rotates, zooms, selects and cuts through the 3D model.
- Switches layers: device geometry, potentials, electric field, local Maxwell-stress traction, reaction forces, material dielectric regions, and enclosure/environment.
- Clicks a component to find its role, dimensions, material, provenance and uncertainty.
- Changes well-defined geometry, voltage, dielectric properties or model boundaries; distinguishes **illustrative previews** from actual recomputed simulation output.
- Switches among **H0: conventional electrostatics and complete force accounting**, **H1: a precise published patent prediction**, and **H2: competing ordinary explanations** such as ion wind, power-lead forces, chamber coupling and thermal or instrument drift.
- Views an accounting panel for blades/electrodes, ground, dielectrics, supports, walls, external environment and electromagnetic field momentum. **Unknown terms stay unknown** — never replace missing forces with zero.
- Sees a plain-English explanation of what the model does **not** establish and the controls necessary to discriminate among mechanisms.

**The lesson:** large, asymmetric local forces can occur even when the forces on a closed assembly balance. A credible propulsion claim requires accounting for momentum transferred to matter, radiation, environment or otherwise specified fields, and measuring it.

## Preliminary experimental test-article specification

The long-term planner should be able to export a **provisional, source-traceable** hardware and experiment specification, not a guaranteed propulsion design:

| Item | Information to record |
| --- | --- |
| Geometry | Patent/figure reference, dimensions, tolerances, gaps, rounding, uncertain dimensions |
| Electrode assembly | Conductor, blade count, mounts, finish and electrical connections |
| Dielectric | Candidate materials, cited permittivity, conditions, breakdown/leakage assumptions |
| Electrical input | Voltage, current and power where known, driver/source, polarity, duty cycle and unknown values |
| Environment | Pressure, air/vacuum conditions, nearby conductive walls, ground paths |
| Instrumentation | Force or torque measurement, uncertainty and independent controls |
| Confounders | Ion wind, leakage, wiring, outgassing, vibration, electrostatic coupling and thermal drift |
| Evidence grade | Claimed vs modeled vs measured; bounded vs unknown uncertainties |
| Safety | Explicit need for qualified high-voltage and experimental-laboratory safety review |

Do not invent material properties, guarantee thrust or silently transform patent illustrations into manufacturing-ready instructions. Real high-voltage prototypes need independent engineering oversight.

## Keep the research paths separate

**Established electrodynamics:** Electric fields, Maxwell stress, dielectric polarization, electromagnetically accelerated exhaust, ion wind and momentum accounting are established physics, even if a particular numerical implementation needs verification.

**Exodus's published hypothesis:** The patent describes a proposed effect from asymmetric electrostatic pressure. Evaluate its actual geometry and derivation, compare it with conventional forces, and seek discriminating measurements. Patent issuance is not validation of novel physical propulsion.

**Mathematical scalar-wave visualization:** A scalar-valued field in a mathematical simulation is not evidence of a new physical scalar-wave interaction.

**Hypothetical physical scalar fields:** Only introduce an actual propulsion mechanism after stating a field equation or Lagrangian, coupling to matter, established-physics limit, quantitative prediction and falsification experiment. Do not infer special material properties from arbitrary presets.

## Visual-product milestones — in parallel with the scientific review gates

- **V0 — first usable 3D explainer:** one grounded, sourced geometry; orbit, zoom, select, layer toggles, readable field/force arrows and a nonexpert tour. If early overlays are schematic, label them openly.
- **V0.1 — visual experience & UX polish:** centerpiece 3D view with studio lighting, knife-edge apex highlight, schematic directional streamlines, interactive/accessible 3D billboard labels with pointer/keyboard selection and screen-space collision relaxation, non-overlapping HUD legend placement, 1-click quick-select chip bar with dynamic voltage sync, full-screen laboratory mode toggle, qualified human-readable inspector roles/statuses, and responsive mobile layout (375px & 390px).
- **V0.2 — learn physics backwards (progressive iceberg journey):** nonblocking three-panel architecture (left guided learning panel, center unobstructed 3D viewport, right controls/inspector), progressive disclosure iceberg model (surface visual demonstration $\to$ shallow plain-English analogy $\to$ deeper Maxwell stress tensor equations $\to$ research null controls and competing mechanisms), 6-chapter scene-synchronized curriculum, visual callout annotations, pause/resume/reset controls, and free-exploration mode.
- **V1 — meaningful controls:** voltage, geometry and known material properties bound to a solver where supported; reliable units, visible provenance, numerical limitations and deterministic saved scenarios.
- **V2 — force and hypothesis comparisons:** whole-assembly reaction force ledger plus H0/H1/H2 views, uncertainty, positive/negative controls and known-propulsion comparators.
- **V3 — research design planner:** provisional bill of materials, known/unknown specifications, material choices, electrical inputs and a defensible measurement plan.
- **V4 — research dashboard:** exportable inputs, plots, method/commit references, uncertainties, supporting data and independent scientific review.

These are **proposed experience milestones**, not accepted or merged features. Prioritize a small V0 in parallel with P2's scientific remediation. Do not bypass the existing independent P0–P4 gates, or begin P3 scientific work without authorization.

## Definition of an understandable visualization

A newcomer should be able to explain **which parts attract, which forces oppose them, where the system transfers momentum, what is unknown, and how to test an alternative explanation** without needing to read source code.

Accessible interactions should include descriptions of colors and arrows, keyboard-friendly controls, readable labels, zoomable diagrams and plain definitions of specialist terms. Keep uncertainty labels visible; avoid visuals that imply a device is working because the arrows look dramatic.

## Collaboration

We welcome contributions in 3D/frontend development, physics modeling, verification, industrial illustration, accessible explanations and experimental design. See the [README](../README.md) for entry points and the [roadmap](ROADMAP.md) for work packages.

**Agent rule:** Every Antigravity/Hermes session that substantively changes the project also updates the public README **in the same branch/PR**, with the newly verified scientific and product status. A review-only session still verifies README accuracy and reports no status change when appropriate. Follow [AGENTS.md](../AGENTS.md). This does not imply an unattended scheduler is running.
