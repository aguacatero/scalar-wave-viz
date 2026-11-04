# V0 — Build the first visual-first 3D Propulsion Explorer demo (#13)

## Summary of Changes

Delivers **Milestone V0 (Round 5): The first working, beginner-friendly 3D Propulsion Explorer** on dedicated feature branch `v0-propulsion-explorer-3d`, implementing the user's visual-first north star from [Issue #13](https://github.com/aguacatero/scalar-wave-viz/issues/13) and [docs/PROPULSION_EXPLORER_VISION.md](docs/PROPULSION_EXPLORER_VISION.md).

This round remediates all 1 HIGH/BLOCKING finding (`V0-R4-F1`) and all 3 MEDIUM findings (`V0-R4-M1` through `M3`) identified in ChatGPT's independent re-review of V0 R4 ([`pullrequestreview-5744233825`](https://github.com/aguacatero/scalar-wave-viz/pull/14#pullrequestreview-5744233825)).

The visual explorer makes the fundamental physics approachable for anyone:
- Understand what electric fields do to an Exodus-inspired electrode arrangement.
- See how local electrostatic traction on a sharp blade is balanced by opposing reactions on the counter-electrode, dielectric potting, and chamber walls.
- Grasp why local attraction does **not** constitute propellantless propulsion ($F_{\text{net}} = 0\text{ N}$).

---

## What Am I Seeing? Visual Evidence

![Propulsion Explorer 3D V0 Viewport](assets/propulsion_explorer_v0_preview.png)

```
Visual Tour & Interactivity Progression:
• Guided Tour:      assets/propulsion_explorer_v0_tour.png
• Force Ledger:     assets/propulsion_explorer_v0_ledger.png
• What-If Sandbox:  assets/propulsion_explorer_v0_sandbox.png
• Component Detail: assets/propulsion_explorer_v0_inspector.png
• Mobile Layout:    assets/propulsion_explorer_v0_mobile.png
```

---

## R4 Review Remediation Matrix (V0 Round 5)

| Finding | Severity | Description | Remediation in R5 | Verification |
| --- | --- | --- | --- | --- |
| **V0-R4-F1** | HIGH / BLOCKING | Alternate-view canvas picking test verified only 3 components and omitted hover banner, badge, and selected `data-id` checks for `support_mount` and `enclosure_walls`. Top view suffered from camera up-vector polar singularity. | 1. Fixed `setViewPreset('top')` in `explorer.js` to set `newUp = new THREE.Vector3(0, 0, -1)` and `newPos = (0, 140, 0.001)`, eliminating the polar singularity and guaranteeing standard screen orientation (-Z up, +X right).<br>2. Adjusted `support_mount` picking target to unoccluded front-left surface point `(-25, -20, 25)` and `enclosure_walls` to camera-adaptive view projections (`(0, 0, 55)` in top view, `(0, 38, 0)` in side view, `(0, 42, 45)` in isometric).<br>3. Upgraded `test_canvas_pointer_picking_alternate_camera_views` in `tests/test_v0_browser_smoke.py` to test **all 5 components in both Side and Top views** with real `page.mouse.move(x, y)` (asserting `#banner-text` hover updates), real `page.mouse.click(x, y)` (asserting exact inspector title and badge match), and asserting unique selected `.component-item-btn.selected[data-id]`. | `test_canvas_pointer_picking_alternate_camera_views` passes in headless Chromium across 10 distinct camera-component interactions (5 components × 2 views). |
| **V0-R4-M1** | MEDIUM | Gap slider physical clearance regression was a static string/math check rather than a runtime WebGL geometry check derived from mesh transforms. | 1. Implemented `test_runtime_gap_slider_mesh_bounding_boxes` in `tests/test_v0_browser_smoke.py`.<br>2. Queries actual WebGL runtime geometry using `THREE.Box3().setFromObject(componentMeshes[id])` after `updateMatrixWorld(true)`.<br>3. Verifies across slider sweeps at 16, 25, and 50 mm that $x_{\text{ground,near}} - x_{\text{blade,tip}} == d$ identically matches the slider value and physical clearance $x_{\text{ground,near}} - x_{\text{diel,max}} \ge 5.0\text{ mm}$ is strictly maintained from dielectric potting ($x_{\text{diel,max}} = 11.0\text{ mm}$). | `test_runtime_gap_slider_mesh_bounding_boxes` passes in headless Chromium. |
| **V0-R4-M2** | MEDIUM | Maxwell stress tensor equation was stated as general scalar $T_{xx} = \frac{1}{2}\varepsilon_0 E_x^2$ without transverse-field terms ($E_y, E_z$) or 1D limitation notice. | 1. Updated tour step 2, HTML explanation section 2, and `provenance_data.json` with the complete vacuum Maxwell stress tensor component $T_{xx} = \varepsilon_0(E_x^2 - \frac{1}{2}|\mathbf{E}|^2) = \frac{1}{2}\varepsilon_0(E_x^2 - E_y^2 - E_z^2)$.<br>2. Explicitly qualified $\frac{1}{2}\varepsilon_0 E_x^2$ as an idealized 1D approximation strictly valid only where transverse fields vanish ($E_y = E_z = 0$).<br>3. Added unit tests `test_maxwell_stress_tensor_transverse_terms_qualified` and `test_maxwell_stress_tensor_in_html_qa` in `tests/test_v0_propulsion_explorer.py`. | Unit tests and DOM structure tests pass. |
| **V0-R4-M3** | MEDIUM | Inspector labeled vector force with `[Illustrative Scale: (V/20)^2 x]`, contradicting the bounded visual arrow lengths (e.g. 0.01x vs 6.1 mm at 2 kV). | 1. Decoupled physical force scaling from perceptual arrow encoding in `#inspector-force`: `[Physical Trend: (V/20)² = ...x | Visual Arrow: ... mm bounded legibility]`.<br>2. Added browser smoke test `test_inspector_force_separates_physical_trend_and_visual_arrow` asserting exact wording at 0, 2, 20, 50 kV. | `test_inspector_force_separates_physical_trend_and_visual_arrow` passes in headless Chromium. |

