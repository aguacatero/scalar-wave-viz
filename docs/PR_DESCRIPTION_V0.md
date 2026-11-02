# V0 — Build the first visual-first 3D Propulsion Explorer demo (#13)

## Summary of Changes

Delivers **Milestone V0 (Round 2): The first working, beginner-friendly 3D Propulsion Explorer** on dedicated feature branch `v0-propulsion-explorer-3d`, implementing the user's visual-first north star from [Issue #13](https://github.com/aguacatero/scalar-wave-viz/issues/13) and [docs/PROPULSION_EXPLORER_VISION.md](docs/PROPULSION_EXPLORER_VISION.md).

This round remediates all 4 blocking/HIGH findings (`V0-R1-F1` to `F4`) and all 4 MEDIUM findings (`V0-R1-M1` to `M4`) identified in ChatGPT's independent review of V0 R1 ([`pullrequestreview-5732570567`](https://github.com/aguacatero/scalar-wave-viz/pull/14#pullrequestreview-5732570567)).

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

## R1 Review Remediation Matrix

| Finding | Severity | Description | Remediation in R2 |
| --- | --- | --- | --- |
| **V0-R1-F1** | HIGH / BLOCKING | Invented newton-valued component forces (+0.045, -0.038, -0.005, -0.002 N) and false "observed/measured" claims. | Removed all fabricated numbers; added qualitative `schematic_direction`, `force_magnitude_status = "SCHEMATIC_VECTOR_NOT_COMPUTED_IN_V0"`, and `system_boundary`. Purged all claims of "observed" or "measured". |
| **V0-R1-F2** | HIGH / BLOCKING | Electric field streamlines signed convention & zero-voltage residual. | Corrected streamline flow from ground (0 V) to cathode (-20 kV) per $\mathbf{E} = -\nabla\Phi$. Extinguished field streamlines and force vectors completely at $V=0\text{ kV}$. |
| **V0-R1-F3** | HIGH / BLOCKING | OrbitControls private method `TypeError` on keyboard input. | Replaced nonexistent methods with robust spherical coordinate camera transformations (`orbitCamera`, `dollyCamera`). Live tested with 0 errors across 10 shortcuts. |
| **V0-R1-F4** | HIGH / BLOCKING | Whole-body ledger system boundary ambiguity. | Explicitly separated Boundary A (Isolated DUT), Boundary B (External Environment), and Boundary C (Total Universe). Reconciled 3D arrow helpers with ledger elements. |
| **V0-R1-M1** | MEDIUM | Stale metadata on What-If slider input. | Implemented dynamic `updateUIState()` synchronizing all legend labels, inspector readouts, and status text on slider events. |
| **V0-R1-M2** | MEDIUM | Enclosure walls not selectable via raycast; lack of hover feedback. | Added `chamberMesh` to pickable objects; added `pointermove` hover feedback and pointer cursor. |
| **V0-R1-M3** | MEDIUM | Mesh dimensions vs JSON metadata & slider collision. | Synchronized 3D geometry dimensions with provenance metadata; bounded gap slider to $\ge 15\text{ mm}$ (dielectric width $20\text{ mm}$) to strictly prevent mesh penetration. |
| **V0-R1-M4** | MEDIUM | Header mobile wrapping, unrendered LaTeX, modal focus trapping. | Added responsive flex-wrapping down to 375px; replaced raw LaTeX with semantic HTML math (`<i>E</i> &prop; 1/<i>r</i>`, `<i>T<sub>xx</sub></i> = &frac12;&epsilon;<sub>0</sub><i>E<sub>x</sub></i><sup>2</sup>`, `<i>F</i> &prop; <i>V</i><sup>2</sup>`); implemented modal focus trapping (`trapFocus`/`releaseFocus`). |

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
   - **Dielectric Barrier Block:** Semitransparent refractive epoxy potting ($\varepsilon_r = 3.8$).
   - **Structural Support Stand:** Non-conductive insulating mount.
   - **Conductive Enclosure:** Bounding stainless steel chamber walls with ground coupling.

3. **Switchable Visual Layers:**
   - Component Geometry
   - Electric Field Streamlines (color-coded $|\mathbf{E}|$ gradient from 0 V ground to -20 kV blade) & Equipotential Contours
   - Action-Reaction Force Vectors (schematic directions; labeled `SCHEMATIC / NOT TO SCALE`)
   - Chamber Enclosure & Wireframe Mode

4. **The Four Questions Guided Tour:**
   - *1. What am I seeing?* Asymmetric high-voltage cathode opposite planar ground collector.
   - *2. Why does it happen?* Sharp edge field concentration ($E \propto 1/r$) and Maxwell electrostatic tension ($T_{xx} = \frac{1}{2}\varepsilon_0 E_x^2$).
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
   - Dielectric Permittivity Slider ($\varepsilon_r \in [1, 5]$): adjusts dielectric opacity and polarization traction.
   - Gap Spacing Slider ($15 - 50\text{ mm}$): translates ground electrode and updates field geometry safely without mesh intersection.

7. **3D Raycaster Component Inspector:**
   - Click any 3D element—including enclosure walls—to view role, citations, operating potential, material, dimensions, and honest provenance badges (`ESTABLISHED MODEL`, `PUBLISHED HYPOTHESIS`, `WHAT-IF PARAMETER`).

---

## Verification & Integrity

- **Unit Tests:** 23 tests in `tests/test_v0_propulsion_explorer.py`, all passing (`Ran 23 tests in 0.039s, OK`).
- **Full Discovery Suite:** 95 tests total (35 P0 + 37 P1 + 23 V0 in 259.48s, all passing).
- **P0 Baseline Preservation:** `git hash-object electrostatics_baseline.py` = `97f65dfa25db7730323edd5e52c98b17371fdeaa` (byte-for-byte identical).
- **P1 Baseline Preservation:** All P1 source and test files match base SHA `8e1fdb32655d073002ae5a794b08e48f19a78a0f` byte-for-byte.
- **Track Separation:** Dedicated feature branch `v0-propulsion-explorer-3d` based directly on `main` after PR #12 merge. Track B (P2 PR #11) remains separate.
- **README Synchronized:** Progress narrative and "What already runs" updated in `README.md`, `AGENTS.md`, and `docs/ROADMAP.md` in this change.
- **Governance:** MANUAL-ONLY; DRAFT PR; no merge authorization granted.
