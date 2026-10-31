# Scientific implementation plan and review gates

## P0 — initial conventional baseline (accepted and merged)

- [x] Add epistemic labels and explicitly flag the legacy notebook assumptions.
- [x] Implement the independent ideal-plate analytic electric pressure, force and stored-energy example.
- [x] Solve 2D Laplace Dirichlet potential for cylindrical electrode sections in a grounded enclosure.
- [x] Test the solver against exact linear harmonic potential and symmetry, boundary and scaling constraints.
- [x] Export a static figure labeling fields, units and separate analytic force results.
- [x] Add CI workflow.
- [x] Confirm remote CI checks after publishing this PR (verified workflow run 39187698432 on PR #5; confirms workflow execution and test pass, NOT physical validation of novel propulsion).

## P1 — numerical repairs and validations (accepted and merged)

- [x] Relocate 3D scalar source out of boundary damping and implement verifiable absorbing boundaries.
- [x] Resolve all frequencies at appropriate grid points/wavelength, then demonstrate convergence and known reflection benchmarks.
- [x] Validate discrete energy conservation and source normalization.
- [x] Add convergence and closed-contour stress integration for the electrostatic field; track reaction on grounded enclosure.

*Status (2026-10-25):* Independently accepted in R11 review ([pullrequestreview-5644613779](https://github.com/aguacatero/scalar-wave-viz/pull/10#pullrequestreview-5644613779)) for scientific code SHA `2a87abd0f8de873899f541d521d303d0f4462954` ([72 tests passed in CI Run 40198587319](https://github.com/aguacatero/scalar-wave-viz/actions/runs/40198587319)). Merged to `main` at `8e1fdb32655d073002ae5a794b08e48f19a78a0f` following explicit owner authorization. [Issue #6](https://github.com/aguacatero/scalar-wave-viz/issues/6) closed.

## P2 — Exodus source-bounded reproduction (active; in progress)

- [ ] Select patent figure and transcribe exact claim and relevant equations with citations.
- [ ] Implement its geometry accurately; use 3D when 2D does not preserve force dimensions.
- [ ] Benchmark field solution and compute forces on **whole device** plus environment.
- [ ] Add H0-versus-H1 prediction comparison with error and experimental control panels.

*Status (2026-10-31):* Active on dedicated branch `p2-patent-geometry-exodus-2026-10-25` under Draft [PR #11](https://github.com/aguacatero/scalar-wave-viz/pull/11) ([Issue #7](https://github.com/aguacatero/scalar-wave-viz/issues/7)). Checkboxes remain unchecked pending independent scientific acceptance. Independent ChatGPT scientific review R3 ([issuecomment-6544610778](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6544610778)) concluded `CHANGES REQUIRED — P2 R3 SCIENTIFIC BASELINE NOT ACCEPTED` (3 High, 2 Medium findings). R4 remediation implements independent dielectric material reaction benchmark (`benchmark_analytic_planar_dielectric_slab_force`) validating virtual work against contour stress (2.2% agreement), commensurate 3D grid spacings ($1.27\text{ mm}$) ensuring exact 1.0000 geometry ratios without distortion, structured 5-part uncertainty budget, strict 23.7 µN physical discrimination threshold (`physical_scale_discrimination_status = "NOT_RESOLVED_AT_CURRENT_3D_GRID_RESOLUTION"`), 2D observed convergence order $p_{\text{obs}} \approx 0.368$ and tip scaling $\alpha_{\text{tip}} \approx 0.23–0.38 \in [0.2, 0.5]$ (governed by $r^{-1/3}$ corner singularity), version-controlled PR description in `docs/PR_DESCRIPTION.md` mechanically verified by tests, and expanded test suite to 43 P2 tests (115 total tests). Awaiting independent ChatGPT R4 re-review.

## P3 — nuclear and scalar-field hypotheses

- [ ] Replace the hardcoded isotope half-lives and their false implication of wave speed with traceable evaluated/predicted nuclear data and error labels.
- [ ] Define an explicit scalar-field Lagrangian/equation and coupling, with known-physics limit and falsifiable prediction.
- [ ] Keep novel modes and speculative properties distinctly labeled.

## P4 — scientific research dashboard

- [ ] Interactive parameter controls, metadata download, independent sources, error bars and publishable static figures.
- [ ] Independent critical review before merging physics-bearing work.

Methods: [Superpowers](https://github.com/obra/superpowers) (design, red-green tests, review), [Matt Pocock skills](https://github.com/mattpocock/skills) (domain-model grilling, decisions and glossary), and [Scientific Agent Skills](https://github.com/k-dense-ai/scientific-agent-skills) (hypothesis, units, experiment design, uncertainty and honest scientific visualization). These guide process, not physical truth.
