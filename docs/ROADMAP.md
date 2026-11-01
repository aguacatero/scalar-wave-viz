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

*Status (2026-11-01):* Active on dedicated branch `p2-patent-geometry-exodus-2026-10-25` under Draft [PR #11](https://github.com/aguacatero/scalar-wave-viz/pull/11) ([Issue #7](https://github.com/aguacatero/scalar-wave-viz/issues/7)). Checkboxes remain unchecked pending independent scientific acceptance. Independent ChatGPT scientific review R8 ([issuecomment-6564571034](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6564571034)) concluded `CHANGES REQUIRED — P2 R8 SCIENTIFIC BASELINE NOT ACCEPTED` (5 High, 1 Medium, 1 Low findings). R9 remediation: (1) expanded surrogate-to-article transfer scaling across $\ge 3$ axial lengths ($L_z \in [0.0254, 0.0508, 0.1016\text{ m}]$, 1, 2, 4 inches) via `compare_fig21_surrogate_to_declared_article` ($R^2 = 1.000000 > 0.99$, max residual $< 25\ \mu\text{N}$, $f_{\text{interior}} = -6.957\text{ N/m}$), designated $+7.22\text{ mN}$ end-cap relief as a single-grid empirical fit observation, and asserted inter-level per-body differences $\Delta F_k > 23.7\ \mu\text{N}$ in 3-level convergence study (P2-R8-F1); (2) expanded domain boundary clearance sensitivity calibration across $\ge 3$ multipliers ($1.0\times, 1.5\times, 2.0\times$) in `calibrate_domain_clearance_uncertainty_3d`, confirming monotonic decay of finite-difference boundary coupling ($7.05\text{ mN} \to 2.33\text{ mN}$), standardized nomenclature as boundary placement sensitivity estimate (P2-R8-F2); (3) documented dielectric susceptibility non-zero intercept ($|b|/\max(|F|) \approx 0.19$) from 3D field redistribution, recorded component closure table across mesh levels, and maintained fail-closed mechanical accounting (P2-R8-F3); (4) centralized gate strictly fails closed with `"NOT_RESOLVED_MISSING_AXIAL_GRID_DISCRETIZATION_EVIDENCE"` if axial evidence is omitted for verified states, and evaluates multi-body discretization uncertainty across all bodies (`max(body_errors)`) (P2-R8-F4); (5) preserved `None/null` for uncalibrated domain uncertainty, serialized JSON with `allow_nan=False`, and added strict CI/test semantic manifest assertions (P2-R8-F5); (6) added strict input validation to `compute_3d_patent_face_h1_quadrature` raising `ValueError` on empty/reversed spans and non-positive/non-finite grid steps (P2-R8-M1); (7) implemented integer round discovery setting `CURRENT_GOVERNING_REVIEW = "P2_R8_REMEDIATION"` (P2-R8-M2); and maintained full test suite (126 total tests passed). Awaiting independent ChatGPT R9 re-review.

## P3 — nuclear and scalar-field hypotheses

- [ ] Replace the hardcoded isotope half-lives and their false implication of wave speed with traceable evaluated/predicted nuclear data and error labels.
- [ ] Define an explicit scalar-field Lagrangian/equation and coupling, with known-physics limit and falsifiable prediction.
- [ ] Keep novel modes and speculative properties distinctly labeled.

## P4 — scientific research dashboard

- [ ] Interactive parameter controls, metadata download, independent sources, error bars and publishable static figures.
- [ ] Independent critical review before merging physics-bearing work.

Methods: [Superpowers](https://github.com/obra/superpowers) (design, red-green tests, review), [Matt Pocock skills](https://github.com/mattpocock/skills) (domain-model grilling, decisions and glossary), and [Scientific Agent Skills](https://github.com/k-dense-ai/scientific-agent-skills) (hypothesis, units, experiment design, uncertainty and honest scientific visualization). These guide process, not physical truth.
