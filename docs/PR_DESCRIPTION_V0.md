# V0 — Build the first visual-first 3D Propulsion Explorer demo (#13)

## Summary of Changes

Delivers **Milestone V0: The first working, beginner-friendly 3D Propulsion Explorer** on dedicated feature branch `v0-propulsion-explorer-3d`, implementing the user's visual-first north star from [Issue #13](https://github.com/aguacatero/scalar-wave-viz/issues/13) and [docs/PROPULSION_EXPLORER_VISION.md](docs/PROPULSION_EXPLORER_VISION.md).

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
```

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
   - Electric Field Streamlines (color-coded $|\mathbf{E}|$ gradient from high-voltage blade tip to ground) & Equipotential Contours
   - Action-Reaction Force Vectors (labeled `SCHEMATIC / NOT TO SCALE`)
   - Chamber Enclosure & Wireframe Mode

4. **The Four Questions Guided Tour:**
   - *1. What am I seeing?* Asymmetric high-voltage cathode opposite planar ground collector.
   - *2. Why does it happen?* Sharp edge field concentration ($E \propto 1/r$) and Maxwell electrostatic tension ($T_{xx} = \frac{1}{2}\varepsilon_0 E_x^2$).
   - *3. What changes it?* Quadratic voltage scaling ($F \propto V^2$), geometry sharpness, dielectric permittivity, and chamber wall distance.
   - *4. How could we test it?* Micro-Newton torsion pendulum in high vacuum ($< 10^{-5}\text{ Torr}$) with null controls for ion wind and electrostatic wall coupling.

5. **Strict Action-Reaction Force Ledger & Fail-Closed Status:**
   - Whole-body table verifying $F_{\text{blade}} (+0.045\text{ N}) + F_{\text{ground}} (-0.038\text{ N}) + F_{\text{dielectric}} (-0.005\text{ N}) + F_{\text{walls}} (-0.002\text{ N}) = 0.000\text{ N}$.
   - Prominent status banner: `WHOLE-BODY THRUST: NOT MEASURED / NOT ESTABLISHED`.
   - Clear explanation that internal electrode traction does not constitute net propellantless thrust.

6. **What-If Parameter Sandbox:**
   - Voltage Slider ($0 - 50\text{ kV}$): dynamically scales field streamlines and force vectors ($\propto V^2$).
   - Dielectric Permittivity Slider ($\varepsilon_r \in [1, 5]$): adjusts dielectric opacity and polarization traction.
   - Gap Spacing Slider ($10 - 50\text{ mm}$): translates ground electrode and updates field geometry.

7. **3D Raycaster Component Inspector:**
   - Click any 3D element to view role, citations, operating potential, material, dimensions, and honest provenance badges (`ESTABLISHED MODEL`, `PUBLISHED HYPOTHESIS`, `WHAT-IF PARAMETER`).

---

## Verification & Integrity

- **Unit Tests:** 17 tests added in `tests/test_v0_propulsion_explorer.py`, all passing (`Ran 17 tests in 0.044s, OK`).
- **Full Discovery Suite:** 89 tests total (35 P0 + 37 P1 + 17 V0).
- **P0 Baseline Preservation:** `git hash-object electrostatics_baseline.py` = `97f65dfa25db7730323edd5e52c98b17371fdeaa` (byte-for-byte identical).
- **P1 Baseline Preservation:** All P1 source and test files match base SHA `8e1fdb32655d073002ae5a794b08e48f19a78a0f` byte-for-byte.
- **Track Separation:** Dedicated feature branch `v0-propulsion-explorer-3d` based directly on `main` after PR #12 merge. Track B (P2 PR #11) remains separate.
- **README Synchronized:** Progress narrative and "What already runs" updated in `README.md`, `AGENTS.md`, and `docs/ROADMAP.md` in this change.
- **Governance:** MANUAL-ONLY; DRAFT PR; no merge authorization granted.
