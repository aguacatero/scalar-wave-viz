# SCALAR WAVE VIZ — ChatGPT Independent Scientific Re-Review P2 R7 — CHANGES REQUIRED

**Repository:** `aguacatero/scalar-wave-viz` · **PR #11 / Issue #7**  
**Exact reviewed source HEAD:** `404e29ef914c0e141deb055ed82f6bf33d1af544`  
**Governing review:** [P2 R6](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6553125965)  
**Scientific disposition:** **CHANGES REQUIRED — P2 R7 SCIENTIFIC BASELINE NOT ACCEPTED.**  
**Governance:** **MANUAL-ONLY / OPEN / DRAFT / UNMERGED.** No merge authorization or P3 kickoff.

## Independently verified

- Live PR #11 is open/draft/unmerged at the exact SHA above.
- Inspected exact-SHA evaluator, geometry configuration, test suite, R7 handoff, PR description and governing R6 findings. Cross-checked patent identity against [US11511891B2](https://patents.google.com/patent/US11511891B2/en).
- [CI run 41275682251](https://github.com/aguacatero/scalar-wave-viz/actions/runs/41275682251), job `124757272055`: logs report **Ran 124 tests in 366.106s / OK** and **Manifest provenance gate passed**. CI tested synthetic PR merge `0a420a3ccddb2646b7f747828f23cf8fc387eee5`, with source HEAD correctly recorded separately.
- Artifact `conventional-electrostatics-preview`, ID `13071571906`, metadata digest `sha256:3f689d33f1ed3497942009d6de7688d0662baf9590a8b34365b09dbf60a9c365` verified; ZIP contents were **not** independently inspected.
- P0 `electrostatics_baseline.py` Git blob independently confirmed as `97f65dfa25db7730323edd5e52c98b17371fdeaa`. P1 source/test blobs `scalar_wave_3d.py`, `electrostatics_numerics.py`, `tests/test_p1_wave_3d.py`, `tests/test_p1_numerics.py` independently match base SHA `8e1fdb32655d073002ae5a794b08e48f19a78a0f`.
- Review is a **source/scientific-method and CI-log audit**, not an independently rerun 3D simulation or physical thrust experiment.

## R6 remediation disposition

| Previous finding | R7 determination |
|---|---|
| R6-F1 full 3D / FIG.21 convergence | **PARTIAL, BLOCKING:** `refine_z=True` default and three refinement levels now exist; the FIG.21 convergence test uses only a **25.4 mm** blade, not the declared **101.6 mm** article, and reports no predeclared body-by-body convergence bounds. Ground thickness is now reported truthfully, but is still geometrically under-resolved. |
| R6-F2 boundary/model uncertainty | **PARTIAL, BLOCKING:** paired-clearance calibration helper and `None` for missing model uncertainty added, but the **main solver and production gate still receive wall reaction** as `u_domain`; helper is not integrated. |
| R6-F3 allowlist and validation | **RESOLVED for the identified bypass:** strict verified-state allowlist; NaN/negative/invalid-state adversarial tests, with present production states failing closed. |
| R6-F4 FIG.21 dielectric reaction | **PARTIAL, BLOCKING:** discrepancy metric exists, but no independent FIG.21 virtual-work closure or quantified per-mesh/per-permittivity acceptance; status remains honestly unverified. |
| R6-M1 direct 3D H1 test | **DIRECT SYNTHETIC BENCHMARK RESOLVED; PHYSICAL SURFACE LIMIT PROVISIONAL:** direct uniform and nonuniform 3D arrays now drive quadrature, but actual solved material-side near-face limit is not validated. |
| R6-M2 manifest review | **CORRECT CURRENT VALUE:** CI manifest contains `P2_R6_REMEDIATION`; implementation remains a manually maintained module constant, not metadata-derived automatic selection. |

## Blocking findings

### P2-R7-F1 — HIGH — FIG.21 convergence evidence evaluates a one-quarter-length surrogate without validating transfer to the declared article

**Source:** [FIG.21 convergence test, lines 541–587](https://github.com/aguacatero/scalar-wave-viz/blob/404e29ef914c0e141deb055ed82f6bf33d1af544/tests/test_p2_exodus_patent.py#L541-L587); [physical model defaults](https://github.com/aguacatero/scalar-wave-viz/blob/404e29ef914c0e141deb055ed82f6bf33d1af544/exodus_patent_geometry.py#L45-L85).

Test configuration explicitly overrides `blade_length_m=0.0254` (1 inch) instead of the declared 4-inch / 0.1016 m article. It also reduces x/y/z enclosure clearance. The three-level fractional-order estimate therefore describes a **different constrained surrogate**, not necessarily the 4-inch FIG.21 setup. Tests only enforce force signs/ranges, blade relative changes (<25%, <10%), and a single blade-derived order (`0.5 < p < 1`); they do not establish convergence of ground/dielectric/wall/net/H1 quantities. Moreover the actual 0.25 mm ground sheet remains one cell thick at each grid (ratios 5.08, 2.54, 1.693), so the physical geometry changes under refinement.

**Required:** clearly label and validate the shortened surrogate against the full 101.6 mm article (or run full-length convergence); quantify end-fringing and boundary effects; resolve or systematically extrapolate the thin ground sheet; publish level-by-level numerical values and predeclared absolute/per-body convergence and H1 tolerances. Do not describe one 3-point blade fit as stable multi-body asymptotic convergence.

### P2-R7-F2 — HIGH — Domain-calibration helper is disconnected from actual solver/decision budget

**Source:** [solver uncertainty assignment, lines 2196–2233](https://github.com/aguacatero/scalar-wave-viz/blob/404e29ef914c0e141deb055ed82f6bf33d1af544/exodus_hypothesis_evaluator.py#L2196-L2233); [returned 'calibrated' field, lines 2284–2294](https://github.com/aguacatero/scalar-wave-viz/blob/404e29ef914c0e141deb055ed82f6bf33d1af544/exodus_hypothesis_evaluator.py#L2284-L2294); [paired calibration helper, lines 2331–2372](https://github.com/aguacatero/scalar-wave-viz/blob/404e29ef914c0e141deb055ed82f6bf33d1af544/exodus_hypothesis_evaluator.py#L2331-L2372).

`solve_exodus_electrostatics_3d` still assigns `clearance_uncert_n = abs(f_3d_enclosure_direct)`, passes that to `evaluate_physical_scale_discrimination_gate`, and sets `calibrated_domain_clearance_uncertainty_n` to the **same uncalibrated wall-force proxy**. The paired clearance helper is only called by its dedicated test, not in the production solve/refinement path. Thus the exported calibration field is misleading and R6-F2 is not actually remedied in the decision budget. In addition, `clearance_multipliers[0]` is reported but not applied to the nominal solve, while the helper varies x/y and omits z clearance.

**Required:** compute matched-grid, same-body boundary-placement sensitivity (including z and FIG.21), propagate the measured quantity and provenance to all solver/result/manifest/budget outputs, and keep the physical wall reaction as a separate ledger entry. Test that changing the calibrated sensitivity actually changes the production gate input/result.

### P2-R7-F3 — HIGH — FIG.21 dielectric mechanical closure is still unverified, and its new regression does not test quantitative agreement

**Source:** [dielectric traction and contour construction, lines 2074–2118](https://github.com/aguacatero/scalar-wave-viz/blob/404e29ef914c0e141deb055ed82f6bf33d1af544/exodus_hypothesis_evaluator.py#L2074-L2118); [permittivity test, lines 1355–1387](https://github.com/aguacatero/scalar-wave-viz/blob/404e29ef914c0e141deb055ed82f6bf33d1af544/tests/test_p2_exodus_patent.py#L1355-L1387).

The test solves only shortened 25.4 mm FIG.21 surrogates at epsilon_r=2.0 and 5.0 on **one grid**. It asserts only that one interface-traction value is greater than the other, that two discrepancy fields are non-null, and that status remains unverified. It does **not** test proportionality to `(epsilon_r-1)`, the claimed 20–35% discrepancy range, a mesh sequence at each permittivity, or independent FIG.21 dielectric virtual work. A 20–35% interface/contour difference is not evidence of quantitative whole-body closure; the method continues to return `finite_3d_dielectric_virtual_work_x_n=None` and `UNVERIFIED_PENDING_CONFORMING_INTERFACE_MESHING`.

**Required:** numerical tables at nominal epsilon_r=3.8 plus independent epsilon sweeps, same-geometry multi-resolution interface/contour/virtual-work comparisons, explicit material-side limiting-field conventions and bounded closure residuals before promoting the whole-body state.

### P2-R7-F4 — HIGH — Claimed mesh 'uncertainty bounds' are not validated whole-body error bounds

**Source:** [refinement/extrapolation, lines 2437–2623](https://github.com/aguacatero/scalar-wave-viz/blob/404e29ef914c0e141deb055ed82f6bf33d1af544/exodus_hypothesis_evaluator.py#L2437-L2623); [z-only study, lines 2627–2659](https://github.com/aguacatero/scalar-wave-viz/blob/404e29ef914c0e141deb055ed82f6bf33d1af544/exodus_hypothesis_evaluator.py#L2627-L2659).

`p_obs`, Richardson extrapolation, and the mesh term passed to the gate are built from **blade force alone**, not from independently converged forces for every body, net momentum balance, and H1 surfaces. The isolated z-grid value (handoff reports ~499.4 microN) is computed with only **two z levels and an assumed p=1**, making it an order-dependent estimate, **not a demonstrated rigorous bound**. `z_mesh_discretization_uncertainty_n` is populated only in the separate z study; it is not separately propagated into the standard production 5-part gate. No multi-body 23.7 microN discrimination certificate is presented.

**Required:** distinguish observed finite differences and assumed-order estimates from justified numerical upper bounds; construct component-by-component convergence/error budgets at physically fixed geometry, include axial and boundary sensitivity in the same decision evidence, and keep the status unresolved until validated.

## Additional findings

### P2-R7-M1 — MED — Synthetic 3D H1 quadrature benchmark is valid but does not establish a material-side face-limit result

**Source:** [quadrature implementation, lines 1625–1690](https://github.com/aguacatero/scalar-wave-viz/blob/404e29ef914c0e141deb055ed82f6bf33d1af544/exodus_hypothesis_evaluator.py#L1625-L1690); [benchmark test, lines 1000–1110](https://github.com/aguacatero/scalar-wave-viz/blob/404e29ef914c0e141deb055ed82f6bf33d1af544/tests/test_p2_exodus_patent.py#L1000-L1110).

Credit for driving the actual extracted 3D quadrature with synthetic uniform/nonuniform fields and checking Cauchy-Schwarz. However, the offset=1 versus 2 assertion uses a **uniform x-invariant field**, which is guaranteed to show no offset sensitivity and does not probe real near-electrode bias. The routine clamps out-of-bounds sample indices rather than rejecting invalid sampling. No convergence of actual solved H1 forces against physical face offset or dielectric-side limits is established. Keep the published force values provisional. Also do not claim a global `1e-12` force-error guarantee from tests asserting 9 decimal places.

### P2-R7-M2 — LOW — Governing-review value corrected, but is not automatically metadata-derived

**Source:** [module constant](https://github.com/aguacatero/scalar-wave-viz/blob/404e29ef914c0e141deb055ed82f6bf33d1af544/exodus_hypothesis_evaluator.py#L1600-L1607); [manifest generator default](https://github.com/aguacatero/scalar-wave-viz/blob/404e29ef914c0e141deb055ed82f6bf33d1af544/exodus_hypothesis_evaluator.py#L2897-L2905). Current `P2_R6_REMEDIATION` is correct in CI, but it is a manually updated constant, not automatically derived from version-controlled review metadata. A handoff/manifest consistency check would prevent recurrence.

## Decision and next pickup

**P2 R7: CHANGES REQUIRED; scientific baseline NOT ACCEPTED.** The strict verified-status allowlist and explicit unbounded model parameters are meaningful safeguards. **Passing 124 tests establishes regression conformance, not validated 3D physical closure or thrust discrimination.** Preserve the current fail-closed `NOT_RESOLVED_AT_CURRENT_3D_GRID_RESOLUTION` / unverified accounting classifications. Do not merge PR #11, claim physical propulsion validation, or begin P3. Remediate the HIGH findings with adversarial regressions and traceable level-by-level numerical evidence, then submit a fresh exact-SHA R8 handoff.