---

## Historical R3 Review Remediation Matrix (V0 Round 4)

| Finding | Severity | Description | Remediation in R4 | Verification |
| --- | --- | --- | --- | --- |
| **V0-R3-F1** | HIGH / BLOCKING | Component selection tests clicked sidebar buttons instead of the real 3D canvas; single synthetic raycast coordinate only checked "some interior ID". | 1. Implemented `getComponentScreenCoords(id)` in `explorer.js` to project unoccluded 3D surface points to client coordinates.<br>2. Built `test_canvas_pointer_picking_all_components_default_view` using real `page.mouse.move(x, y)` and `page.mouse.click(x, y)` across all 5 components (`blade_electrode`, `dielectric_block`, `ground_electrode`, `support_mount`, `enclosure_walls`), verifying `#banner-text` hover updates (`Hover: {name} — Click to inspect`) and exact inspector title and badge matching.<br>3. Built `test_canvas_pointer_picking_alternate_camera_views` verifying canvas pointer picking across Side and Top camera presets.<br>4. Built `test_layer_toggles_and_raycast_fallback` verifying that disabling interior geometry causes pointer picking to fall through to `enclosure_walls`. | `tests/test_v0_browser_smoke.py` (`test_canvas_pointer_picking_all_components_default_view`, `test_canvas_pointer_picking_alternate_camera_views`, `test_layer_toggles_and_raycast_fallback`) all pass in headless Chromium. |
| **V0-R3-M1** | MEDIUM | Gap slider label was center-to-center instead of surface-to-surface; ground mesh center placed at `x = gap` resulted in front face at `x = gap - 2.0` (14 mm face gap for 16 mm slider). Blade tip radius 0.1 mm was unmodeled in mesh but lacked explicit non-modeled metadata tags. | 1. Repositioned `groundMesh` to `position.set(currentGapMM + 2.0, 0, 0)` so its front face is identically at $x = currentGapMM$, establishing strict surface-to-surface physical gap $d = x_{\text{ground,near}} - 0$. At minimum $d = 16.0\text{ mm}$, physical clearance from dielectric block (right face at $x = 11.0\text{ mm}$) is $+5.0\text{ mm} \ge 3.0\text{ mm}$.<br>2. Updated slider label to `Electrode Surface Gap (d):` and hint noting physical clearance.<br>3. Tagged `blade_electrode.tip_radius_modeled_in_mesh: false` in `provenance_data.json` with note explaining idealized knife-edge vertex in V0 mesh; displayed in inspector card. | Unit tests in `tests/test_v0_propulsion_explorer.py` (`test_gap_slider_bounds_prevent_dielectric_collision`, `test_blade_and_dielectric_dimensions_provenance_vs_js`) and browser smoke tests pass. |
| **V0-R3-M2** | MEDIUM | GPU memory test ran 40 synchronous calls in one `page.evaluate` without rendering frames, assigned window property instead of updater variable, and permitted growth <= 15. | 1. Built `test_gpu_memory_disposal_during_rendered_slider_sweeps` in `tests/test_v0_browser_smoke.py`.<br>2. Instruments `THREE.BufferGeometry.prototype.dispose` and `THREE.Material.prototype.dispose` to track disposal invocations.<br>3. Drives real DOM sliders (`#slider-voltage`, `#slider-gap`, `#slider-eps`) across 3 sweeps (17 total steps) with animation frame delays.<br>4. Asserts $> 30$ active geometry disposals occurred during sweeps and `renderer.info.memory.geometries` remains tightly bounded ($\Delta \le 2$). | `test_gpu_memory_disposal_during_rendered_slider_sweeps` passes in headless Chromium. |
| **V0-R3-M3** | MEDIUM | Permittivity slider made only a cosmetic opacity change despite claiming polarization stress and capacitive coupling changes in descriptive text. | Qualified permittivity slider explicitly as visual/material proxy in V0: labeled `Dielectric Permittivity (ε_r) [Visual Proxy Only]:` in DOM, legend, and provenance data (`permittivity_status: "VISUAL_MATERIAL_PROXY_ONLY_IN_V0"` and `note: "Permittivity slider is a visual material proxy adjusting visual rendering/opacity only; continuous field redistribution, polarization force scaling, and capacitive coupling are not recalculated in V0 and will be introduced in solver-backed V1"`). | Unit test `test_dielectric_permittivity_proxy_metadata` and DOM structure tests pass. |
| **V0-R3-M4** | MEDIUM | Quadratic arrow formula omitted arrows below 5 kV and at 50 kV reached 112.5 mm, piercing the 80 mm chamber wall. | Implemented piecewise bounded legibility encoding: at $V = 0$, arrows extinguish (`visible = false`); for $V \in (0, 20]\text{ kV}$, $L = 6.0 + 10.0 \times (V/20)^2\text{ mm}$ ($[6.0, 16.0]\text{ mm}$); for $V \in (20, 50]\text{ kV}$, $L = 16.0 + 14.0 \times \frac{V^2 - 400}{2100}\text{ mm}$ ($[16.0, 30.0]\text{ mm}$). Positioned chamber wall reaction origin at $(75, 0, 0)$ pointing $-X$. All arrow origins and endpoints remain strictly within enclosure $[-80, 80]\text{ mm}$ with $> 40\text{ mm}$ wall clearance at 50 kV. | Unit test `test_bounded_force_arrow_legibility_encoding` and browser smoke test `test_bounded_force_arrows_browser_verification` pass. |

