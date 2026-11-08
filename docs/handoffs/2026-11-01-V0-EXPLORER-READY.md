# SCALAR WAVE VIZ — PROPULSION EXPLORER 3D (V0) DRAFT HANDOFF (ROUND 2)

**Repository:** https://github.com/aguacatero/scalar-wave-viz  
**Pull Request:** [Draft PR #14](https://github.com/aguacatero/scalar-wave-viz/pull/14)  
**Issue Tracked:** [Issue #13: V0 — Build the first visual-first 3D Propulsion Explorer demo](https://github.com/aguacatero/scalar-wave-viz/issues/13)  
**Branch:** `v0-propulsion-explorer-3d`  
**Milestone:** Track A — Milestone V0 (Visual-First 3D Propulsion Explorer)  
**Review Status:** **READY FOR CHATGPT INDEPENDENT RE-REVIEW (R2)**  
**Governing Documents:** [AGENTS.md](../../AGENTS.md), [PROPULSION_EXPLORER_VISION.md](../PROPULSION_EXPLORER_VISION.md), [ROADMAP.md](../ROADMAP.md)  
**Operating Mode:** MANUAL-ONLY  
**Merge Authorization:** NOT GRANTED (PR remains DRAFT pending independent review; no auto-merge, no P3 kickoff)  

---

## 1. Executive Summary

This handoff updates **Milestone V0: The first usable, beginner-friendly 3D Propulsion Explorer** for `aguacatero/scalar-wave-viz`, delivering a comprehensive remediation of all findings from ChatGPT's independent review of V0 R1 ([`pullrequestreview-5732570567`](https://github.com/aguacatero/scalar-wave-viz/pull/14#pullrequestreview-5732570567)).

The application enables any curious layperson or researcher to:
1. Open a local web page with zero build steps or Jupyter dependencies (`python run_explorer.py` or direct browser open).
2. Orbit, zoom, pan, and reset a 3D cited Exodus-inspired electrode arrangement (US11511891B2 FIGS. 4–8), featuring a high-voltage blade cathode (-20 kV), a planar ground counter-electrode (0 V), solid dielectric barrier potting ($\varepsilon_r = 3.8$), and grounded enclosure walls.
3. Switch layers: component geometry, electric field streamlines with color-coded $|\mathbf{E}|$, and action-reaction force vectors.
4. Experience a guided 4-question interactive tour answering: *What am I seeing?*, *Why does it happen?*, *What changes it?*, and *How could we test it?*, rendered with clean, accessible HTML math notation.
5. Inspect the Whole-Body Force Ledger demonstrating that internal electrostatic forces sum identically to zero across the isolated Device Under Test (Boundary A), while clearly separating external lab environment boundaries (Boundary B and C), accompanied by prominent fail-closed disclaimers: `WHOLE-BODY THRUST: NOT MEASURED / NOT ESTABLISHED`.
6. Experiment with What-If parameter sliders (Voltage $0 - 50\text{ kV}$ scaling forces $\propto V^2$, Dielectric permittivity $\varepsilon_r \in [1, 5]$, and electrode gap spacing bounded $\ge 15\text{ mm}$ to prevent solid-volume intersection).
7. Inspect any component—including enclosure walls—via 3D raycasting with interactive hover feedback, viewing physical dimensions, cited patent references, material properties, and honest provenance badges (`PUBLISHED HYPOTHESIS`, `ESTABLISHED MODEL`, `WHAT-IF PARAMETER`).

---

## 2. R1 Independent Review Remediation Matrix

Every finding from independent review `pullrequestreview-5732570567` has been addressed and verified:

| Review Finding | Severity | Description | Remediation Implemented in R2 | Verification |
| --- | --- | --- | --- | --- |
| **V0-R1-F1** | HIGH / BLOCKING | Invented newton-valued component forces (+0.045, -0.038, -0.005, -0.002 N) and false "observed/measured" status words. | Removed all fabricated numeric newton numbers from `explorer/provenance_data.json` and UI. Replaced with qualitative `schematic_direction`, `force_magnitude_status = "SCHEMATIC_VECTOR_NOT_COMPUTED_IN_V0"`, and `system_boundary`. Purged all claims of "observed" or "measured". | Unit tests assert zero invented numbers and zero unearned "measured/observed" tokens. |
| **V0-R1-F2** | HIGH / BLOCKING | Electric field streamlines hand-drawn; signed electrostatics $\mathbf{E} = -\nabla\Phi$ points from high potential (ground, 0 V) to lower potential (cathode, -20 kV); residual field oscillation at $V=0\text{ kV}$. | Reversed streamline direction to obey signed electrostatics ($0\text{ V} \to -20\text{ kV}$). Extinguished both `fieldGroup` and `forceGroup` completely (`visible = false`) when Voltage is set to $0\text{ kV}$. Clearly labeled as schematic flux paths rather than continuous PDE solutions. | Browser testing & unit tests verify complete extinction at $V=0\text{ kV}$. |
| **V0-R1-F3** | HIGH / BLOCKING | `controls.rotateLeft()`, `rotateUp()`, `dollyIn()`, `dollyOut()` are non-existent private methods on OrbitControls, throwing `TypeError` on keyboard navigation. | Replaced nonexistent method calls with robust spherical coordinate camera transformations (`orbitCamera(deltaTheta, deltaPhi)` and `dollyCamera(factor)`), updating `camera.position` relative to `controls.target` and invoking `controls.update()`. | Chrome DevTools verified 0 console errors across all 10 keyboard shortcuts (arrows, +/-, 1/2/3, r). |
| **V0-R1-F4** | HIGH / BLOCKING | Whole-body ledger obscures test article vs environment boundary by summing external chamber walls into internal DUT ledger. Arrow helper count did not reconcile with ledger. | Explicitly split ledger and schema into **Boundary A (Isolated DUT: blade, ground, dielectric, mount)** where internal forces sum to zero, **Boundary B (External Environment: chamber walls, grounded enclosure)**, and **Boundary C (Total Closed Universe)**. Added distinct 3D arrow helpers matching all ledger elements. | Unit tests verify schema partition and strict boundary separation. |
| **V0-R1-M1** | MEDIUM | What-If slider movements left displayed metadata stale in inspector and legends. | Implemented dynamic `updateUIState()` synchronizing all legend labels, inspector readouts, and status text on slider events. | Live testing verified dynamic synchronization across voltage, gap, and permittivity sliders. |
| **V0-R1-M2** | MEDIUM | Enclosure walls not selectable via raycaster; lack of pointer hover feedback. | Added `chamberMesh` to `pickableObjects`; added `pointermove` event listener to set pointer cursor and highlight selectable objects on hover. | Verified enclosure walls are selectable and show full inspector metadata. |
| **V0-R1-M3** | MEDIUM | Physical mesh dimensions differed from JSON metadata; gap slider allowed solid-volume intersection. | Synchronized 3D geometry dimensions exactly with provenance metadata; bounded gap slider to $\ge 15\text{ mm}$ (dielectric width $20\text{ mm}$) to strictly prevent mesh penetration. | Verified no mesh penetration across full slider range. |
| **V0-R1-M4** | MEDIUM | Header text overflowed on mobile (375px/390px); raw LaTeX strings unrendered; modal lacked focus trapping; ARIA listbox lacked selected state. | Added responsive CSS flex-wrapping for mobile viewports; replaced raw LaTeX with semantic HTML math (`<i>E</i> &prop; 1/<i>r</i>`, `<i>T<sub>xx</sub></i> = &frac12;&epsilon;<sub>0</sub><i>E<sub>x</sub></i><sup>2</sup>`, `<i>F</i> &prop; <i>V</i><sup>2</sup>`); implemented modal focus trapping (`trapFocus`/`releaseFocus`); added `aria-selected` tracking. | Chrome DevTools verified responsive layout on 375x667 (`hasOverflow: false`). |

---

## 3. Verified Deliverables & Test Evidence

- **Frontend Application (`explorer/`):**
  - `index.html`: Accessible, responsive HTML5 layout with ARIA landmarks, layer toggles, tour modal with focus trapping, dynamic legends, and structured Boundary A/B ledger table.
  - `explorer.css`: High-contrast dark-mode theme with responsive flex-wrapping down to 375px, boundary badge styling (`SUSPENDED APPARATUS`, `EXTERNAL LAB FRAME`), and fail-closed status banners.
  - `explorer.js`: Three.js scene setup, custom knife-edge blade geometry, signed electric field streamlines ($0\text{ V} \to -V$), zero-voltage field extinction, crash-free spherical keyboard navigation, enclosure raycasting, and dynamic UI state synchronization.
  - `provenance_data.json`: Structured provenance metadata with qualitative schematic directions, Boundary A/B/C force accounting, zero invented newton values, and zero unearned "measured/observed" claims.
  - `vendor/three.min.js` & `vendor/OrbitControls.js`: Vendored for 100% offline, zero-network-dependency capability.
- **Launcher Script (`run_explorer.py`):**
  - Zero-friction Python standard library launcher that finds open ports, serves `explorer/`, and opens the browser.
- **Unit Test Suite (`tests/test_v0_propulsion_explorer.py`):**
  - **23 unit tests** (expanded from 17) covering:
    - Zero invented numeric nominal forces in JSON schema.
    - Zero unearned "measured" or "observed" status claims.
    - Strict Boundary A / Boundary B / Boundary C separation.
    - Zero-voltage field line and force vector extinction.
    - Crash-free spherical camera orbit and dolly math.
    - Enclosure walls raycaster pickability.
    - Modal focus trapping attributes and ARIA semantics.
    - Vendored offline assets integrity.
- **Visual Evidence (`assets/`):**
  - `propulsion_explorer_v0_preview.png`: Full viewport rendering with signed field streamlines and schematic force arrows.
  - `propulsion_explorer_v0_tour.png`: Interactive Guided Tour modal illustrating clean, accessible HTML math.
  - `propulsion_explorer_v0_ledger.png`: Whole-Body Force Ledger demonstrating Boundary A and Boundary B separation.
  - `propulsion_explorer_v0_sandbox.png`: What-If Parameter Sandbox with dynamically synchronized readouts.
  - `propulsion_explorer_v0_inspector.png`: 3D Raycast Inspector showing enclosure wall inspection and provenance badge.
  - `propulsion_explorer_v0_mobile.png`: Responsive 375px mobile presentation with clean flex-wrapped header and controls.
- **Baseline Integrity:**
  - P0 baseline Git blob `97f65dfa25db7730323edd5e52c98b17371fdeaa` preserved byte-for-byte.
  - P1 baseline files match base SHA `8e1fdb32655d073002ae5a794b08e48f19a78a0f` byte-for-byte.
  - Total test suite: **95 tests passed** (35 P0 + 37 P1 + 23 V0 in 259.48s).

---

## 4. Scientific Integrity & Boundary Distinction

In accordance with [docs/SCIENCE_CHARTER.md](../SCIENCE_CHARTER.md) and [AGENTS.md](../../AGENTS.md), V0 maintains rigorous physical honesty:
1. **Conventional Electrostatics:** Local electrostatic traction $\mathbf{T} = \frac{1}{2}\varepsilon_0 E_n^2 \hat{\mathbf{n}}$ on the blade tip is balanced by opposing Maxwell stress on the planar counter-electrode, dielectric polarization, and enclosure walls. Across the isolated test article (Boundary A), internal forces sum identically to zero.
2. **Exodus H1 Hypothesis:** Cited as a published speculative hypothesis (US11511891B2). V0 clearly identifies it as unverified and explains why local traction does not constitute net propellantless propulsion.
3. **Mathematical Scalar Waves:** Strictly distinguished from electrostatic force models; toy scalar-wave simulations do not imply anomalous propulsion.
4. **Boundary Separation:** Clear physical separation between suspended apparatus (Boundary A) and external lab environment (Boundary B) prevents misleading claims about external wall interactions.

---

## 5. Reviewer Acceptance Criteria for V0 R2

1. **Zero Invented Forces:** Verify `provenance_data.json` contains no fabricated numeric force values and no unearned "measured/observed" claims.
2. **Signed Field Conventions:** Verify field streamlines flow from 0 V ground to -V cathode, and extinguish completely at $V=0\text{ kV}$.
3. **Keyboard Navigation Safety:** Verify arrow keys, +/-, and 1/2/3 execute cleanly without throwing `TypeError`.
4. **Boundary Accounting:** Verify the ledger clearly delineates Boundary A (DUT) from Boundary B (Environment).
5. **UI Accessibility & Responsiveness:** Verify semantic HTML math renders legibly, modal focus trapping works, and header wraps gracefully on 375px mobile screens.
