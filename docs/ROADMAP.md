# Scientific implementation plan and review gates

## P0 — initial conventional baseline (this PR)

- [x] Add epistemic labels and explicitly flag the legacy notebook assumptions.
- [x] Implement the independent ideal-plate analytic electric pressure, force and stored-energy example.
- [x] Solve 2D Laplace Dirichlet potential for cylindrical electrode sections in a grounded enclosure.
- [x] Test the solver against exact linear harmonic potential and symmetry, boundary and scaling constraints.
- [x] Export a static figure labeling fields, units and separate analytic force results.
- [x] Add CI workflow.
- [ ] Confirm remote CI checks after publishing this PR.

## P1 — numerical repairs and validations

- [ ] Relocate 3D scalar source out of boundary damping and implement verifiable absorbing boundaries.
- [ ] Resolve all frequencies at appropriate grid points/wavelength, then demonstrate convergence and known reflection benchmarks.
- [ ] Validate discrete energy conservation and source normalization.
- [ ] Add convergence and closed-contour stress integration for the electrostatic field; track reaction on grounded enclosure.

## P2 — Exodus source-bounded reproduction

- [ ] Select patent figure and transcribe exact claim and relevant equations with citations.
- [ ] Implement its geometry accurately; use 3D when 2D does not preserve force dimensions.
- [ ] Benchmark field solution and compute forces on **whole device** plus environment.
- [ ] Add H0-versus-H1 prediction comparison with error and experimental control panels.

## P3 — nuclear and scalar-field hypotheses

- [ ] Replace the hardcoded isotope half-lives and their false implication of wave speed with traceable evaluated/predicted nuclear data and error labels.
- [ ] Define an explicit scalar-field Lagrangian/equation and coupling, with known-physics limit and falsifiable prediction.
- [ ] Keep novel modes and speculative properties distinctly labeled.

## P4 — scientific research dashboard

- [ ] Interactive parameter controls, metadata download, independent sources, error bars and publishable static figures.
- [ ] Independent critical review before merging physics-bearing work.

Methods: [Superpowers](https://github.com/obra/superpowers) (design, red-green tests, review), [Matt Pocock skills](https://github.com/mattpocock/skills) (domain-model grilling, decisions and glossary), and [Scientific Agent Skills](https://github.com/k-dense-ai/scientific-agent-skills) (hypothesis, units, experiment design, uncertainty and honest scientific visualization). These guide process, not physical truth.