---

## Historical R2 Review Remediation Matrix

| Finding | Severity | Description | Remediation in R3 |
| --- | --- | --- | --- |
| **V0-R2-F1** | HIGH / BLOCKING | Outer transparent enclosure box occluded interior components in raycast picking. | Implemented `getPickedObject(event)` prioritizing interior components first. |
| **V0-R2-M1** | MEDIUM | Gap slider allowed 2 mm solid-volume collision between ground plate and dielectric. | Resized dielectric to width 16 mm (extents `[-5, 11] mm`); set gap min to 16 mm (clearance $\ge 3.0\text{ mm}$). |
| **V0-R2-M2** | MEDIUM | Dielectric citation referenced FIG. 7 instead of potting specification (FIGS. 6B, 21, 23A). | Corrected citation to FIGS. 6B, 21, 23A; col. 7 lines 30–55. |
| **V0-R2-M3** | MEDIUM | Tests were purely static string checks; committed screenshots had layers toggled off. | Built 8 browser smoke tests; recaptured non-blank screenshots. |
| **V0-R2-M4** | MEDIUM | Force vectors used arbitrary constants (24, 22, 8, 16, 10). | Standardized all vectors to uniform normalized base length. |
| **V0-R2-M5** | MEDIUM | Removing children did not dispose geometries and materials. | Implemented recursive `disposeHierarchy(root)`. |

