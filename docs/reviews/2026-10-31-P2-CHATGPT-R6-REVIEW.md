# SCALAR WAVE VIZ — ChatGPT Independent Scientific Re-Review P2 R6 — CHANGES REQUIRED

**Repository:** `aguacatero/scalar-wave-viz` · **PR #11 / Issue #7**  
**Exact reviewed source HEAD:** `476b4200ba414221a38441ba690a83d2bd3716e0`  
**Governing review:** [P2 R5](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6548482245)  
**Scientific disposition:** **CHANGES REQUIRED — P2 R6 SCIENTIFIC BASELINE NOT ACCEPTED.**  
**Governance:** **MANUAL-ONLY / OPEN / DRAFT / UNMERGED.** No merge authorization or P3 kickoff.

## Independently verified evidence

- Confirmed live PR #11 is open/draft/unmerged at the stated head SHA.
- Inspected exact-SHA evaluator, geometry configuration, R6 tests, remediation plan/handoff, model contract and PR description. Cross-checked Eq. (11) against [US11511891B2](https://patents.google.com/patent/US11511891B2/en).
- [CI run 41240666547](https://github.com/aguacatero/scalar-wave-viz/actions/runs/41240666547), job `124653704450`: inspected job logs; **`Ran 122 tests in 198.884s` / `OK`**, and manifest provenance gate passed. CI tested synthetic PR merge `64e5d7c189017f94d2a547e1c689e3a7d480ff7a` and correctly recorded source HEAD separately.
- Artifact `conventional-electrostatics-preview`, ID `13057775525`, 1,065,537 bytes, digest `sha256:1a42ef756805ddad0692b0e6ab0e1eb12de5676d4cf152ee3f71eaaebb43a556` confirmed from metadata; **artifact ZIP contents not independently inspected**.
- P0 `electrostatics_baseline.py` blob independently confirmed as `97f65dfa25db7730323edd5e52c98b17371fdeaa`. P1 files do not appear in PR changed-file list and P1 regressions pass.
- This was an independent **source/scientific-method and CI-log audit**, not an independently rerun numerical solver or physical experiment.

## R5 remediation disposition

| R5 item | R6 determination |
| --- | --- |
| **R5-F1** 3D convergence | **PARTIAL / STILL BLOCKING:** z-refinement capability added, but FIG.21 study does not use it; ground thickness claim materially conflicts with source; no robust body-by-body convergence criteria. |
| **R5-F2** discrimination gate | **PARTIAL / STILL BLOCKING:** centralized function and post-refinement call implemented; clearance/model uncertainty remain uncalibrated, and gate has a status-validation vulnerability. |
| **R5-F3** dielectric accounting | **PARTIAL / STILL BLOCKING:** provisional label, `None` virtual-work field and discrepancy metric are appropriate; actual FIG.21 dielectric reaction/whole-body closure are not verified. |
| **R5-F4** H1 face quantity | **SUBSTANTIALLY IMPLEMENTED / VALIDATION INCOMPLETE:** literal Eq. (11) now uses 3D near-face samples and distinguishes half-factor and mean plug-in, but a direct 3D face-quadrature analytic regression and surface-limit validation are missing. |
| **R5-M1** dynamic plot labels | **RESOLVED:** shared formatter invoked by the test; source uses a single shared formatting path. |

## Blocking findings

### P2-R6-F1 — HIGH — Reported full-3D/FIG.21 convergence and ground-thickness fidelity do not match code or tests

**Sources:** [3D grid discretization](https://github.com/aguacatero/scalar-wave-viz/blob/476b4200ba414221a38441ba690a83d2bd3716e0/exodus_hypothesis_evaluator.py#L1709-L1743), [3D refinement defaults](https://github.com/aguacatero/scalar-wave-viz/blob/476b4200ba414221a38441ba690a83d2bd3716e0/exodus_hypothesis_evaluator.py#L2238-L2275), [z-refinement method](https://github.com/aguacatero/scalar-wave-viz/blob/476b4200ba414221a38441ba690a83d2bd3716e0/exodus_hypothesis_evaluator.py#L2427-L2452), [tests](https://github.com/aguacatero/scalar-wave-viz/blob/476b4200ba414221a38441ba690a83d2bd3716e0/tests/test_p2_exodus_patent.py#L433-L541), [geometry configuration](https://github.com/aguacatero/scalar-wave-viz/blob/476b4200ba414221a38441ba690a83d2bd3716e0/exodus_patent_geometry.py#L49-L65).

1. `run_3d_mesh_convergence_study(..., refine_z=False)` defaults to **fixed dz**. The FIG.21 test calls it at subdivisions `(1, 2)` **without** `refine_z=True`, so the supposed multilevel *full 3D* nine-blade study refines x/y but **not z**. Only the separate single-blade two-level smoke test sets `refine_z=True`.
2. The geometry source retains `ground_plane_thickness_m=0.00025` (**0.25 mm**), and `n_ground_th=max(1, round(T2/dx))`. At dx=1.27, 0.635 and 0.4233 mm, the actual 1-cell ground thickness differs from the model target by factors **5.08, 2.54, 1.69**, respectively. Yet the R6 handoff/PR description claim `T_gnd=1.27 mm` and ratio **1.0000**. The test only checks ratio `>=1.0`, not equality. Do not silently replace an *unsourced* 0.25 mm target with a 1.27 mm value to make the geometry look commensurate.
3. FIG.21 tests assert sign, nonzero quantities and blade force change below 35%, not predeclared **per-body** numerical tolerances for blade, ground, dielectric, wall, net and literal H1. The two-level FIG.21 run cannot establish observed order or extrapolation stability for those quantities.
4. The `u_mesh,z=0.05 µN` claim is unsupported by an independently exposed/calculated axial uncertainty in the solver. The axial regression checks relative force change `<0.05` (5%), which is **not 0.05 µN**. Two levels with assumed order p=1 cannot establish a rigorous bound by themselves.

**Required:** use 3+ controlled x/y/z refinement levels on **FIG.21** at fixed intended geometry; reconcile the sourced/unsourced T2 dimension; show numerical tables, per-body and H1 changes, observed-order stability, and predeclared tolerances. Derive and store the z-bound from actual force differences with explicit assumptions; do not claim a numerical bound unsupported by code/evidence.

### P2-R6-F2 — HIGH — Clearance and missing-parameter terms are still not empirically/numerically calibrated uncertainty bounds

**Sources:** [uncertainty assignment](https://github.com/aguacatero/scalar-wave-viz/blob/476b4200ba414221a38441ba690a83d2bd3716e0/exodus_hypothesis_evaluator.py#L2037-L2068), [clearance-sweep functions](https://github.com/aguacatero/scalar-wave-viz/blob/476b4200ba414221a38441ba690a83d2bd3716e0/exodus_hypothesis_evaluator.py#L2174-L2237), [refined gate call](https://github.com/aguacatero/scalar-wave-viz/blob/476b4200ba414221a38441ba690a83d2bd3716e0/exodus_hypothesis_evaluator.py#L2377-L2424).

- `domain_boundary_clearance_uncertainty_n = abs(f_3d_enclosure_direct)` measures the **force actually exerted on the enclosure wall**, not the **sensitivity of the computed force to boundary placement**. The existing x/y/z clearance sweeps are separate and are not used to obtain a bound from matched-grid, paired-clearance force differences.
- `missing_parameter_model_uncertainty_n=5.0e-5` N (**50 µN**) remains hard-coded, without fillet-radius, epoxy property, enclosure, lead-wire or other declared parameter sweeps. The `missing_parameter_model_is_bounded=False` flag correctly fails closed, but the numeric 50 µN must not be presented as measured calibration.
- The post-refinement gate now correctly executes, but it receives a **blade-only** Richardson difference, reused for every refinement level; this is not a convergence bound on the **whole multi-body mechanical balance**. Two-level fallback assumes order p=1.

**Required:** calibrate domain-placement uncertainty from paired **same-body, same-grid** clearance sweeps; separate physical wall reaction from domain truncation uncertainty; report unbounded parameter ranges without pseudo-quantified precision; use multi-body 3D convergence evidence in the decision budget.

### P2-R6-F3 — HIGH — Production gate can accept a mechanically **UNVERIFIED** whole-body status

**Sources:** [gate predicate](https://github.com/aguacatero/scalar-wave-viz/blob/476b4200ba414221a38441ba690a83d2bd3716e0/exodus_hypothesis_evaluator.py#L1599-L1677), [actual vacuum status](https://github.com/aguacatero/scalar-wave-viz/blob/476b4200ba414221a38441ba690a83d2bd3716e0/exodus_hypothesis_evaluator.py#L2056-L2086).

The predicate uses only `not whole_body_status.startswith("UNVERIFIED")`. But the actual vacuum result state is `VACUUM_NO_DIELECTRIC_UNVERIFIED_PENDING_CONVERGENCE`, which **does not start with** `UNVERIFIED`. With otherwise small synthetic bounds and `missing_parameter_model_is_bounded=True`, the production gate can return `RESOLVED_CONSERVED_WITHIN_DISCRIMINATING_THRESHOLD` for that **explicitly unverified** state. The test suite only injects a status beginning with `UNVERIFIED`.

**Required:** define an allowlist/enum of explicitly verified whole-body states (not a prefix-based denial test), reject unknown/empty/nonfinite/negative uncertainty inputs, and add adversarial positive/negative tests using the exact current vacuum status string plus all actual dielectric states.

### P2-R6-F4 — HIGH — FIG.21 dielectric mechanical closure remains unverified and is not shown to converge

**Sources:** [dielectric force construction](https://github.com/aguacatero/scalar-wave-viz/blob/476b4200ba414221a38441ba690a83d2bd3716e0/exodus_hypothesis_evaluator.py#L1916-L1946), [status and return fields](https://github.com/aguacatero/scalar-wave-viz/blob/476b4200ba414221a38441ba690a83d2bd3716e0/exodus_hypothesis_evaluator.py#L2056-L2172), [FIG.21 tests](https://github.com/aguacatero/scalar-wave-viz/blob/476b4200ba414221a38441ba690a83d2bd3716e0/tests/test_p2_exodus_patent.py#L516-L540), [dielectric test](https://github.com/aguacatero/scalar-wave-viz/blob/476b4200ba414221a38441ba690a83d2bd3716e0/tests/test_p2_exodus_patent.py#L590-L611).

The actual nine-blade model computes material reaction from centered `E²∂ε_r/∂x` on a Cartesian staircased dielectric boundary, with no independent virtual-work result (`None`), and reports `UNVERIFIED_PENDING_CONFORMING_INTERFACE_MESHING`. This provisional admission is scientifically appropriate; however, the new interface/contour relative-discrepancy field is only asserted to exist/be nonzero, not bounded by an acceptance criterion or shown to converge across FIG.21 meshes/permittivities. The slab benchmark continues to permit a 35% interface/contour discrepancy, and does not independently validate FIG.21 dielectric force.

**Required:** carry out matched FIG.21 virtual-work/interface/contour comparisons with controlled mesh and dielectric location/permittivity studies, state constitutive/traction assumptions, and require quantitative independent whole-body closure before changing the status to verified.

## Additional findings

### P2-R6-M1 — MED — Claimed uniform-field validation does not exercise the new 3D H1 quadrature

[H1 samples and integrals](https://github.com/aguacatero/scalar-wave-viz/blob/476b4200ba414221a38441ba690a83d2bd3716e0/exodus_hypothesis_evaluator.py#L1995-L2040) vs [test](https://github.com/aguacatero/scalar-wave-viz/blob/476b4200ba414221a38441ba690a83d2bd3716e0/tests/test_p2_exodus_patent.py#L877-L894).

The test named `test_true_3d_patent_face_h1_uniform_field_analytic_benchmark` calls `benchmark_analytic_parallel_plate_maxwell_stress`, an **independent analytical/2D benchmark**, and then inspects proof-obligation notes. It does **not** drive or verify the new 3D H1 near-face numerical quadrature on a known uniform field. The actual 3D code samples one cell away from each electrode and uses centered bulk gradients rather than an independently validated material-side surface limiting field. Keep the H1 force numbers provisional; add direct uniform/nonuniform analytic 3D face sample tests, controlled face offset/mesh sensitivity, proper dielectric-side treatment, and a full surface normal/area audit.

### P2-R6-M2 — MED — Generated manifest still identifies an obsolete governing review

[Manifest generator](https://github.com/aguacatero/scalar-wave-viz/blob/476b4200ba414221a38441ba690a83d2bd3716e0/exodus_hypothesis_evaluator.py#L2705-L2723) hard-codes `"governing_review": "P2_R4_REMEDIATION"`. I confirmed this exact value in successful R6 CI output; the active governing review is **P2 R5** and the new candidate is **R6**. Provenance SHA checks pass, but do not validate this stale review metadata. Derive this consistently from version-controlled review metadata and add a regression.

## Positive progress / decision

Confirmed **122/122 passing tests**, source/CI provenance, intact P0 blob, draft governance, added z-refinement capability, post-refinement re-evaluation of the real production gate, explicit fail-closed missing-parameter flag, honest provisional dielectric naming and optional virtual work, actual 3D near-face H1 integration (not prior six-box-face proxy), and shared plot formatter.

Nevertheless **no target-scale H0/H1 discrimination** or **verified FIG.21 whole-body 3D mechanical closure** has been established. Source/extrapolation claims in R6 materially overstate the implemented convergence and input uncertainty. Address F1–F4 before any P2 scientific baseline sign-off; close M1–M2 in the same remediation.

**FINAL P2 R6 VERDICT: CHANGES REQUIRED — P2 SCIENTIFIC BASELINE NOT ACCEPTED. KEEP PR #11 DRAFT/OPEN/UNMERGED; MANUAL-ONLY; NO MERGE OR P3 KICKOFF.**