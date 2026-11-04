# SCALAR WAVE VIZ — PROPULSION EXPLORER 3D (V0) DRAFT HANDOFF (ROUND 5)

**Repository:** https://github.com/aguacatero/scalar-wave-viz  
**Pull Request:** [Draft PR #14](https://github.com/aguacatero/scalar-wave-viz/pull/14)  
**Issue Tracked:** [Issue #13: V0 — Build the first visual-first 3D Propulsion Explorer demo](https://github.com/aguacatero/scalar-wave-viz/issues/13)  
**Branch:** `v0-propulsion-explorer-3d`  
**Milestone:** Track A — Milestone V0 (Visual-First 3D Propulsion Explorer)  
**Review Status:** **READY FOR CHATGPT INDEPENDENT RE-REVIEW (R5)**  
**Governing Documents:** [AGENTS.md](../../AGENTS.md), [PROPULSION_EXPLORER_VISION.md](../PROPULSION_EXPLORER_VISION.md), [ROADMAP.md](../ROADMAP.md)  
**Operating Mode:** MANUAL-ONLY  
**Merge Authorization:** NOT GRANTED (PR remains DRAFT pending independent review; Track B PR #11 remains separate; no auto-merge, no P3 kickoff)  

---

## 1. Executive Summary

This handoff advances **Milestone V0: The first usable, beginner-friendly 3D Propulsion Explorer** for `aguacatero/scalar-wave-viz`, delivering a comprehensive remediation of all findings from ChatGPT's independent re-review of V0 R4 ([`pullrequestreview-5744233825`](https://github.com/aguacatero/scalar-wave-viz/pull/14#pullrequestreview-5744233825)), which concluded `CHANGES REQUIRED — NOT ACCEPTED for the V0 baseline at R4` with 1 HIGH/BLOCKING finding and 3 MEDIUM findings.

Every finding (`V0-R4-F1` and `V0-R4-M1` through `M3`) has been fully resolved, verified by 32 unit tests, 14 headless Playwright browser smoke tests (including full 5-component alternate-view pointer picking, runtime WebGL Box3 bounding box validation, and inspector force string assertions), and recaptured visual evidence across all 6 screenshots in `assets/`.

---

## 2. R4 Independent Review Remediation Matrix

| Review Finding | Severity | Description | Remediation Implemented in R5 | Verification |
| --- | --- | --- | --- | --- |
| **V0-R4-F1** | HIGH / BLOCKING | Alternate-view canvas picking test only checked 3 components and omitted hover banner, badge, and selected `data-id` checks for `support_mount` and `enclosure_walls`. | 1. Configured camera preset `'top'` with `newUp = new THREE.Vector3(0, 0, -1)` and `newPos = (0, 140, 0.001)` to eliminate lookAt polar orientation singularity.<br>2. Positioned `support_mount` surface target at $(-25, -20, 25)$ (unoccluded in isometric, side, and top views) and `enclosure_walls` camera-adaptive view projection.<br>3. Expanded `test_canvas_pointer_picking_alternate_camera_views` in `tests/test_v0_browser_smoke.py` to test ALL 5 components (`blade_electrode`, `dielectric_block`, `ground_electrode`, `support_mount`, `enclosure_walls`) in BOTH Side and Top presets with real `page.mouse.move` (checking `#banner-text` hover updates), real `page.mouse.click` (checking `#inspector-name` and `#inspector-badge`), and asserting unique selected `.component-item-btn.selected[data-id]`. | `test_canvas_pointer_picking_alternate_camera_views` passes 100% across all 5 components in Side and Top views in headless Chromium. |
| **V0-R4-M1** | MEDIUM | Physical gap test was a static string check rather than an actual WebGL runtime geometry regression. | Implemented `test_runtime_gap_slider_mesh_bounding_boxes` in `tests/test_v0_browser_smoke.py`. Drives the actual DOM `#slider-gap` across 16, 25, 50 mm, evaluating `THREE.Box3().setFromObject(mesh)` with updated world matrices to assert: (1) `ground.min.x - blade.max.x == d` within 0.01 mm tolerance; (2) `ground.min.x - dielectric.max.x >= 5.0` mm clearance invariant; (3) UI inspector retains tip radius metadata and surface gap notes. | Browser test passes in headless Chromium across all 3 gap slider steps. |
| **V0-R4-M2** | MEDIUM | Maxwell stress tensor equation was stated as general scalar $T_{xx} = \frac{1}{2}\varepsilon_0 E_x^2$ without transverse-field terms or 1D limitation notice. | Corrected the equation across `explorer/index.html`, `explorer/explorer.js`, and `explorer/provenance_data.json` to state the full 3D vacuum Maxwell stress tensor component $T_{xx} = \varepsilon_0 \left(E_x^2 - \frac{1}{2}|\mathbf{E}|^2\right) = \frac{1}{2}\varepsilon_0(E_x^2 - E_y^2 - E_z^2)$. Explicitly qualified $\frac{1}{2}\varepsilon_0 E_x^2$ as an idealized 1D approximation strictly valid only where transverse fields vanish ($E_y = E_z = 0$). Added unit regression tests. | Unit tests `test_maxwell_stress_tensor_transverse_terms_qualified` and `test_maxwell_stress_tensor_in_html_qa` pass. |
| **V0-R4-M3** | MEDIUM | Inspector's `Illustrative Scale: (V/20)^2 x` contradicted the bounded visual arrow lengths (e.g. 0.01x vs 6.1 mm at 2 kV). | Separated physical scaling trend from visual arrow encoding in `explorer.js`: `#inspector-force` now displays `[Physical Trend: (V/20)² = ...x | Visual Arrow: ... mm bounded legibility]`. Displays `0.0 (Field OFF at 0 V)` at 0 kV, `0.01x | 6.1 mm` at 2 kV, `1.00x | 16.0 mm` at 20 kV, and `6.25x | 30.0 mm` at 50 kV. Added browser smoke test. | Browser test `test_inspector_force_separates_physical_trend_and_visual_arrow` passes across all 4 voltage levels. |

---

## 3. Verified Deliverables & Test Evidence

- **Frontend Application (`explorer/`):**
  - `index.html`: Accessible layout with updated Maxwell stress tensor formulation, surface gap slider label, visual proxy qualification, bounded schematic arrow legend, Boundary A/B/C force ledger, and fail-closed disclaimers.
  - `explorer.css`: High-contrast dark-mode theme with responsive mobile layout down to 375px.
  - `explorer.js`: Version `0.5.0-r5`. Three.js scene with orientation-stable top/side camera view presets, unoccluded screen projection for all 5 components, separate physical trend vs visual arrow encoding in inspector, `disposeHierarchy(root)` GPU leak cleanup, bounded arrow length scaling ($[6.0, 30.0]\text{ mm}$), surface-to-surface gap positioning with $+5.0\text{ mm} \ge 3.0\text{ mm}$ physical clearance, signed electric field streamlines ($0\text{ V} \to -V$), zero-voltage field extinction, and spherical keyboard navigation.
  - `provenance_data.json`: Schema version `0.5.0-r5` with synchronized blade dimensions, non-modeled tip radius tag, surface-to-surface gap definition, visual proxy permittivity qualification, full Maxwell stress tensor formulation, and Boundary A/B/C force accounting.
  - `vendor/three.min.js` & `vendor/OrbitControls.js`: Vendored for 100% offline execution.
- **Automated Test Suites:**
  - `tests/test_v0_propulsion_explorer.py`: **32 unit tests** (all passing) verifying schema provenance, dielectric citation accuracy, non-modeled tip radius tag, surface gap physical clearance invariant ($\ge 5.0\text{ mm}$), raycast picking logic, recursive GPU disposal, bounded vector legibility encoding ($[6.0, 30.0]\text{ mm}$), full Maxwell stress tensor qualification in JSON and HTML QA modal, and screen coordinate projection hooks.
  - `tests/test_v0_browser_smoke.py`: **14 browser smoke tests** using Playwright against real Chromium verifying canvas rendering, real canvas pointer picking across all 5 components in default AND alternate camera views (Side and Top) with hover status updates, layer toggle fallback, DOM slider synchronization, runtime WebGL Box3 bounding box verification across gap slider sweeps, inspector force string separation, instrumented GPU disposal across rendered sweeps, bounded force arrow chamber containment, modal dialogs, keyboard navigation, and 375x667 mobile layout.
- **Visual Evidence (`assets/`):**
  - `propulsion_explorer_v0_preview.png`: Full viewport rendering with 3D blade cathode, planar ground plate, dielectric potting, signed field streamlines, and bounded schematic force vectors all visibly active.
  - `propulsion_explorer_v0_tour.png`: Interactive Guided Tour modal illustrating clean, accessible HTML math with full Maxwell stress tensor qualification.
  - `propulsion_explorer_v0_ledger.png`: Whole-Body Force Ledger demonstrating Boundary A and Boundary B separation.
  - `propulsion_explorer_v0_sandbox.png`: What-If Parameter Sandbox with surface gap slider and permittivity proxy qualification.
  - `propulsion_explorer_v0_inspector.png`: 3D Raycast Inspector showing interior blade cathode selected through transparent chamber with separated physical trend vs bounded visual arrow readout.
  - `propulsion_explorer_v0_mobile.png`: Responsive 375px mobile presentation with active 3D scene and wrapped controls.
- **Baseline Integrity:**
  - P0 baseline Git blob `97f65dfa25db7730323edd5e52c98b17371fdeaa` preserved byte-for-byte.
  - P1 baseline files match base SHA `8e1fdb32655d073002ae5a794b08e48f19a78a0f` byte-for-byte.

---

## 4. Reviewer Acceptance Criteria for V0 R5

1. **Five-Component Real Canvas Picking in Alternate Views (`V0-R4-F1`):** Verify `tests/test_v0_browser_smoke.py` (`test_canvas_pointer_picking_alternate_camera_views`) exercises real pointer events (`page.mouse.move`, `page.mouse.click`) across all 5 component IDs in both Side and Top presets, asserting hover text, exact inspector title and badge, and unique `.component-item-btn.selected[data-id]`.
2. **Runtime WebGL Box3 Bounding Box Verification (`V0-R4-M1`):** Verify `test_runtime_gap_slider_mesh_bounding_boxes` drives `#slider-gap` across `16, 25, 50` mm, evaluating `THREE.Box3().setFromObject(mesh)` to assert $d = x_{\text{ground,near}} - x_{\text{blade,tip}}$ and clearance from dielectric $\ge 5.0\text{ mm}$.
3. **Full Maxwell Stress Tensor Formulation (`V0-R4-M2`):** Verify the general vacuum Maxwell stress tensor component $T_{xx} = \varepsilon_0(E_x^2 - \frac{1}{2}|\mathbf{E}|^2) = \frac{1}{2}\varepsilon_0(E_x^2 - E_y^2 - E_z^2)$ is stated in HTML, JS, and JSON, with $\frac{1}{2}\varepsilon_0 E_x^2$ explicitly marked as the 1D limit where transverse fields vanish.
4. **Separated Physical Trend vs Visual Arrow Encoding (`V0-R4-M3`):** Verify inspector displays both the physical quadratic trend (`(V/20)² = ...x`) and the bounded visual arrow length (`... mm bounded legibility`), verified by browser smoke test across 0, 2, 20, and 50 kV.