---

## Historical R1 Review Remediation Matrix

| Finding | Severity | Description | Remediation in R2 |
| --- | --- | --- | --- |
| **V0-R1-F1** | HIGH / BLOCKING | Invented newton-valued component forces (+0.045, -0.038, -0.005, -0.002 N) and false "observed/measured" claims. | Removed all fabricated numbers; added qualitative directions and explicit `SCHEMATIC_VECTOR_NOT_COMPUTED_IN_V0`. |
| **V0-R1-F2** | HIGH / BLOCKING | Electric field streamlines signed convention & zero-voltage residual. | Corrected streamline flow from ground (0 V) to cathode (-20 kV) per $\mathbf{E} = -\nabla\Phi$. Extinguished field streamlines and force vectors completely at $0\text{ kV}$. |
| **V0-R1-F3** | HIGH / BLOCKING | OrbitControls private method `TypeError` on keyboard input. | Replaced nonexistent methods with robust spherical coordinate camera transformations (`orbitCamera`, `dollyCamera`). Live tested with 0 errors across 10 shortcuts. |
| **V0-R1-F4** | HIGH / BLOCKING | Whole-body ledger system boundary ambiguity. | Explicitly separated Boundary A (Isolated DUT), Boundary B (External Environment), and Boundary C (Total Universe). Reconciled 3D arrow helpers with ledger elements. |
| **V0-R1-M1** | MEDIUM | Stale metadata on What-If slider input. | Implemented dynamic `updateUIState()` synchronizing all legend labels, inspector readouts, and status text on slider events. |
| **V0-R1-M2** | MEDIUM | Enclosure walls not selectable via raycast; lack of hover feedback. | Added `chamberMesh` to pickable objects; added `pointermove` hover feedback and pointer cursor. |
| **V0-R1-M3** | MEDIUM | Mesh dimensions vs JSON metadata & slider collision. | Synchronized 3D geometry dimensions with provenance metadata; bounded gap slider to prevent mesh penetration. |
| **V0-R1-M4** | MEDIUM | Header mobile wrapping, unrendered LaTeX, modal focus trapping. | Added responsive flex-wrapping down to 375px; replaced raw LaTeX with semantic HTML math; implemented modal focus trapping. |

---

## Key Features Implemented

1. **Zero-Friction Local Run:**
   - Launch immediately with `python run_explorer.py` (opens `http://127.0.0.1:8000`).
   - Or serve with `python -m http.server 8000 --directory explorer`.
   - Or open `explorer/index.html` directly in any modern browser.
   - 100% offline capability: Three.js r128 and OrbitControls are vendored in `explorer/vendor/`. No npm install, no build step, no network requests.

2. **Recognizable, Sourced 3D Geometry:**
   - **Asymmetric High-Voltage Blade:** Tapered knife-edge blade cathode (-20 kV), cited from US11511891B2 FIGS. 4–8.
   - **Ground Counter-Electrode:** Planar collector electrode (0 V).
   - **Dielectric Barrier Block:** Semitransparent refractive epoxy potting ($\varepsilon_r = 3.8$, US11511891B2 FIGS. 6B, 21, 23A).
   - **Structural Support Stand:** Non-conductive insulating mount.
   - **Conductive Enclosure:** Bounding stainless steel chamber walls with ground coupling.

