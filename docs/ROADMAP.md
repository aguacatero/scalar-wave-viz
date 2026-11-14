# Scalar Wave Viz roadmap — visualize first, verify rigorously

**The user goal:** an approachable 3D visual laboratory for learning how electric and proposed scalar fields interact with matter, why objects experience forces, whether a complete device could propel itself, and what a controlled experimental prototype would require.

Work on **Track A (the visual explorer)** in parallel with **Track B (scientific acceptance)**. Do not wait until all scientific review gates are finished to make an honest educational visual, and never treat an attractive render or passing tests as proof of anomalous propulsion.

Read [the product vision](PROPULSION_EXPLORER_VISION.md) and [the scientific charter](SCIENCE_CHARTER.md).

## Track A — interactive visual explorer (planned; independent of P0–P4 acceptance count)

- [x] **V0: Useful first 3D view.** Documented electrode geometry with orbit/zoom, component selection, schematic or computed electric-field layers, local force arrows and mechanical reactions, and a plain-English tour. Clearly distinguish illustrative overlays from solved fields. Implemented on branch `v0-propulsion-explorer-3d` ([Issue #13](https://github.com/aguacatero/scalar-wave-viz/issues/13), [PR #14](https://github.com/aguacatero/scalar-wave-viz/pull/14)); R5 accepted by ChatGPT at `5d8b822e8771dc19a4bf2a27bfc013e3662e03ea` and merged into `main` (`bc3929605300177c3ac26a579930af915c5cebea`).
- [x] **V0.1: Visual experience & UX polish.** Centerpiece 3D view with studio lighting, knife-edge apex highlight, schematic directional streamlines, interactive/accessible 3D billboard labels with pointer/keyboard selection and screen-space collision relaxation, non-overlapping HUD legend placement, 1-click quick-select chip bar with dynamic voltage sync, full-screen laboratory mode toggle, qualified human-readable inspector roles/statuses, and responsive mobile layout (375px & 390px). Implemented on stacked branch `feat/v0-1-visual-ux-polish` ([Draft PR #15](https://github.com/aguacatero/scalar-wave-viz/pull/15)); **R5 accepted by ChatGPT** ([pullrequestreview-5816455237](https://github.com/aguacatero/scalar-wave-viz/pull/15#pullrequestreview-5816455237)) at exact code SHA `55da03af781dbc1470a2bd22a7b9dfc93bbf0950` (unmerged draft; 140 repository tests passing).
- [x] **V0.2: Learn Physics Backwards.** Transform technical 3D demonstration into an intuitive, visual-first physics learning experience using the Iceberg Learning Model (Surface $\to$ Shallow depth $\to$ Deeper $\to$ Research depth). Nonblocking 3-panel layout (left learning panel, center unobstructed 3D viewport, right controls/inspector), 6-chapter scene-synchronized curriculum, 3D mathematical scalar-wave contrast visualizer (`scalarWaveGroup`, `#scalar-wave-badge`), clean semantic HTML math and clickable primary citations, bidirectional mobile ledger navigation and unconstrained vertical scrolling, visual callout annotations, pause/resume/reset, free-exploration mode, progressive disclosure `<details>`, and responsive mobile panel tabs. Implemented on stacked branch `feat/v0-2-learn-physics-backwards` ([Issue #17](https://github.com/aguacatero/scalar-wave-viz/issues/17), [Draft PR #18](https://github.com/aguacatero/scalar-wave-viz/pull/18)); **R6 ACCEPTED FOR V0.2 EDUCATIONAL VISUAL BASELINE** by ChatGPT ([issuecomment-6871100151](https://github.com/aguacatero/scalar-wave-viz/pull/18#issuecomment-6871100151)) at frozen code SHA `634437f70e6b2bdd5b3bd41d6b77cbe551078f05` (0 HIGH, 0 MEDIUM; R6-N1 doc observation resolved in documentation-only closeout; 157 repository tests passing; unmerged draft preserving accepted V0 and V0.1 baselines).
- [ ] **V1: Interactive solver integration (SPECIFICATION R2 PREPARED FOR RE-REVIEW).** Connect interactive voltage, gap, and benchmark geometry controls to validated conventional P0/P1 electrostatic calculations (`electrostatics_baseline.py`, `electrostatics_numerics.py`) via a loopback-enforced `run_explorer.py` bridge (`n` $\in \{41,81,101\}$, strict RFC 8259 JSON `null` masking, `request_id` concurrency protection) and bundled offline `file://` snapshots (`v1_reference_snapshots.js`), enforcing grid-resolved contour topology checks before emitting force budgets, reporting all 6 conductor force components, net vector residuals, $V^2$ tolerance scaling, and honest `UNBALANCED_EXCEEDS_TOLERANCE` / `NOT_ASSESSED` uncertainty labels, keeping 3D Exodus schematic force arrows and $\varepsilon_r$ visual proxy strictly separated from computed fields, preserving the Iceberg Learning Model, and isolating unaccepted P2 calculations via cryptographic solver blob-hash checks. See [V1 Solver Integration Spec R2](V1_SOLVER_INTEGRATION_SPEC.md) (including PR #15 $\to$ PR #18 merge sequencing).
- [ ] **V2: Whole-device force story.** H0 conventional force ledger vs H1 sourced patent prediction vs H2 conventional confounders, plus environmental momentum paths and null controls.
- [ ] **V3: Test-article planner.** Provisional geometry/dimensions, candidate materials, electrical inputs, missing specifications, research BOM outline and independent test conditions. No implied high-voltage safety certification or functioning propulsion design.
- [ ] **V4: Evidence dashboard.** Export figures, parameters, source revisions, uncertainty/error bars, literature sources and measurement-control checklists. Formal scientific P4 review still required.

**First priority:** build V0 using whatever physics is already established or explicitly labeled provisional. Capture simple usability feedback from nonexperts before building an elaborate research UI.

## Track B — scientific acceptance gates

### P0 — first conventional baseline (ACCEPTED / MERGED)

- [x] Label established vs hypothesized physics and flag legacy notebook assumptions.
- [x] Analytic capacitor-force and energy reference.
- [x] 2D electrostatic potential/field in a grounded enclosure; symmetry, units and boundary tests.
- [x] Reproducible baseline figure and CI; independently reviewed, owner-authorized merge in [PR #5](https://github.com/aguacatero/scalar-wave-viz/pull/5).

### P1 — numerical repairs and force accounting (ACCEPTED / MERGED)

- [x] Repair 3D mathematical scalar-wave source, absorption/reflection benchmarks and energy-conservation checks.
- [x] Electrostatic mesh convergence and closed-surface stress accounting, including surrounding conductors.
- [x] Independent scientific R11 acceptance for code SHA `2a87abd0f8de873899f541d521d303d0f4462954`, [72-test CI](https://github.com/aguacatero/scalar-wave-viz/actions/runs/40198587319).
- [x] [PR #10](https://github.com/aguacatero/scalar-wave-viz/pull/10) owner-authorized merge; main SHA `8e1fdb32655d073002ae5a794b08e48f19a78a0f` on 2026-10-25.

### P2 — Exodus source-bounded patent geometry (ACTIVE DRAFT / NOT ACCEPTED)

- [x] A source-cited geometry/H0-H1 comparison and 3D modeling implementation **exist on Draft PR #11**, not as accepted science.
- [ ] Demonstrate full declared-article 3D convergence and force accounting for electrodes, dielectric, enclosure and environment.
- [ ] Validate domain-clearance, dielectric/interface, axial and full-device uncertainty estimates; export strict finite scientific evidence.
- [ ] Independent review sign-off at the correct SHA and **separate owner-authorized merge**.

**Verified as of 2026-11-01:** [Issue #7](https://github.com/aguacatero/scalar-wave-viz/issues/7), [Draft PR #11](https://github.com/aguacatero/scalar-wave-viz/pull/11); the [independent R9 review](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6566089334) concluded `CHANGES REQUIRED — P2 R9 SCIENTIFIC BASELINE NOT ACCEPTED` (findings tracked for R10: full-length FIG. 21 refinement, domain sensitivity bounds, 3D dielectric virtual work benchmark, multi-body discretization extrapolation, and missing-term reporting). P2 remains scientifically unaccepted, draft and unmerged; do not start P3 scientific work. V0 visual explorer development proceeds in parallel on Track A.

### P3 — physical scalar and nuclear hypotheses (PENDING)

- [ ] Replace speculative isotope half-lives and mass-number-to-wave-speed extrapolations with genuine data or clearly identified hypothetical inputs.
- [ ] Specify any new physical scalar field with a field equation or Lagrangian, material coupling, established-physics limit, dimensional consistency, measurable prediction and falsification test.
- [ ] Keep numerical and experimental uncertainty distinct. No novel physical modes are established by the legacy scalar-wave notebook.

### P4 — independently reviewed science dashboard (PENDING)

- [ ] Complete interactive evidence dashboard, independent sources, provenance export, error bars and reproducible figures.
- [ ] Independent critical review of scientific displays and owner-authorized merge.

**Important distinction:** user-facing V0/V1 development may proceed in Track A, but the formal P4 science gate remains pending. P2 findings cannot be bypassed through UI implementation.

## Working agreements

Every screen should answer **What am I seeing? Why? What would change it? How could we test it?** Every model declares equations, units, material assumptions, boundary conditions, and uncertainty. Distinguish established laws, published hypotheses, illustrative what-if scenarios, and measurements. Complete whole-device force accounting is required before interpreting a numerical residual as propulsion.

Follow [AGENTS.md](../AGENTS.md): **every substantive Antigravity/Hermes work session must synchronize the public README in the same branch/PR**, using verified live PR and CI status. Update the scientific progress figure if labels or gate counts change. Null results are scientific progress.

Methods such as [Superpowers](https://github.com/obra/superpowers), [Matt Pocock skills](https://github.com/mattpocock/skills) and [Scientific Agent Skills](https://github.com/k-dense-ai/scientific-agent-skills) assist execution and review, not physical proof.
