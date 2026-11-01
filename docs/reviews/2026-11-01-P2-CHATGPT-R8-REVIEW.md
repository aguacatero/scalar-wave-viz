# SCALAR WAVE VIZ — ChatGPT Independent Scientific Re-Review P2 R8 — CHANGES REQUIRED

**Repository:** `aguacatero/scalar-wave-viz` · **Draft PR #11 / Issue #7**
**Exact reviewed source HEAD:** `ab6cfd446fc6988897835bde6f2830403c326451`
**Governing review:** [P2 R7](https://github.com/aguacatero/scalar-wave-viz/pull/11#issuecomment-6559262041)
**Scientific disposition:** **CHANGES REQUIRED — P2 R8 SCIENTIFIC BASELINE NOT ACCEPTED**
**Governance:** **MANUAL-ONLY / OPEN / DRAFT / UNMERGED. No merge authorization and no P3 kickoff.**

## Independent verification and scope

- Confirmed PR #11 is still open/draft/unmerged at the exact source SHA. R8 is 1 commit ahead of the R7 source `404e29ef914c0e141deb055ed82f6bf33d1af544`.
- Inspected exact-SHA evaluator, R8 regression tests, in-repo R8 handoff, plan and PR description; compared with the R7 findings.
- [GitHub Actions run 41338220531](https://github.com/aguacatero/scalar-wave-viz/actions/runs/41338220531), job `124942475382`: inspected logs, which report **Ran 126 tests in 448.093s / OK** and **Manifest provenance gate passed**. Source HEAD is separately recorded from synthetic PR merge `1aa5ae5...`.
- Artifact `conventional-electrostatics-preview`, ID `13096655906`, digest `sha256:5f0024df128bce966fcb530c2ea28cadb49f7fe77025484595a81bc2c694e63a`, verified via metadata. **Artifact ZIP contents were not independently inspected.**
- P0 `electrostatics_baseline.py` blob independently verified `97f65dfa25db7730323edd5e52c98b17371fdeaa`. Four P1 source/test files (`scalar_wave_3d.py`, `electrostatics_numerics.py`, `tests/test_p1_wave_3d.py`, `tests/test_p1_numerics.py`) have identical blobs at the PR head and base `8e1fdb32655d073002ae5a794b08e48f19a78a0f`.
- This is a **source/scientific-method and CI-log audit**, not an independently rerun 3D solver or laboratory measurement.

## R7 remediation status

| R7 finding | R8 reviewer determination |
|---|---|
| **R7-F1** surrogate / convergence | **PARTIAL — BLOCKING.** Model variants and matched-grid 25.4/101.6 mm comparison added; two axial lengths at one grid cannot validate a linear-with-end-caps transfer law or full-article convergence. Level-specific output ranges are not demonstrated discretization tolerances. |
| **R7-F2** domain uncertainty | **PARTIAL — BLOCKING.** The paired-clearance helper is now integrated into normal solves and separated from wall reaction, but the convergence path reuses coarse-grid calibration at every finer grid; difference between two box sizes is not a demonstrated upper bound. |
| **R7-F3** dielectric accounting | **PARTIAL — BLOCKING.** Permittivity sweep and two recorded resolution values exist, but no quantitative closure/convergence acceptance, independent FIG.21 virtual-work comparison, or established whole-body force reaction. |
| **R7-F4** whole-body uncertainty | **PARTIAL — BLOCKING.** Optional axial term now enters RSS when supplied; standard 3D/refinement calls do not supply it, and the reported mesh extrapolation remains blade-derived rather than whole-body-derived. |
| **R7-M1** H1 offset/bounds | **SUBSTANTIALLY RESOLVED AT SYNTHETIC QUADRATURE LEVEL; physical face limit still provisional.** Out-of-bounds rejection and x-gradient offset test added. |
| **R7-M2** review provenance | **RESOLVED for present CI/handoff.** Versioned review-file discovery is used by manifest; fallback/manual constant and lexicographic filename ordering remain minor robustness considerations. |

## Blocking findings

### P2-R8-F1 — HIGH — Two-length, single-grid transfer fit cannot certify 101.6 mm FIG.21 article convergence

**Source:** [transfer implementation lines 2862–2942](https://github.com/aguacatero/scalar-wave-viz/blob/ab6cfd446fc6988897835bde6f2830403c326451/exodus_hypothesis_evaluator.py#L2862-L2942), [test lines 659–678](https://github.com/aguacatero/scalar-wave-viz/blob/ab6cfd446fc6988897835bde6f2830403c326451/tests/test_p2_exodus_patent.py#L659-L678), [three-grid surrogate test lines 549–658](https://github.com/aguacatero/scalar-wave-viz/blob/ab6cfd446fc6988897835bde6f2830403c326451/tests/test_p2_exodus_patent.py#L549-L658).

The full-length comparison evaluates only the 25.4 and 101.6 mm models at `dx=dy=1.27 mm, dz=2.54 mm`. It defines `f_interior=(F_long−F_short)/(L_long−L_short)` and `F_end=F_short−L_short*f_interior`; **every pair of numerical points fits this two-parameter affine relation exactly**, so this does **not** independently validate a length-independent end-cap term or transfer extrapolation. The acceptance test only constrains the force ratio to 3.8–4.3 and end-cap fraction <5%. The three-level convergence test remains at 25.4 mm with co-varied enclosure margins; its "predeclared" per-level blade/ground/dielectric/wall/net ranges merely bracket expected values (force windows on the order of millinewtons), rather than enforcing **inter-level per-body convergence within the 23.7 microN discrimination budget**. Its ground electrode is physically under-resolved (actual/target thickness 5.08, 2.54, 1.693 across levels), so refined discrete geometries are not identical to the declared 0.25 mm sheet.

**Required:** test >=3 axial lengths, >=2 grid resolutions for the full declared length, controlled z-end and x/y boundary sweeps, and both body-by-body forces and H1 face quantities. Quantify thickness-model sensitivity and predeclare convergence/error tolerances based on physical scale rather than broad level-specific pass bands. Until then, label the reported 1.03% end-cap effect a **single-grid observation**, not verified transfer.

### P2-R8-F2 — HIGH — Clearance calibration is integrated, but not a mesh-consistent boundary-truncation bound

**Source:** [paired 3D calibration lines 2452–2521](https://github.com/aguacatero/scalar-wave-viz/blob/ab6cfd446fc6988897835bde6f2830403c326451/exodus_hypothesis_evaluator.py#L2452-L2521), [solve and budget wiring lines 2290–2364](https://github.com/aguacatero/scalar-wave-viz/blob/ab6cfd446fc6988897835bde6f2830403c326451/exodus_hypothesis_evaluator.py#L2290-L2364), [refinement uses base clearance lines 2621–2652](https://github.com/aguacatero/scalar-wave-viz/blob/ab6cfd446fc6988897835bde6f2830403c326451/exodus_hypothesis_evaluator.py#L2621-L2652).

Credit: normal solves now compute a paired boundary sensitivity, in x/y/z, and wall traction has its own field. However `run_3d_mesh_convergence_study` computes `u_clearance_base` **only at its coarsest level** and passes the exact same value to every finer-level solve without recalibration. Furthermore `u_domain=max(|ΔF_blade|,|ΔF_ground|,|ΔF_dielectric|)` from a single (U, 1.5U) pair is a measured change, not a proven upper bound on the truncation error relative to unbounded space. The 7.05 mN reported placement sensitivity already exceeds 23.7 microN by about 300x. `test_calibrate_domain_clearance_uncertainty_3d` asserts field separation and synthetic gate RSS sensitivity, not a fine-grid/FIG21-calibrated production result or asymptotic domain independence.

**Required:** calibrate actual selected FIG.21 geometry at each reviewed grid or demonstrate bounded transfer of clearance sensitivity across grids; sweep >=3 clearances and check limiting trend; retain original wall reaction separately; include per-body (and net) sensitivity and provenance in the published uncertainty evidence. Do not call a two-box difference a rigorous upper bound.

### P2-R8-F3 — HIGH — FIG.21 dielectric whole-body reaction/closure still lacks quantitative verification

**Source:** [test lines 1545–1591](https://github.com/aguacatero/scalar-wave-viz/blob/ab6cfd446fc6988897835bde6f2830403c326451/tests/test_p2_exodus_patent.py#L1545-L1591), [dielectric force implementation lines 2172–2208](https://github.com/aguacatero/scalar-wave-viz/blob/ab6cfd446fc6988897835bde6f2830403c326451/exodus_hypothesis_evaluator.py#L2172-L2208).

Permittivity-sweep regression uses a **shortened 25.4 mm surrogate** on a coarse grid and asserts only squared Pearson correlation `R²>0.98` between `F_interface` and `(epsilon_r-1)` at four points. A high correlation does not establish zero intercept, a theoretically justified proportionality, or interface/contour equality. The two-mesh `epsilon_r=3.8` test requires merely that both relative discrepancy values exist and are positive; it never asserts that error **decreases**, let alone reaches a specified tolerance. Independent FIG.21 virtual work remains `None`, and the solver correctly marks mechanical accounting `UNVERIFIED_PENDING_CONFORMING_INTERFACE_MESHING`. The reported mN-scale net residual is orders of magnitude above the 23.7 microN threshold.

**Required:** independent FIG.21 virtual-work/energy-shape-derivative benchmark, compatible interface-side fields and normals, mesh-by-mesh numeric closure table for each component, convergence criterion and a physically motivated residual tolerance. Keep the unverified state until satisfied.

### P2-R8-F4 — HIGH — Production uncertainty gate still permits omission of z-discretization and uses blade-only multi-grid error

**Source:** [gate lines 1751–1908](https://github.com/aguacatero/scalar-wave-viz/blob/ab6cfd446fc6988897835bde6f2830403c326451/exodus_hypothesis_evaluator.py#L1751-L1908), [ordinary solve defaults lines 1920–1931](https://github.com/aguacatero/scalar-wave-viz/blob/ab6cfd446fc6988897835bde6f2830403c326451/exodus_hypothesis_evaluator.py#L1920-L1931), [mesh extrapolation and post-refinement gate lines 2664–2791](https://github.com/aguacatero/scalar-wave-viz/blob/ab6cfd446fc6988897835bde6f2830403c326451/exodus_hypothesis_evaluator.py#L2664-L2791), [separate z-only study lines 2795–2858](https://github.com/aguacatero/scalar-wave-viz/blob/ab6cfd446fc6988897835bde6f2830403c326451/exodus_hypothesis_evaluator.py#L2795-L2858).

The gate sets `u_axial_z=0.0` when `z_mesh_discretization_uncertainty_n=None`, and that term is **optional**; a synthetic otherwise-"verified" record can therefore return RESOLVED without any evidence of axial convergence. Ordinary solves default axial estimate to None; `run_3d_mesh_convergence_study` does not pass an axial input to its post-refinement gate. Only the separate z-only two-level study supplies it. The existing 3-level extrapolate/error term is calculated from **blade force alone** and cannot stand in for a conservative component-wise whole-body bound. The simultaneous x/y/z refinement error and separately estimated z-only error are not established independent random errors, so adding their squares to an RSS does not itself prove a calibrated numerical uncertainty bound.

**Required:** make physical acceptance contingent upon **present and qualified** 3D/axial + per-body convergence evidence; require an explicit missing-estimate state (not silently 0) when applicable; test adversarial verified-status cases with omitted axial data; avoid double counting correlated refinement components or justify their dependence; preserve separate sensitivity-estimate versus validated-bound nomenclature.

### P2-R8-F5 — HIGH — Exported FIG.21 manifest can misrepresent missing calibration as zero and serialize non-standard NaN uncertainty values

**Source:** [uncalibrated solver branch, gate NaN, and returned fields lines 2300–2412](https://github.com/aguacatero/scalar-wave-viz/blob/ab6cfd446fc6988897835bde6f2830403c326451/exodus_hypothesis_evaluator.py#L2300-L2412), [manifest explicitly disables FIG21 calibration lines 3195–3208](https://github.com/aguacatero/scalar-wave-viz/blob/ab6cfd446fc6988897835bde6f2830403c326451/exodus_hypothesis_evaluator.py#L3195-L3208), [FIG21 uncertainty serialization lines 3421–3456](https://github.com/aguacatero/scalar-wave-viz/blob/ab6cfd446fc6988897835bde6f2830403c326451/exodus_hypothesis_evaluator.py#L3421-L3456), [JSON writer lines 3532–3534](https://github.com/aguacatero/scalar-wave-viz/blob/ab6cfd446fc6988897835bde6f2830403c326451/exodus_hypothesis_evaluator.py#L3532-L3534).

`generate_exodus_patent_manifest` explicitly evaluates the declared full-length FIG.21 model with `calibrate_domain_clearance=False` and no supplied sensitivity. The solve then has `clearance_uncert_n=None`, passes `float('nan')` to the gate, which returns nonfinite combined RSS/linear values, **but returns `domain_boundary_clearance_uncertainty_n=0.0` in `Finite3DModelResult`**. Consequently, the FIG.21 manifest exposes **0.0** in the domain uncertainty field while its placement-sensitivity field is `null`, and passes nonfinite totals to Python's default `json.dump` (which writes non-standard `NaN` tokens unless `allow_nan=False`). The provenance gate checks SHAs, not strict JSON numerical finiteness or the semantic consistency of these uncertainty fields. This is a deterministic source-path audit; the artifact ZIP bytes were not inspected.

**Required:** preserve `None/null` for uncalibrated/unknown domain uncertainty (never substitute zero); use explicit failed-closed status and structured error/unknown fields instead of NaN; serialize with `allow_nan=False`; add strict JSON parse and schema/invariant assertions against the **actual CI-generated FIG.21 manifest**. Either calibrate the released full-length FIG.21 model or clearly mark the unavailable uncertainty estimate without numeric precision.

## Additional considerations

- **P2-R8-M1 (MED):** [H1 quadrature](https://github.com/aguacatero/scalar-wave-viz/blob/ab6cfd446fc6988897835bde6f2830403c326451/exodus_hypothesis_evaluator.py#L1661-L1748) now rejects out-of-range offsets and the synthetic x-gradient test demonstrates offset dependence. This resolves the synthetic-function regression request, **not** the actual solved electrode material-side limiting-field/offset/mesh convergence. `blade_tip_spans=[]` still produces an artificial zero-area proximal face rather than a rejected invalid face; check empty/reversed spans and finite positive grid sizes. Keep physical H1 numbers provisional.
- **P2-R8-M2 (LOW):** [review discovery](https://github.com/aguacatero/scalar-wave-viz/blob/ab6cfd446fc6988897835bde6f2830403c326451/exodus_hypothesis_evaluator.py#L1616-L1643) reads repository review filenames correctly for current files; it sorts by lexicographic filename and falls back to `CURRENT_GOVERNING_REVIEW` on absent files. Prefer explicit machine-readable review metadata, numeric-round ordering, and fail-closed mismatch checks for publication. Current CI `P2_R7_REMEDIATION` value is correct.

## Review disposition / R9 pickup

**CHANGES REQUIRED — R8 SCIENTIFIC BASELINE NOT ACCEPTED.** Recognize real engineering progress (integrated domain sensitivity for ordinary solves; reviewed code status allowlist; H1 synthetic offset checks; dynamic review discovery; 126 passing tests; P0/P1 blob preservation). However the **full-length FIG21 numerical closure**, **whole-body 3D discretization**, **domain-truncation estimate validity**, and **released manifest uncertainty integrity** remain unresolved.

**No positive physical thrust finding or qualified 23.7 microN discrimination is supported.** Keep whole-body verification `UNVERIFIED_PENDING_CONFORMING_INTERFACE_MESHING`, missing model parameters unbounded, and physical discrimination unresolved. PR stays DRAFT/UNMERGED; no owner merge authorization and no P3. Remediate five HIGH issues with negative regressions, actual declared-geometry convergence data, and a strict machine-readable manifest evidence check before asking for R9 independent review.
