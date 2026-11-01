# SCALAR WAVE VIZ — ChatGPT Independent Scientific Re-Review P2 R5 — CHANGES REQUIRED

**Repository:** `aguacatero/scalar-wave-viz` · **PR #11 / Issue #7**  
**Exact reviewed source HEAD:** `a47f551ff32a53fdfa092b531edd9a7c4490fd1f`  
**Governing review:** [P2 R4](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6548110642)  
**Scientific disposition:** **CHANGES REQUIRED — P2 R5 SCIENTIFIC BASELINE NOT ACCEPTED.**  
**Governance:** **MANUAL-ONLY / OPEN / DRAFT / UNMERGED.** No merge approval or P3 authorization.

## Independent evidence verification

- GitHub PR HEAD is exactly `a47f551ff32a53fdfa092b531edd9a7c4490fd1f`; live PR is still draft, open and unmerged.
- [GitHub Actions run 41236495854](https://github.com/aguacatero/scalar-wave-viz/actions/runs/41236495854), job `124641274311`: downloaded and inspected job logs, **`Ran 118 tests in 153.821s` / `OK`**; provenance gate explicitly passed. CI used tested synthetic merge `cad466aec31252f3b32114c6da6b2185e3b8327f` and recorded source HEAD separately.
- Artifact `conventional-electrostatics-preview` ID `13056440606`, 1,065,638 bytes, metadata digest `sha256:59c5a1f6ad5f3b0b85c986aad4ef20aacb36e217b716e2c416c315ab2015307c`, associated with source HEAD. **Artifact ZIP contents not independently inspected.**
- Source HEAD's P0 `electrostatics_baseline.py` blob matches `97f65dfa25db7730323edd5e52c98b17371fdeaa`; P1 sources are absent from the PR changed-file list, and the 37 P1 tests passed.
- Inspected exact-SHA evaluator, R5 P2 tests, geometry/manifest logic, plot, handoff and version-controlled PR description; compared the scope with [Issue #7](https://github.com/aguacatero/scalar-wave-viz/issues/7) and the [primary patent](https://patents.google.com/patent/US11511891B2/en). This is an independent code/scientific-method review, **not an independently rerun full solver or a physical experiment.**

## R4 finding disposition

| Governing finding | R5 disposition |
| --- | --- |
| R4-F1 HIGH: 3D refinement | **PARTIAL.** Commensurate lateral levels and recorded quantities are real improvements; 3D force convergence, full geometry fidelity and FIG.21 multilevel validation remain unproven. |
| R4-F2 HIGH: uncertainty gate | **PARTIAL.** Five terms and RSS are now checked in the initial gate, but several terms are ad hoc, and the post-refinement budget is not fed through the production gate. |
| R4-F3 HIGH: 3D dielectric | **PARTIAL.** Independent 3D benchmark and constitutive interface estimate added; the FIG.21 reaction and whole-body closure are still explicitly unverified. |
| R4-M1 MED: 116/115 test mismatch | **RESOLVED for current HEAD.** PR description, handoff and actual CI all say 118 tests. |
| R4-M2 MED: corner singularity language | **LARGELY RESOLVED.** Phrasing now says “consistent with”; provisional labels added. |
| R4-M3 MED: static plot label | **CODE FIXED.** Plot labels use live fields, though its new regression only reconstructs the format strings rather than invoking the chart. |

## Blocking findings

### P2-R5-F1 — HIGH — Fixed-geometry *lateral* refinement is not validated full 3D patent-article force convergence

Sources: [3D grid and masks](https://github.com/aguacatero/scalar-wave-viz/blob/a47f551ff32a53fdfa092b531edd9a7c4490fd1f/exodus_hypothesis_evaluator.py#L1616-L1686), [refinement routine](https://github.com/aguacatero/scalar-wave-viz/blob/a47f551ff32a53fdfa092b531edd9a7c4490fd1f/exodus_hypothesis_evaluator.py#L2097-L2254), [test](https://github.com/aguacatero/scalar-wave-viz/blob/a47f551ff32a53fdfa092b531edd9a7c4490fd1f/tests/test_p2_exodus_patent.py#L427-L463), [nine-blade test](https://github.com/aguacatero/scalar-wave-viz/blob/a47f551ff32a53fdfa092b531edd9a7c4490fd1f/tests/test_p2_exodus_patent.py#L605-L617).

The 1.27/k mm lateral sequence removes the large **blade-width** rounding error from prior iterations, but:
1. **The z-grid is held at dz=2.54 mm.** This tests 3D model sensitivity to x/y resolution, not convergence with respect to all three spatial dimensions or end-fringing resolution.
2. **Ground electrode thickness T2 is not resolved:** `n_ground_th=max(1,round(0.25mm/dx))` produces one-cell thicknesses of **1.27, 0.635 and ~0.423 mm** at k=1,2,3 vs the modeled **0.25 mm** (ratios ~5.08, 2.54, 1.69). Assertions on tip/gap/pitch/ground **width**/z length do not capture this remaining geometry distortion. Ground thickness is an externally estimated unsourced dimension, which should be audited/swept rather than treated as exact.
3. `run_3d_mesh_convergence_study` defaults to the **single-blade schematic**. The actual FIG.21 nine-blade potted article is only tested at one fine-grid setting, with no multi-resolution force convergence.
4. The test asserts sign, nonzero force, geometric ratios, and existence of an extrapolate, **not tolerance-bounded changes in each 3D blade, ground, dielectric, wall, net and H1 result**. A single three-point observed-order estimate for *blade force* alone does not validate all these terms or asymptotic convergence.

**Required R6:** report fixed-geometry multilevel FIG.21 force tables for each body, net, material and patent-face H1 quantities; refine z as well as lateral mesh or bound z-discretization error separately; quantify actual ground thickness and tip geometry error at each level; show observed differences/extrapolation stability with predeclared tolerances. Where a parameter is truly unknown, explicitly leave model uncertainty unbounded or report a sensitivity range.

### P2-R5-F2 — HIGH — Uncertainty numbers remain uncalibrated, and refinement does not recompute the real acceptance predicate

Sources: [production budget and gate](https://github.com/aguacatero/scalar-wave-viz/blob/a47f551ff32a53fdfa092b531edd9a7c4490fd1f/exodus_hypothesis_evaluator.py#L1909-L1971), [post-hoc update](https://github.com/aguacatero/scalar-wave-viz/blob/a47f551ff32a53fdfa092b531edd9a7c4490fd1f/exodus_hypothesis_evaluator.py#L2214-L2253), [adversarial test](https://github.com/aguacatero/scalar-wave-viz/blob/a47f551ff32a53fdfa092b531edd9a7c4490fd1f/tests/test_p2_exodus_patent.py#L561-L603).

The initial `solve_exodus_electrostatics_3d` code calculates:
- `u_mesh = 0.25*abs(F_3D_blade - F_2D_extruded_blade)` — **3D/2D model dimensional/fringing difference is not a measured 3D discretization error**.
- `u_domain = 0.20*abs(F_wall)+1e-5` — a **fixed percentage/offset**, *not* derived from `run_3d_enclosure_clearance_sweep`.
- `u_model = 5e-5 N` (**50 µN**) — a **hard-coded** purported tip-radius/model-sensitivity bound without an actual fillet-radius sweep; other omitted apparatus parameters remain unbounded.

The refinement routine later replaces `mesh_force_discretization_uncertainty_n`, RSS, and linear bound in returned dataclasses, **but does not rerun the `is_resolved` predicate or update `physical_scale_discrimination_status` / `finite_3d_is_conserved` against the replaced budget**. Its regression merely re-implements a separate `_evaluate_gate` helper *inside the test*, so it does not adversarially exercise the production acceptance function. With current hard-coded `u_model=50 µN > 23.7 µN` and unverified whole-body status, the actual gate cannot pass at any mesh, which is honest fail-closed now but not a calibrated decision procedure.

**Required R6:** centralize the production gate as a pure function taking the **final** 3D five-term budget and verified-body state; call it after refinement; test injected small closure/large mesh/domain/model through that actual function. Calculate domain uncertainty from paired clearance sweeps at consistent geometry and mesh, mesh uncertainty from controlled 3D convergence, and model bounds from declared parameter sweeps or mark unknown/unbounded. Avoid combining unqualified guesses as if they were statistically independent 1-sigma errors. Retain **NOT RESOLVED** until all terms are demonstrably below the declared criterion.

### P2-R5-F3 — HIGH — A partially agreeing 3D benchmark does not validate the nine-blade dielectric mechanical reaction

Sources: [3D benchmark](https://github.com/aguacatero/scalar-wave-viz/blob/a47f551ff32a53fdfa092b531edd9a7c4490fd1f/exodus_hypothesis_evaluator.py#L998-L1157), [actual article reaction](https://github.com/aguacatero/scalar-wave-viz/blob/a47f551ff32a53fdfa092b531edd9a7c4490fd1f/exodus_hypothesis_evaluator.py#L1817-L1840), [result fields](https://github.com/aguacatero/scalar-wave-viz/blob/a47f551ff32a53fdfa092b531edd9a7c4490fd1f/exodus_hypothesis_evaluator.py#L2019-L2029), [benchmark regression](https://github.com/aguacatero/scalar-wave-viz/blob/a47f551ff32a53fdfa092b531edd9a7c4490fd1f/tests/test_p2_exodus_patent.py#L287-L300).

The new independent-observable benchmark is useful, but its four force values are **-49.58 µN analytical, -38.30 µN virtual work, -36.58 µN contour and -28.00 µN interface**. Contour vs virtual work is ~4.5%, while the direct interface estimate differs from contour by **~23.5%** and analytical vs contour by **~26.2%**. The test permits up to **35%** interface/contour disagreement and still hard-labels the result `INDEPENDENT_3D_DIELECTRIC_BENCHMARK_VALIDATED` without any refinement or demonstrated uncertainty for the benchmark. In the *actual* FIG.21 solver, `finite_3d_dielectric_virtual_work_x_n` remains **0.0**, and there is no direct-material vs contour discrepancy acceptance check, sensitivity sweep, or body-fitted interface treatment. Its honest global `whole_body_3d_mechanical_accounting=UNVERIFIED_PENDING_CONFORMING_INTERFACE_MESHING` appropriately precludes scientific acceptance.

**Required R6:** rename the benchmark status to *provisional/approximate* until cross-method discrepancies are explained and shown to converge; run interface/contour/virtual-work comparisons on the actual 9-blade potted geometry across mesh and dielectric location/permittivity; explicitly handle constitutive assumptions and stress discontinuity rather than claiming that centered `E²∇ε` across a staircased interface is validated traction. Do not set the FIG.21 virtual-work metric to 0 when it is **not computed** (use optional/unknown semantics). Only declare verified whole-body accounting on independent, quantitative closure.

### P2-R5-F4 — HIGH — The new “3D H1” surface prediction is not the patent's Eq. (11) face quantity

Sources: [new directional H1 fields](https://github.com/aguacatero/scalar-wave-viz/blob/a47f551ff32a53fdfa092b531edd9a7c4490fd1f/exodus_hypothesis_evaluator.py#L1841-L1852), [documented H1 Eq. (11)](https://github.com/aguacatero/scalar-wave-viz/blob/a47f551ff32a53fdfa092b531edd9a7c4490fd1f/docs/EXODUS_MODEL_CONTRACT.md#L37-L64).

`h1_surface_integral_e2_v2_m` sums **E² on all six faces of the solver's blade-enclosing integration box**, *not* the patent's prescribed proximal tip 100a / distal face 101a electrode surface integrals. `h1_surface_force_prediction_n=0.5*eps0*(e2_bx_r-e2_bx_l)` additionally inserts **the Maxwell-stress factor 1/2** and labels this as an H1 prediction even though the patent alternative is **ε0(E2² A2−E1² A1)** with no such factor. The six-face summed `E²` has no directly justified identification with Eq. (11), and it is not a separate H1 numerical convergence test. The original 2D H1 remains separately implemented, but these new 3D fields cannot be used to support claimed **3D patent H1 face convergence**.

**Required R6:** perform explicit 3D material-side quadrature on the actual electrode faces 100a and 101a with correct normals, areas and dielectric-side sampling; return the **literal patent Eq. (11) H1 result** separately from the **0.5-factor corrected Maxwell traction** and from full closed-surface H0. Add uniform/nonuniform face-value and face-area adversarial regressions, and quantify 3D H1 sensitivity through refinement.

## Additional finding

### P2-R5-M1 — MED — A regression does not exercise the actual plotting implementation

[tests/test_p2_exodus_patent.py L881–895](https://github.com/aguacatero/scalar-wave-viz/blob/a47f551ff32a53fdfa092b531edd9a7c4490fd1f/tests/test_p2_exodus_patent.py#L881-L895) recreates the expected `f"..."` strings locally from model fields, but never calls/inspects `examples/exodus_patent_demo.py`. The source figure now uses dynamic labels [L137–155](https://github.com/aguacatero/scalar-wave-viz/blob/a47f551ff32a53fdfa092b531edd9a7c4490fd1f/examples/exodus_patent_demo.py#L137-L155), so the immediate visual defect is fixed; however, a future hard-coded regression in the figure would not fail this test. Extract a shared label formatter called by both plotting code and test, or render the figure with alternate inputs and inspect the resulting axis tick labels.

## Recommendation / next R6 checkpoint

The R5 work is genuine progress: correct CI/provenance, commensurate x/y blade spacing, observed-order analysis, reported 3D body quantities, new interface-force calculation, richer uncertainty accounting, corrected metadata/phrasing and live plot labels. **Nevertheless, current code cannot establish target-scale 3D FIG.21 mechanical closure or quantitatively discriminating H0/H1 forces.** The review should not grant P2 scientific acceptance solely on successful CI or explicit fail-closed tags.

Prioritize (1) a *single, production-tested* uncertainty gate with measured rather than guessed inputs, (2) consistent *nine-blade* 3D force and dielectric convergence including z/ground thickness, (3) true 3D patent-face H1 quadrature; then use the resulting evidence to set a scientifically justified next checkpoint. Continue to separate numerical verification from laboratory validation.

**FINAL R5 VERDICT: CHANGES REQUIRED — P2 SCIENTIFIC BASELINE NOT ACCEPTED. KEEP PR #11 DRAFT/OPEN/UNMERGED; MANUAL-ONLY; NO MERGE OR P3 KICKOFF.**