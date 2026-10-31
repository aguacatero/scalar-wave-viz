# SCALAR WAVE VIZ — ChatGPT Independent Scientific Re-Review P2 R4 — CHANGES REQUIRED

**Repository:** `aguacatero/scalar-wave-viz` · **PR #11 / Issue #7**  
**Exact reviewed source HEAD:** `c3eb72e12dce497c0704a6688db02ea7d2823ae2`  
**Governing review:** [P2 R3](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6544610778)  
**Disposition:** **P2 R4 SCIENTIFIC BASELINE NOT ACCEPTED — CHANGES REQUIRED.**  
**Governance:** **MANUAL-ONLY / OPEN / DRAFT / UNMERGED.** No merge approval, no P3 kickoff authorization.

## Independently verified evidence

- Live PR #11 HEAD matches the cited R4 SHA and remains draft/open/unmerged.
- [GitHub Actions run 41212614599](https://github.com/aguacatero/scalar-wave-viz/actions/runs/41212614599) succeeded. Inspected job 124570592946 logs: **`Ran 115 tests in 99.561s` / `OK`**, and manifest provenance gate passed.
- Artifact metadata confirms ID `13047410750`, name `conventional-electrostatics-preview`, and digest `sha256:d791a1abc8d0b81f675f584c896c959873ae8fd7de29a6808dcb7eb2e704edc2`. ZIP contents were not independently downloaded.
- Verified P0 `electrostatics_baseline.py` blob SHA `97f65dfa25db7730323edd5e52c98b17371fdeaa` and that P0/P1 source files are absent from PR changed-file list.
- Examined exact-SHA evaluator, geometry, P2 tests, demo and live PR description; compared patent FIG.21 data in [US11511891B2](https://patents.google.com/patent/US11511891B2/en) with [Tajmar & Schreiber (2020)](https://doi.org/10.1016/j.elstat.2020.103477). This is a source-and-code scientific review, not an independent numerical solver rerun or laboratory validation.

## Blocking findings

### P2-R4-F1 — HIGH — 3D force refinement still changes geometry; no 3D observed-order or multi-body convergence

[exodus_hypothesis_evaluator.py L1804–1862](https://github.com/aguacatero/scalar-wave-viz/blob/c3eb72e12dce497c0704a6688db02ea7d2823ae2/exodus_hypothesis_evaluator.py#L1804-L1862), [L1466–1479](https://github.com/aguacatero/scalar-wave-viz/blob/c3eb72e12dce497c0704a6688db02ea7d2823ae2/exodus_hypothesis_evaluator.py#L1466-L1479), [tests L411–435](https://github.com/aguacatero/scalar-wave-viz/blob/c3eb72e12dce497c0704a6688db02ea7d2823ae2/tests/test_p2_exodus_patent.py#L411-L435), [L530–542](https://github.com/aguacatero/scalar-wave-viz/blob/c3eb72e12dce497c0704a6688db02ea7d2823ae2/tests/test_p2_exodus_patent.py#L530-L542).

The **single default 3D solve** has commensurate `dx=dy=1.27 mm, dz=2.54 mm`, an improvement in nominal feature dimensions. But `run_3d_mesh_convergence_study` still defaults to **2.0, 1.5, 1.2 mm** lateral spacing; rounding the 1.27 mm blade thickness makes actual widths 2.0, 1.5, 1.2 mm (ratios **1.575, 1.181, 0.945**), recreating the R3 geometry-vs-mesh confound. The 3D Richardson estimate is still forced to `p=1`, never estimates observed order, and extrapolates **blade force only**. The nine-blade 3D test examines only one nominally commensurate grid. Further, a 1.27 mm-wide tip represented by **one lateral cell** is geometrically aligned but does not, by that fact alone, resolve its near-corner field and stresses.

**Required:** Fixed-geometry refinement sequence with >=3 suitable 3D resolutions; report actual geometry (including pitch, thickness, gap, z extent), 3D blade/ground/dielectric/wall/net forces and H1 surface quantities at each level, observed order or explicit non-asymptotic status, contour and domain stability, and force-difference tolerances. Quantify uncertainty at the 237 µN experimental scale instead of treating a single exact 1.0000 width ratio as convergence.

### P2-R4-F2 — HIGH — The 23.7 µN discrimination gate does not use the declared uncertainty budget

[exodus_hypothesis_evaluator.py L1638–1681](https://github.com/aguacatero/scalar-wave-viz/blob/c3eb72e12dce497c0704a6688db02ea7d2823ae2/exodus_hypothesis_evaluator.py#L1638-L1681), [tests L504–528](https://github.com/aguacatero/scalar-wave-viz/blob/c3eb72e12dce497c0704a6688db02ea7d2823ae2/tests/test_p2_exodus_patent.py#L504-L528).

The `physical_scale_discrimination_status` predicate tests **only `abs(f_3d_net) < 23.7 µN` and relative closure <0.5%**. It does not evaluate or combine `mesh_force_discretization_uncertainty_n`, `domain_boundary_clearance_uncertainty_n`, or omitted-parameter uncertainty. Currently the mesh term is assigned `0.18 * abs(F_blade)` from a **2D estimate**, not an independently determined 3D force error; the clearance term is a **hard-coded 50 µN**, already > the 23.7 µN threshold, and model uncertainties are only a string. Therefore a future smaller net residual could be marked **RESOLVED** even with acknowledged errors larger than the signal-resolution limit. `finite_3d_is_conserved` also uses the looser **237 µN** threshold, yielding inconsistent flags in a future borderline case.

**Required:** Separate solver, closure, discretization, domain, and missing-parameter terms with documented estimation methods and same-geometry 3D evidence. Define and enforce an acceptance rule that checks a defensible combined/conservative bound, not just closure, and fail closed when unbounded. Add adversarial tests injecting small closure but excessive mesh/domain/model uncertainty. Current status **NOT RESOLVED** is appropriate.

### P2-R4-F3 — HIGH — Independent *2D* dielectric benchmark does not validate the actual 3D dielectric reaction

[exodus_hypothesis_evaluator.py L740–954](https://github.com/aguacatero/scalar-wave-viz/blob/c3eb72e12dce497c0704a6688db02ea7d2823ae2/exodus_hypothesis_evaluator.py#L740-L954), [L1610–1622](https://github.com/aguacatero/scalar-wave-viz/blob/c3eb72e12dce497c0704a6688db02ea7d2823ae2/exodus_hypothesis_evaluator.py#L1610-L1622), [tests L269–284](https://github.com/aguacatero/scalar-wave-viz/blob/c3eb72e12dce497c0704a6688db02ea7d2823ae2/tests/test_p2_exodus_patent.py#L269-L284).

The new `benchmark_analytic_planar_dielectric_slab_force` is a useful **limited, independent-observable 2D cross-check**: analytic -123.96 µN, virtual-work -109.14 µN, contour -111.54 µN at one setup. It does **not** provide an independently evaluated dielectric force for the 3D FIG.21 geometry. The operative 3D code still sets **`F_dielectric = F_article_contour - (F_blade + F_ground)`**, so `F_blade + F_ground + F_dielectric` is algebraically the article contour integral. The 3D whole-body force budget thus remains partly identity-based and lacks independently verified dielectric-interface traction or 3D fixed-voltage virtual work. The code honestly labels whole-body accounting `UNVERIFIED_PENDING_CONFORMING_INTERFACE_MESHING`; scientific gate cannot accept while that remains true.

**Required:** Independent 3D dielectric material/interface reaction via a justified constitutive stress and conforming interface integration or 3D virtual-work derivative with voltage-source work handled correctly; compare against contour difference under mesh refinement and dielectric-position perturbations. Retain **UNVERIFIED** and fail closed until verified.

## Additional findings

### P2-R4-M1 — MED — Active PR description claims 116 tests; actual CI and R4 handoff report 115

[docs/PR_DESCRIPTION.md L68–73](https://github.com/aguacatero/scalar-wave-viz/blob/c3eb72e12dce497c0704a6688db02ea7d2823ae2/docs/PR_DESCRIPTION.md#L68-L73) and [live PR body](https://github.com/aguacatero/scalar-wave-viz/pull/11) say **116 (35+37+44)**. CI job logs unequivocally say **115**, matching handoff's **35+37+43**. The current metadata regression test [L763–794](https://github.com/aguacatero/scalar-wave-viz/blob/c3eb72e12dce497c0704a6688db02ea7d2823ae2/tests/test_p2_exodus_patent.py#L763-L794) verifies repository text patterns, not live GitHub metadata or the claimed count. **Correct the PR body/source document and validate count against CI results; avoid asserting a remote PR sync from a local-file-only test.**

### P2-R4-M2 — MED — Observed 2D order is useful, but a single triplet does not confirm the singularity is the governing convergence mechanism

[exodus_hypothesis_evaluator.py L1070–1126](https://github.com/aguacatero/scalar-wave-viz/blob/c3eb72e12dce497c0704a6688db02ea7d2823ae2/exodus_hypothesis_evaluator.py#L1070-L1126), [docs/PR_DESCRIPTION.md L57–62](https://github.com/aguacatero/scalar-wave-viz/blob/c3eb72e12dce497c0704a6688db02ea7d2823ae2/docs/PR_DESCRIPTION.md#L57-L62). The measured 2D `p_obs ~0.368` and tip-field slopes are **consistent with**, not proof of, an `r^-1/3` local corner singularity dominating global force convergence. A single triplet without a stable refinement window, tip-radius sensitivity, or alternate contour tests does not demonstrate an asymptotic error law. Change "confirming that convergence is governed" to "consistent with a corner-singularity-influenced convergence rate"; keep 2D observed-order extrapolation expressly provisional.

### P2-R4-M3 — MED — Figure hard-codes a result dependent on live model parameters

[examples/exodus_patent_demo.py L137–155](https://github.com/aguacatero/scalar-wave-viz/blob/c3eb72e12dce497c0704a6688db02ea7d2823ae2/examples/exodus_patent_demo.py#L137-L155) prints **"Net (683 µN)"** as a constant label although the plotted force is calculated from `f3d.finite_3d_net_system_force_x_n`. A user parameter change can leave a stale force label even while the bar value changes. Build the label from the same computed field and add a regression with changed parameters.

## Disposition / R5 pickup

**Positive progress:** source/patent parameter separation, corrected Tajmar–Schreiber apparatus description, directly integrated 3D enclosure wall traction, one nominally commensurate 9-blade solution, explicit fail-closed physical-scale status, and a new 2D dielectric virtual-work cross-check. These are meaningful engineering improvements, but the three blocking issues above preclude **P2 scientific baseline acceptance**.

For R5, provide finding→patch→adversarial-test evidence; source-head-pinned runs and force tables for all 3D bodies/H1 quantities at several fixed-geometry meshes; independently verified 3D dielectric reaction; uncertainty-bound gating; corrected PR/docs/figure metadata; successful CI and artifact provenance. Do not merge or authorize P3 based solely on passing tests.

**Final verdict: CHANGES REQUIRED — P2 R4 NOT ACCEPTED. MANUAL-ONLY, PR #11 stays DRAFT/OPEN/UNMERGED.**