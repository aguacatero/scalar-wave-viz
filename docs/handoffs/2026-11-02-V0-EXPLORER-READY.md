# SCALAR WAVE VIZ — PROPULSION EXPLORER 3D (V0) DRAFT HANDOFF (ROUND 3)

**Repository:** https://github.com/aguacatero/scalar-wave-viz  
**Pull Request:** [Draft PR #14](https://github.com/aguacatero/scalar-wave-viz/pull/14)  
**Issue Tracked:** [Issue #13: V0 — Build the first visual-first 3D Propulsion Explorer demo](https://github.com/aguacatero/scalar-wave-viz/issues/13)  
**Branch:** `v0-propulsion-explorer-3d`  
**Milestone:** Track A — Milestone V0 (Visual-First 3D Propulsion Explorer)  
**Review Status:** **READY FOR CHATGPT INDEPENDENT RE-REVIEW (R3)**  
**Governing Documents:** [AGENTS.md](../../AGENTS.md), [PROPULSION_EXPLORER_VISION.md](../PROPULSION_EXPLORER_VISION.md), [ROADMAP.md](../ROADMAP.md)  
**Operating Mode:** MANUAL-ONLY  
**Merge Authorization:** NOT GRANTED (PR remains DRAFT pending independent review; no auto-merge, no P3 kickoff)  

---

## 1. Executive Summary

This handoff advances **Milestone V0: The first usable, beginner-friendly 3D Propulsion Explorer** for `aguacatero/scalar-wave-viz`, delivering a comprehensive remediation of all findings from ChatGPT's independent re-review of V0 R2 ([`pullrequestreview-5739337831`](https://github.com/aguacatero/scalar-wave-viz/pull/14#pullrequestreview-5739337831)), which concluded `CHANGES REQUIRED — NOT ACCEPTED for the V0 baseline` with 1 HIGH/BLOCKING finding and 5 MEDIUM findings.

Every finding (`V0-R2-F1` and `V0-R2-M1` through `M5`) has been fully resolved, verified by unit tests, browser smoke tests, and recaptured non-blank visual evidence.

---

## 2. R2 Independent Review Remediation Matrix

| Review Finding | Severity | Description | Remediation Implemented in R3 | Verification |
| --- | --- | --- | --- | --- |
| **V0-R2-F1** | HIGH / BLOCKING | Outer transparent enclosure box (`enclosure_walls`) occludes interior components (`blade_electrode`, `ground_electrode`, `dielectric_block`, `support_mount`) in raycast picking because the camera is positioned outside the chamber. | Implemented `getPickedObject(event)` in `explorer.js`: iterates through all raycast intersections along the pointer ray, prioritizing visible interior components first, and only selecting `enclosure_walls` if no interior component is intersected. Both click and hover use this picker. | Verified in `tests/test_v0_browser_smoke.py` (`test_raycast_picking_prioritizes_interior_over_chamber`) and `tests/test_v0_propulsion_explorer.py`. |
| **V0-R2-M1** | MEDIUM | Gap slider allowed 2 mm solid-volume collision between ground plate (centered at min x=15, width 4, left face at x=13) and dielectric block (centered at x=5, width 20, right face at x=15); blade mesh dimensions `(30, 25.4, 3)` disagreed with provenance JSON `(50.8, 25.4, 1.27)`. | Resized dielectric block to width 16 mm centered at x=3 mm (extents `[-5.0, 11.0] mm`). Set gap slider `min="16"` (ground plate centered at x=gap, width 4 mm, left face at `gap - 2.0 = 14.0 mm`). Minimum clearance is `14.0 - 11.0 = +3.0 mm`, strictly preventing intersection across the entire range `[16, 50] mm`. Synchronized blade dimensions in `provenance_data.json` to `{width: 30.0, height: 25.4, thickness: 3.0, tip_radius: 0.1}`. | Invariant unit test in `tests/test_v0_propulsion_explorer.py` asserts `ground_x_min - diel_x_max >= 3.0 mm` across the range; dimensional match verified. |
| **V0-R2-M2** | MEDIUM | Dielectric citation referenced `US11511891B2, FIG. 7 (dielectric potting)`, but patent FIG. 7 depicts electrostatic pressure-force vectors, not dielectric potting specification (which is found in FIGS. 6B, 21, 23A; col. 7 lines 30–55). | Corrected citation in `provenance_data.json` to `US11511891B2, FIGS. 6B, 21, 23A; col. 7 lines 30–55 (dielectric medium 600 / high-voltage epoxy potting)`. Added explicit note distinguishing single-stage schematic potting block from multi-blade test article. | Unit test `test_dielectric_citation_and_potting_provenance` asserts citation contains FIGS. 6B, 21, 23A / col. 7 and rejects FIG. 7. |
| **V0-R2-M3** | MEDIUM | CI tests were purely static string/JSON checks without runtime browser execution; committed visual evidence (`preview.png` and `mobile.png`) had layers toggled off, showing empty scenes. | 1. Built `tests/test_v0_browser_smoke.py` with 8 Playwright browser smoke tests covering default load, raycast picking, slider synchronization, modal trapping, keyboard navigation, narrow mobile viewport (375x667), and memory stability. Added Playwright to CI workflow.<br>2. Recaptured all 6 screenshots in `assets/` with all visual layers (Geometry, Fields, Forces) fully active. | Playwright suite passes 8/8 tests in headless browser; fresh PNG assets committed. |
| **V0-R2-M4** | MEDIUM | Force vectors used arbitrary constants (24, 22, 8, 16, 10), implying unsupported relative force ratios that broke directional balance when dielectric slider moved. | Standardized all 5 schematic force vectors to uniform normalized base length `UNIFORM_ARROW_BASE_LEN = 18.0`. All arrows scale identically as $18.0 \times (V/20)^2$, strictly depicting physical lines of action and action/reaction directions without implying uncomputed force ratios. | Verified by unit test asserting absence of disparate constants; UI disclaimers updated. |
| **V0-R2-M5** | MEDIUM | Removing `forceGroup` and `fieldGroup` children did not dispose geometries and materials, causing GPU resource leaks on slider input. | Implemented `disposeHierarchy(root)` which traverses all descendants and invokes `.dispose()` on all geometries and materials. Invoked on every rebuild in `updateForceVectors()` and `updateFieldLines()`. | Browser test `test_gpu_memory_does_not_grow_on_repeated_slider_updates` verifies zero geometry count growth across 40 rapid slider updates. |

---

## 3. Verified Deliverables & Test Evidence

- **Frontend Application (`explorer/`):**
  - `index.html`: Accessible layout with updated gap slider (`min="16"` with verified +3 mm clearance hint), uniform schematic vector legend, Boundary A/B/C force ledger, and fail-closed disclaimers.
  - `explorer.css`: High-contrast dark-mode theme with responsive mobile layout down to 375px.
  - `explorer.js`: Three.js scene setup with `getPickedObject(event)` occlusion-free raycasting, `disposeHierarchy(root)` GPU memory leak cleanup, uniform arrow length scaling, positive-clearance dielectric geometry, signed electric field streamlines ($0\text{ V} \to -V$), zero-voltage field extinction, and spherical keyboard navigation.
  - `provenance_data.json`: Schema version `0.3.0-r3` with synchronized blade dimensions, corrected dielectric patent citation, Boundary A/B/C force accounting, and zero unearned claims.
  - `vendor/three.min.js` & `vendor/OrbitControls.js`: Vendored for 100% offline execution.
- **Automated Test Suites:**
  - `tests/test_v0_propulsion_explorer.py`: **28 unit tests** (all passing) verifying schema provenance, dielectric citation accuracy, blade dimensional synchronization, +3 mm physical clearance invariant, raycast picking logic, recursive GPU disposal, and uniform vector scaling.
  - `tests/test_v0_browser_smoke.py`: **8 browser smoke tests** using Playwright against real Chromium verifying canvas rendering, interior raycast picking without chamber occlusion, slider DOM sync, modal dialogs, keyboard navigation, 375x667 mobile layout, and zero GPU memory leak on slider drag.
- **Visual Evidence (`assets/`):**
  - `propulsion_explorer_v0_preview.png`: Full viewport rendering with 3D blade cathode, planar ground plate, dielectric potting, signed field streamlines, and uniform schematic force vectors all visibly active.
  - `propulsion_explorer_v0_tour.png`: Interactive Guided Tour modal illustrating clean, accessible HTML math.
  - `propulsion_explorer_v0_ledger.png`: Whole-Body Force Ledger demonstrating Boundary A and Boundary B separation.
  - `propulsion_explorer_v0_sandbox.png`: What-If Parameter Sandbox with positive-clearance gap slider.
  - `propulsion_explorer_v0_inspector.png`: 3D Raycast Inspector showing interior blade cathode selected through transparent chamber.
  - `propulsion_explorer_v0_mobile.png`: Responsive 375px mobile presentation with active 3D scene and wrapped controls.
- **Baseline Integrity:**
  - P0 baseline Git blob `97f65dfa25db7730323edd5e52c98b17371fdeaa` preserved byte-for-byte.
  - P1 baseline files match base SHA `8e1fdb32655d073002ae5a794b08e48f19a78a0f` byte-for-byte.

---

## 4. Reviewer Acceptance Criteria for V0 R3

1. **Occlusion-Free Interior Picking (`V0-R2-F1`):** Verify clicking or hovering on interior components (blade, ground, dielectric, mount) selects the interior component rather than `enclosure_walls`.
2. **Physical Clearance & Dimension Sync (`V0-R2-M1`):** Verify ground plate at minimum gap (16 mm) maintains $\ge 3.0\text{ mm}$ physical clearance from dielectric potting, and blade dimensions match provenance JSON.
3. **Citation Accuracy (`V0-R2-M2`):** Verify dielectric citation references FIGS. 6B, 21, 23A / col. 7 and rejects FIG. 7 for potting.
4. **Browser Runtime Tests & Non-Blank Screenshots (`V0-R2-M3`):** Verify browser smoke suite executes in CI and committed screenshots display active scene elements.
5. **Uniform Schematic Vectors (`V0-R2-M4`):** Verify all schematic arrows scale uniformly as $18.0 \times (V/20)^2$ without arbitrary force ratios.
6. **Zero GPU Memory Leaks (`V0-R2-M5`):** Verify `disposeHierarchy` recursively frees Three.js geometries and materials on slider updates.
