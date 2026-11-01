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

*Status (2026-11-01):* Active on dedicated branch `p2-patent-geometry-exodus-2026-10-25` under Draft [PR #11](https://github.com/aguacatero/scalar-wave-viz/pull/11) ([Issue #7](https://github.com/aguacatero/scalar-wave-viz/issues/7)). Checkboxes remain unchecked pending independent scientific acceptance. Independent ChatGPT scientific review R7 ([issuecomment-6559262041](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6559262041)) concluded `CHANGES REQUIRED — P2 R7 SCIENTIFIC BASELINE NOT ACCEPTED` (4 High, 1 Medium, 1 Low findings). R8 remediation: (1) formally distinguished shortened surrogate (`FIG21_MODEL_VARIANT_SHORTENED_AXIAL_SURROGATE_25MM`) from declared test article (`FIG21_MODEL_VARIANT_DECLARED_ARTICLE_101MM`), validated transfer scaling via `compare_fig21_surrogate_to_declared_article` ($4.000\times$ length ratio, $-6.957\text{ N/m}$ interior density, isolating $+7.22\text{ mN}$ end-cap relief, $< 1.1\%$), recorded level-by-level per-body bounds in 3-level convergence test, and documented ground sheet thinning ratios ($5.08, 2.54, 1.693$); (2) expanded domain boundary clearance calibration across all 3 dimensions ($x, y, z$) in `calibrate_domain_clearance_uncertainty_3d`, integrated directly into production solves and gate, strictly separated physical wall reaction traction from boundary placement sensitivity, and verified that altering sensitivity changes the production gate RSS; (3) verified FIG. 21 potting dielectric linearity across $\varepsilon_r \in [1.5, 2.5, 3.8, 5.0]$ ($R^2 = 0.9846 > 0.98$), tracked multi-resolution interface-to-contour agreement, documented Korteweg-Helmholtz limiting conventions, and maintained fail-closed unverified gate; (4) distinguished observed finite differences from proven bounds, combined lateral and axial discretization uncertainties ($u_{\text{mesh,total}} = \sqrt{u_{xy}^2 + u_z^2}$) in production gate, and tracked multi-body convergence metrics; (5) added strict bounds checking to `compute_3d_patent_face_h1_quadrature` raising `ValueError` on out-of-bounds offsets, verified non-zero offset sensitivity on non-uniform gradient fields, and bounded precision claims to $< 10^{-9}$; (6) implemented automated review round discovery `discover_governing_review_round()` setting `CURRENT_GOVERNING_REVIEW = "P2_R7_REMEDIATION"`; and expanded test suite to 54 P2 tests (126 total tests passed). Awaiting independent ChatGPT R8 re-review.

## P3 — nuclear and scalar-field hypotheses

- [ ] Replace the hardcoded isotope half-lives and their false implication of wave speed with traceable evaluated/predicted nuclear data and error labels.
- [ ] Define an explicit scalar-field Lagrangian/equation and coupling, with known-physics limit and falsifiable prediction.
- [ ] Keep novel modes and speculative properties distinctly labeled.

## P4 — scientific research dashboard

- [ ] Interactive parameter controls, metadata download, independent sources, error bars and publishable static figures.
- [ ] Independent critical review before merging physics-bearing work.

Methods: [Superpowers](https://github.com/obra/superpowers) (design, red-green tests, review), [Matt Pocock skills](https://github.com/mattpocock/skills) (domain-model grilling, decisions and glossary), and [Scientific Agent Skills](https://github.com/k-dense-ai/scientific-agent-skills) (hypothesis, units, experiment design, uncertainty and honest scientific visualization). These guide process, not physical truth.
