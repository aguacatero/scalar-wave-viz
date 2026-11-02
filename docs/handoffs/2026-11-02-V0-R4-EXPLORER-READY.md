# SCALAR WAVE VIZ — PROPULSION EXPLORER 3D (V0) DRAFT HANDOFF (ROUND 4)

**Repository:** https://github.com/aguacatero/scalar-wave-viz  
**Pull Request:** [Draft PR #14](https://github.com/aguacatero/scalar-wave-viz/pull/14)  
**Issue Tracked:** [Issue #13: V0 — Build the first visual-first 3D Propulsion Explorer demo](https://github.com/aguacatero/scalar-wave-viz/issues/13)  
**Branch:** `v0-propulsion-explorer-3d`  
**Milestone:** Track A — Milestone V0 (Visual-First 3D Propulsion Explorer)  
**Review Status:** **READY FOR CHATGPT INDEPENDENT RE-REVIEW (R4)**  
**Governing Documents:** [AGENTS.md](../../AGENTS.md), [PROPULSION_EXPLORER_VISION.md](../PROPULSION_EXPLORER_VISION.md), [ROADMAP.md](../ROADMAP.md)  
**Operating Mode:** MANUAL-ONLY  
**Merge Authorization:** NOT GRANTED (PR remains DRAFT pending independent review; no auto-merge, no P3 kickoff)  

---

## 1. Executive Summary

This handoff advances **Milestone V0: The first usable, beginner-friendly 3D Propulsion Explorer** for `aguacatero/scalar-wave-viz`, delivering a comprehensive remediation of all findings from ChatGPT's independent re-review of V0 R3 ([`pullrequestreview-5742453106`](https://github.com/aguacatero/scalar-wave-viz/pull/14#pullrequestreview-5742453106)), which concluded `CHANGES REQUIRED — V0 R3 NOT ACCEPTED for the V0 baseline` with 1 HIGH/BLOCKING finding and 4 MEDIUM findings.

Every finding (`V0-R3-F1` and `V0-R3-M1` through `M4`) has been fully resolved, verified by 30 unit tests, 12 headless Playwright browser smoke tests (including real canvas pointer interactions and instrumented prototype disposal), and recaptured visual evidence across all 6 screenshots in `assets/`.

---

## 2. R3 Independent Review Remediation Matrix

| Review Finding | Severity | Description | Remediation Implemented in R4 | Verification |
| --- | --- | --- | --- | --- |
| **V0-R3-F1** | HIGH / BLOCKING | Component selection tests clicked sidebar buttons instead of the real 3D canvas; single synthetic raycast coordinate only checked "some interior ID" without validating exact component IDs or fallback behaviors. | 1. Implemented `getComponentScreenCoords(id)` in `explorer.js` to project unoccluded 3D surface points to client coordinates.<br>2. Built `test_canvas_pointer_picking_all_components_default_view` using real `page.mouse.move(x, y)` and `page.mouse.click(x, y)` across all 5 components (`blade_electrode`, `dielectric_block`, `ground_electrode`, `support_mount`, `enclosure_walls`), verifying `#banner-text` hover updating (`Hover: {name} — Click to inspect`) and exact inspector title and badge matching.<br>3. Built `test_canvas_pointer_picking_alternate_camera_views` verifying canvas pointer picking across Side and Top camera presets.<br>4. Built `test_layer_toggles_and_raycast_fallback` verifying that disabling interior geometry causes pointer picking to fall through to `enclosure_walls`. | `tests/test_v0_browser_smoke.py` (`test_canvas_pointer_picking_all_components_default_view`, `test_canvas_pointer_picking_alternate_camera_views`, `test_layer_toggles_and_raycast_fallback`) all pass in headless Chromium. |
| **V0-R3-M1** | MEDIUM | Gap slider label was center-to-center instead of surface-to-surface; placing ground center at `x = gap` resulted in front face at `x = gap - 2.0` (14 mm face gap for 16 mm slider). Blade tip radius 0.1 mm was unmodeled in mesh but lacked explicit non-modeled metadata tags. | 1. Repositioned `groundMesh` to `position.set(currentGapMM + 2.0, 0, 0)` so its front face is identically at $x = currentGapMM$, establishing strict surface-to-surface physical gap $d = x_{\text{ground,near}} - 0$. At minimum $d = 16.0\text{ mm}$, physical clearance from dielectric block (right face at $x = 11.0\text{ mm}$) is $+5.0\text{ mm} \ge 3.0\text{ mm}$.<br>2. Updated slider label to `Electrode Surface Gap (d):` and hint noting physical clearance.<br>3. Tagged `blade_electrode.tip_radius_modeled_in_mesh: false` in `provenance_data.json` with note explaining idealized knife-edge vertex in V0 mesh; displayed in inspector card. | Unit tests in `tests/test_v0_propulsion_explorer.py` (`test_gap_slider_bounds_prevent_dielectric_collision`, `test_blade_and_dielectric_dimensions_provenance_vs_js`) and browser smoke tests pass. |
| **V0-R3-M2** | MEDIUM | GPU memory test ran 40 synchronous calls in one `page.evaluate` without rendering frames, assigned window property instead of updater variable, and permitted growth <= 15. | 1. Built `test_gpu_memory_disposal_during_rendered_slider_sweeps` in `tests/test_v0_browser_smoke.py`.<br>2. Instruments `THREE.BufferGeometry.prototype.dispose` and `THREE.Material.prototype.dispose` to track disposal invocations.<br>3. Drives real DOM sliders (`#slider-voltage`, `#slider-gap`, `#slider-eps`) across 3 sweeps (17 total steps) with animation frame delays.<br>4. Asserts $> 30$ active geometry disposals occurred during sweeps and `renderer.info.memory.geometries` remains tightly bounded ($\Delta \le 2$). | `test_gpu_memory_disposal_during_rendered_slider_sweeps` passes in headless Chromium. |
| **V0-R3-M3** | MEDIUM | Permittivity slider made only a cosmetic opacity change despite claiming polarization stress and capacitive coupling changes in descriptive text. | Qualified permittivity slider explicitly as visual/material proxy in V0: labeled `Dielectric Permittivity (ε_r) [Visual Proxy Only]:` in DOM, legend, and provenance data (`permittivity_status: "VISUAL_MATERIAL_PROXY_ONLY_IN_V0"` and `note: "Permittivity slider is a visual material proxy adjusting visual rendering/opacity only; continuous field redistribution, polarization force scaling, and capacitive coupling are not recalculated in V0 and will be introduced in solver-backed V1"`). | Unit test `test_dielectric_permittivity_proxy_metadata` and DOM structure tests pass. |
| **V0-R3-M4** | MEDIUM | Quadratic arrow formula omitted arrows below 5 kV and at 50 kV reached 112.5 mm, piercing the 80 mm chamber wall. | Implemented piecewise bounded legibility encoding: at $V = 0$, arrows extinguish (`visible = false`); for $V \in (0, 20]\text{ kV}$, $L = 6.0 + 10.0 \times (V/20)^2\text{ mm}$ ($[6.0, 16.0]\text{ mm}$); for $V \in (20, 50]\text{ kV}$, $L = 16.0 + 14.0 \times \frac{V^2 - 400}{2100}\text{ mm}$ ($[16.0, 30.0]\text{ mm}$). Positioned chamber wall reaction origin at $(75, 0, 0)$ pointing $-X$. All arrow origins and endpoints remain strictly within enclosure $[-80, 80]\text{ mm}$ with $> 40\text{ mm}$ wall clearance at 50 kV. | Unit test `test_bounded_force_arrow_legibility_encoding` and browser smoke test `test_bounded_force_arrows_browser_verification` pass. |

---

## 3. Verified Deliverables & Test Evidence

- **Frontend Application (`explorer/`):**
  - `index.html`: Accessible layout with updated surface gap slider label (`Electrode Surface Gap (d):`), permittivity visual proxy label (`Dielectric Permittivity (ε_r) [Visual Proxy Only]:`), bounded schematic arrow legend, Boundary A/B/C force ledger, and fail-closed disclaimers.
  - `explorer.css`: High-contrast dark-mode theme with responsive mobile layout down to 375px.
  - `explorer.js`: Three.js scene setup with `getComponentScreenCoords(id)` screen projection, real pointer picking without chamber occlusion, `disposeHierarchy(root)` GPU memory leak cleanup, bounded arrow length scaling ($[6.0, 30.0]\text{ mm}$), surface-to-surface gap positioning with $+5.0\text{ mm} \ge 3.0\text{ mm}$ positive physical clearance, signed electric field streamlines ($0\text{ V} \to -V$), zero-voltage field extinction, and spherical keyboard navigation.
  - `provenance_data.json`: Schema version `0.4.0-r4` with synchronized blade dimensions, non-modeled tip radius tag, surface-to-surface gap definition, visual proxy permittivity qualification, and Boundary A/B/C force accounting.
  - `vendor/three.min.js` & `vendor/OrbitControls.js`: Vendored for 100% offline execution.
- **Automated Test Suites:**
  - `tests/test_v0_propulsion_explorer.py`: **30 unit tests** (all passing) verifying schema provenance, dielectric citation accuracy, non-modeled tip radius tag, surface gap physical clearance invariant ($\ge 5.0\text{ mm}$), raycast picking logic, recursive GPU disposal, bounded vector legibility encoding ($[6.0, 30.0]\text{ mm}$), and screen coordinate projection hooks.
  - `tests/test_v0_browser_smoke.py`: **12 browser smoke tests** using Playwright against real Chromium verifying canvas rendering, real canvas pointer picking across all 5 components in default and alternate camera views, hover status updates, layer toggle fallback, DOM slider synchronization, instrumented GPU disposal across rendered sweeps, bounded force arrow chamber containment, modal dialogs, keyboard navigation, and 375x667 mobile layout.
- **Visual Evidence (`assets/`):**
  - `propulsion_explorer_v0_preview.png`: Full viewport rendering with 3D blade cathode, planar ground plate, dielectric potting, signed field streamlines, and bounded schematic force vectors all visibly active.
  - `propulsion_explorer_v0_tour.png`: Interactive Guided Tour modal illustrating clean, accessible HTML math.
  - `propulsion_explorer_v0_ledger.png`: Whole-Body Force Ledger demonstrating Boundary A and Boundary B separation.
  - `propulsion_explorer_v0_sandbox.png`: What-If Parameter Sandbox with surface gap slider and permittivity proxy qualification.
  - `propulsion_explorer_v0_inspector.png`: 3D Raycast Inspector showing interior blade cathode selected through transparent chamber with tip radius metadata note.
  - `propulsion_explorer_v0_mobile.png`: Responsive 375px mobile presentation with active 3D scene and wrapped controls.
- **Baseline Integrity:**
  - P0 baseline Git blob `97f65dfa25db7730323edd5e52c98b17371fdeaa` preserved byte-for-byte.
  - P1 baseline files match base SHA `8e1fdb32655d073002ae5a794b08e48f19a78a0f` byte-for-byte.

---

## 4. Reviewer Acceptance Criteria for V0 R4

1. **Real Canvas Pointer Picking (`V0-R3-F1`):** Verify `tests/test_v0_browser_smoke.py` exercises real pointer events (`page.mouse.move`, `page.mouse.click`) projecting mesh surface coordinates across all 5 components in default isometric and alternate views, asserting exact inspector updates, hover banner text, and layer-hide chamber fallback.
2. **Surface-to-Surface Gap & Clearance (`V0-R3-M1`):** Verify ground plate is positioned at $x = currentGapMM + 2.0$ so its near face is identically at $x = currentGapMM$ (establishing surface-to-surface gap $d$), guaranteeing $+5.0\text{ mm} \ge 3.0\text{ mm}$ clearance from dielectric potting; verify tip radius 0.1 mm is explicitly tagged as non-modeled in V0 polygonal mesh.
3. **Rendered GPU Disposal Verification (`V0-R3-M2`):** Verify `test_gpu_memory_disposal_during_rendered_slider_sweeps` drives real DOM sliders across rendered animation frames with instrumented prototype `.dispose()`, asserting $> 30$ disposals and bounded geometry count ($\Delta \le 2$).
4. **Permittivity Visual Proxy Qualification (`V0-R3-M3`):** Verify permittivity slider is explicitly qualified as visual material proxy only in DOM labels, legends, and provenance JSON.
5. **Bounded Arrow Legibility & Chamber Containment (`V0-R3-M4`):** Verify schematic force arrows scale smoothly within $[6.0, 30.0]\text{ mm}$ for all $V \in (0, 50]\text{ kV}$, extinguish at 0 kV, and all arrow tips remain strictly inside $[-80, 80]\text{ mm}$ chamber enclosure.
