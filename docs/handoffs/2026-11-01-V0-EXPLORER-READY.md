# SCALAR WAVE VIZ — PROPULSION EXPLORER 3D (V0) DRAFT HANDOFF

**Repository:** https://github.com/aguacatero/scalar-wave-viz  
**Pull Request:** (Draft PR to be opened for Issue #13)  
**Issue Tracked:** [Issue #13: V0 — Build the first visual-first 3D Propulsion Explorer demo](https://github.com/aguacatero/scalar-wave-viz/issues/13)  
**Branch:** `v0-propulsion-explorer-3d`  
**Milestone:** Track A — Milestone V0 (Visual-First 3D Propulsion Explorer)  
**Governing Documents:** [AGENTS.md](../../AGENTS.md), [PROPULSION_EXPLORER_VISION.md](../PROPULSION_EXPLORER_VISION.md), [ROADMAP.md](../ROADMAP.md)  
**Operating Mode:** MANUAL-ONLY  
**Merge Authorization:** NOT GRANTED (PR remains DRAFT pending independent review; no auto-merge, no P3 kickoff)  

---

## 1. Executive Summary

This handoff delivers **Milestone V0: The first usable, beginner-friendly 3D Propulsion Explorer** for `aguacatero/scalar-wave-viz`, implementing the user's primary vision from [Issue #13](https://github.com/aguacatero/scalar-wave-viz/issues/13) in parallel with ongoing Track B scientific work.

The application allows any curious nonspecialist or researcher to:
1. Open a local web page with zero build steps or Jupyter dependencies (`python run_explorer.py` or direct browser open).
2. Orbit, zoom, pan, and reset a 3D cited Exodus-inspired electrode arrangement (US11511891B2 FIGS. 4–8), featuring a high-voltage blade cathode (-20 kV), a planar ground counter-electrode (0 V), solid dielectric barrier potting ($\varepsilon_r = 3.8$), and grounded enclosure walls.
3. Switch layers: component geometry, electric field streamlines with color-coded $|\mathbf{E}|$, and action-reaction force vectors.
4. Experience a guided 4-question interactive tour answering: *What am I seeing?*, *Why does it happen?*, *What changes it?*, and *How could we test it?*.
5. Inspect the Whole-Body Force Ledger demonstrating that internal electrostatic forces sum identically to zero ($F_{\text{net}} = 0.000\text{ N}$), accompanied by prominent fail-closed disclaimers: `WHOLE-BODY THRUST: NOT MEASURED / NOT ESTABLISHED`.
6. Experiment with What-If parameter sliders (Voltage $0 - 50\text{ kV}$ scaling forces $\propto V^2$, Dielectric permittivity $\varepsilon_r \in [1, 5]$, and electrode gap spacing).
7. Inspect any component via 3D raycasting to view physical dimensions, cited patent references, material properties, and honest provenance badges (`PUBLISHED HYPOTHESIS`, `ESTABLISHED MODEL`, `WHAT-IF PARAMETER`).

---

## 2. Verified Deliverables & Test Evidence

- **Frontend Application (`explorer/`):**
  - `index.html`: Accessible, responsive HTML5 layout with ARIA landmarks, layer toggles, tour modal, help system, and ledger table.
  - `explorer.css`: High-contrast dark-mode theme with clear visual hierarchy, accessible color palettes, and responsive layouts.
  - `explorer.js`: Complete Three.js scene setup, custom knife-edge blade geometry, electric field streamlines, 3D arrow helpers, raycaster picking, camera animations, and slider bindings.
  - `provenance_data.json`: Structured, verifiable provenance metadata for all components, forces, null controls, and 4 questions.
  - `vendor/three.min.js` & `vendor/OrbitControls.js`: Vendored for 100% offline, zero-network-dependency capability.
- **Launcher Script (`run_explorer.py`):**
  - Zero-friction Python standard library launcher that finds open ports, serves `explorer/`, and opens the browser.
- **Unit Test Suite (`tests/test_v0_propulsion_explorer.py`):**
  - 17 unit tests verifying file existence, vendored offline assets, provenance schema integrity, action-reaction conservation, fail-closed thrust disclaimers, HTML accessibility, and launcher port detection.
- **Visual Evidence:**
  - `assets/propulsion_explorer_v0_preview.png`: Full viewport rendering of the 3D scene with field lines and force vectors.
  - `assets/propulsion_explorer_v0_tour.png`: Interactive Guided Tour modal illustrating Step 1 ("What am I seeing?").
  - `assets/propulsion_explorer_v0_ledger.png`: Whole-Body Force Ledger panel and `NOT MEASURED / NOT ESTABLISHED` banner.
  - `assets/propulsion_explorer_v0_sandbox.png`: What-If Parameter Sandbox with voltage and permittivity controls.
  - `assets/propulsion_explorer_v0_inspector.png`: 3D Raycast Inspector showing blade component citations and provenance badge.
- **Baseline Integrity:**
  - P0 baseline Git blob `97f65dfa25db7730323edd5e52c98b17371fdeaa` preserved byte-for-byte.
  - P1 baseline files preserved byte-for-byte.
  - Total test suite: **89 tests passed** (35 P0 + 37 P1 + 17 V0).