3. **Switchable Visual Layers:**
   - Component Geometry
   - Electric Field Streamlines (color-coded $|\mathbf{E}|$ gradient from 0 V ground to -20 kV blade) & Equipotential Contours
   - Action-Reaction Force Vectors (bounded schematic directions with $[6.0, 30.0]\text{ mm}$ scaling; labeled `SCHEMATIC / NOT TO SCALE`)
   - Chamber Enclosure & Wireframe Mode

4. **The Four Questions Guided Tour:**
   - *1. What am I seeing?* Asymmetric high-voltage cathode opposite planar ground collector.
   - *2. Why does it happen?* Sharp edge field concentration ($E \propto 1/r$) and Maxwell electrostatic tension ($T_{xx} = \varepsilon_0(E_x^2 - \frac{1}{2}|\mathbf{E}|^2) = \frac{1}{2}\varepsilon_0(E_x^2 - E_y^2 - E_z^2)$, with $\frac{1}{2}\varepsilon_0 E_x^2$ strictly valid only where transverse fields vanish).
   - *3. What changes it?* Quadratic voltage scaling ($F \propto V^2$), geometry sharpness, dielectric permittivity, and chamber wall distance.
   - *4. How could we test it?* Micro-Newton torsion pendulum in high vacuum ($< 10^{-5}\text{ Torr}$) with null controls for ion wind and electrostatic wall coupling.

5. **Strict Action-Reaction Force Ledger & Fail-Closed Status:**
   - Structured by physical system boundaries:
     - **Boundary A (Isolated DUT):** Blade traction + Ground reaction + Dielectric polarization + Mount support = $0.000\text{ N}$ (Internal balance).
     - **Boundary B (External Environment):** Chamber wall reaction and mount ground reaction.
     - **Boundary C (Total Closed Universe):** Net force = $0.000\text{ N}$.
   - Prominent status banner: `WHOLE-BODY THRUST: NOT MEASURED / NOT ESTABLISHED`.
   - Clear explanation that internal electrode traction does not constitute net propellantless thrust.

6. **What-If Parameter Sandbox:**
   - Voltage Slider ($0 - 50\text{ kV}$): dynamically scales field streamlines and force vectors ($\propto V^2$); complete extinction at $0\text{ kV}$.
   - Dielectric Permittivity Slider ($\varepsilon_r \in [1, 5]$): visual material proxy adjusting opacity.
   - Gap Spacing Slider ($16 - 50\text{ mm}$): surface-to-surface gap $d$ with verified $\ge 5.0\text{ mm}$ positive physical clearance from dielectric.

7. **3D Raycaster Component Inspector:**
   - Real pointer picking on canvas across all 5 components (including interior components through transparent chamber).
   - Shows role, citations, operating potential, material, dimensions, non-modeled tip radius note, honest provenance badges (`ESTABLISHED MODEL`, `PUBLISHED HYPOTHESIS`, `WHAT-IF PARAMETER`), and force breakdown separating physical trend `(V/20)²` from visual arrow legibility encoding.

---

## Verification & Integrity

- **Unit Tests:** 32 tests in `tests/test_v0_propulsion_explorer.py`, all passing (`Ran 32 tests in 0.047s, OK`).
- **Browser Smoke Suite:** 14 tests in `tests/test_v0_browser_smoke.py`, all passing in headless Chromium (`Ran 14 tests in 15.4s, OK`).
- **Full Discovery Suite:** 118 tests total (35 P0 + 16 P1 numerics + 21 P1 wave + 14 V0 smoke + 32 V0 unit, all passing).
- **P0 Baseline Preservation:** `git hash-object electrostatics_baseline.py` = `97f65dfa25db7730323edd5e52c98b17371fdeaa` (byte-for-byte identical).
- **P1 Baseline Preservation:** All P1 source and test files match base SHA `8e1fdb32655d073002ae5a794b08e48f19a78a0f` byte-for-byte.
- **Track Separation:** Dedicated feature branch `v0-propulsion-explorer-3d` based directly on `main` after PR #12 merge. Track B (P2 PR #11) remains separate.
- **README Synchronized:** Progress narrative and "What already runs" updated in `README.md`, `AGENTS.md`, and `docs/ROADMAP.md` in this change.
- **Governance:** MANUAL-ONLY; DRAFT PR; no merge authorization granted.
