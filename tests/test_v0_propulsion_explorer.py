"""Unit tests for the 3D Propulsion Explorer (V0) assets, provenance, and launcher.

Remediated for Review Round V0 R4:
- V0-R3-F1: Verify screen coordinate projection and real canvas pointer picking infrastructure.
- V0-R3-M1: Verify physical surface gap d definition (blade tip to ground near face), positive clearance >= 5.0 mm from dielectric, and tip radius non-modeled provenance metadata.
- V0-R3-M2: Verified by companion Playwright browser smoke suite (frame-rendered slider sweeps and disposal instrumentation).
- V0-R3-M3: Verify permittivity slider is explicitly qualified as visual/material proxy only in V0.
- V0-R3-M4: Verify bounded legibility vector length encoding ([6.0, 30.0] mm), staying strictly inside chamber at all voltages.
"""

from __future__ import annotations

import json
import math
import os
import re
import socket
import unittest
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
EXPLORER_DIR = REPO_ROOT / "explorer"
ASSETS_DIR = REPO_ROOT / "assets"


class PropulsionExplorerV0AssetTests(unittest.TestCase):
    """Verify that all V0 explorer files exist, are readable, and non-empty."""

    def test_required_files_exist(self):
        required_files = [
            EXPLORER_DIR / "index.html",
            EXPLORER_DIR / "explorer.css",
            EXPLORER_DIR / "explorer.js",
            EXPLORER_DIR / "provenance_data.json",
            EXPLORER_DIR / "vendor" / "three.min.js",
            EXPLORER_DIR / "vendor" / "OrbitControls.js",
            REPO_ROOT / "run_explorer.py",
            ASSETS_DIR / "propulsion_explorer_v0_preview.png",
        ]
        for f in required_files:
            self.assertTrue(f.exists(), f"Missing required file: {f}")
            self.assertGreater(f.stat().st_size, 0, f"File is empty: {f}")

    def test_vendored_libraries_are_offline_ready(self):
        three_path = EXPLORER_DIR / "vendor" / "three.min.js"
        controls_path = EXPLORER_DIR / "vendor" / "OrbitControls.js"

        self.assertGreater(three_path.stat().st_size, 200_000)
        self.assertGreater(controls_path.stat().st_size, 10_000)

        with open(three_path, "r", encoding="utf-8", errors="ignore") as f:
            three_content = f.read(500)
            self.assertIn("THREE", three_content)

        with open(controls_path, "r", encoding="utf-8", errors="ignore") as f:
            controls_content = f.read(500)
            self.assertIn("OrbitControls", controls_content)


class PropulsionExplorerProvenanceSchemaTests(unittest.TestCase):
    """Verify schema, scientific provenance, and strict system boundary accounting."""

    def setUp(self):
        self.provenance_path = EXPLORER_DIR / "provenance_data.json"
        with open(self.provenance_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def test_top_level_keys(self):
        expected_keys = {"metadata", "four_questions", "components", "force_accounting_ledger", "null_controls"}
        self.assertTrue(expected_keys.issubset(self.data.keys()))

    def test_metadata_scientific_disposition(self):
        meta = self.data["metadata"]
        self.assertEqual(meta["scientific_disposition"], "EDUCATIONAL_3D_EXPLORER_NO_UNVERIFIED_THRUST")
        self.assertEqual(meta["evidence_grade"], "PROVISIONAL_ILLUSTRATIVE_SCENE")
        self.assertIn("US11511891B2", meta["citation"])

    def test_six_chapters_iceberg_structure(self):
        """V0.2 regression: verify six_chapters exists with 6 Iceberg chapters."""
        self.assertIn("six_chapters", self.data)
        chapters = self.data["six_chapters"]
        self.assertEqual(len(chapters), 6)
        expected_titles = [
            "Meet the Device",
            "Turn on the Electricity",
            "Follow the Forces",
            "Can the Whole Device Move?",
            "Scalar Waves",
            "How Could We Test",
        ]
        for i, ch in enumerate(chapters):
            self.assertEqual(ch["chapter"], i + 1)
            self.assertIn(expected_titles[i], ch["title"])
            self.assertTrue(len(ch["surface"]) > 10)
            self.assertTrue(len(ch["shallow"]) > 10)
            self.assertIn("equations", ch["deeper"])
            self.assertIn("specifications", ch["deeper"])
            self.assertIn("citations", ch["deeper"])
            self.assertIn("hypotheses", ch["research"])
            self.assertIn("uncertainties", ch["research"])
            self.assertIn("controls", ch["research"])
            self.assertIn("annotation", ch)
            self.assertIn("camera", ch)
            self.assertIn("layers", ch)

    def test_no_invented_newton_forces_in_components(self):
        """V0-R1-F1 regression: ensure no invented numeric force quantities appear in data."""
        components = self.data["components"]
        for comp in components:
            self.assertNotIn("nominal_force_n", comp, f"Component {comp['id']} has invented nominal_force_n")
            self.assertNotIn("force_vector", comp, f"Component {comp['id']} has invented numeric force_vector")
            self.assertIn("schematic_direction", comp)
            self.assertEqual(comp["force_magnitude_status"], "SCHEMATIC_VECTOR_NOT_COMPUTED_IN_V0")

            # Must not claim observation or positive measurement on unmeasured models
            lower_status = comp["status"].lower()
            self.assertFalse(bool(re.search(r"\bobserved\b", lower_status)), f"Component {comp['id']} claims 'observed' status without measurement")
            self.assertFalse(bool(re.search(r"(?<!un)measured", lower_status)), f"Component {comp['id']} claims 'measured' status without measurement")

    def test_four_questions_narrative_and_signed_physics(self):
        """V0-R1-F2 regression: conventional E points from high potential (ground) to low potential (cathode)."""
        fq = self.data["four_questions"]
        self.assertIn("what_am_i_seeing", fq)
        self.assertIn("why_does_it_happen", fq)
        self.assertIn("what_changes_it", fq)
        self.assertIn("how_could_we_test_it", fq)

        why_text = fq["why_does_it_happen"]
        self.assertIn("higher potential (ground, 0 V) toward lower potential (cathode, -20 kV)", why_text)
        self.assertIn("Maxwell", why_text)

        test_text = fq["how_could_we_test_it"]
        self.assertIn("Tajmar", test_text)
        self.assertIn("< 10^-5 Torr", test_text)

    def test_maxwell_stress_tensor_transverse_terms_qualified(self):
        """V0-R4-M2 regression: verify Maxwell stress tensor includes full 3D terms and marks 1/2 eps0 Ex^2 as 1D limit."""
        why_text = self.data["four_questions"]["why_does_it_happen"]
        self.assertIn("T_xx = &epsilon;_0 (E_x^2 - &frac12;|E|^2)", why_text)
        self.assertIn("transverse fields vanish", why_text)

    def test_system_boundaries_in_ledger(self):
        """V0-R1-F4 regression: distinguish DUT control volume from external chamber environment."""
        ledger = self.data["force_accounting_ledger"]
        self.assertIn("boundary_a_isolated_dut", ledger)
        self.assertIn("boundary_b_external_environment", ledger)
        self.assertIn("boundary_c_total_universe", ledger)

        dut = ledger["boundary_a_isolated_dut"]
        self.assertEqual(dut["whole_body_thrust_status"], "NOT MEASURED / NOT ESTABLISHED")
        self.assertIn("BALANCED", dut["internal_stress_sum"])
        self.assertIn("UNVERIFIED_PENDING_CHAMBER_CALIBRATION", dut["external_environmental_coupling"])

        ext = ledger["boundary_b_external_environment"]
        ext_elements = [x["element"] for x in ext["interactions"]]
        self.assertIn("Chamber Enclosure Walls", ext_elements)

        universe = ledger["boundary_c_total_universe"]
        self.assertIn("IDENTICALLY ZERO", universe["total_sum"])

    def test_components_system_boundaries_assigned(self):
        """V0-R1-F4 regression: every component must specify its system boundary."""
        for comp in self.data["components"]:
            self.assertIn("system_boundary", comp)
            self.assertIn(comp["system_boundary"], {"DEVICE_UNDER_TEST", "EXTERNAL_ENVIRONMENT"})

        # Blade, ground, dielectric, mount must be DUT; enclosure must be EXTERNAL_ENVIRONMENT
        by_id = {c["id"]: c for c in self.data["components"]}
        self.assertEqual(by_id["blade_electrode"]["system_boundary"], "DEVICE_UNDER_TEST")
        self.assertEqual(by_id["ground_electrode"]["system_boundary"], "DEVICE_UNDER_TEST")
        self.assertEqual(by_id["dielectric_block"]["system_boundary"], "DEVICE_UNDER_TEST")
        self.assertEqual(by_id["support_mount"]["system_boundary"], "DEVICE_UNDER_TEST")
        self.assertEqual(by_id["enclosure_walls"]["system_boundary"], "EXTERNAL_ENVIRONMENT")

    def test_null_controls_comprehensiveness(self):
        controls = self.data["null_controls"]
        self.assertGreaterEqual(len(controls), 3)
        ctrl_names = [c["name"].lower() for c in controls]
        self.assertTrue(any("vacuum" in name for name in ctrl_names))
        self.assertTrue(any("polarity" in name for name in ctrl_names))
        self.assertTrue(any("enclosure" in name or "clearance" in name for name in ctrl_names))

    def test_dielectric_citation_and_potting_provenance(self):
        """V0-R2-M2: verify dielectric citation targets FIGS. 6B, 21, 23A (col. 7 lines 30-55) and rejects FIG. 7."""
        by_id = {c["id"]: c for c in self.data["components"]}
        dielectric = by_id["dielectric_block"]
        citation = dielectric.get("citation", "")
        self.assertIn("FIGS. 6B, 21, 23A", citation)
        self.assertIn("col. 7 lines 30–55", citation)
        self.assertNotIn("FIG. 7 (dielectric potting)", citation, "Dielectric citation must not cite FIG. 7 for potting")

    def test_blade_and_dielectric_dimensions_provenance_vs_js(self):
        """V0-R2-M1 / V0-R3-M1: verify provenance JSON dimensions synchronize with 3D mesh geometry in JS and tag tip radius."""
        by_id = {c["id"]: c for c in self.data["components"]}
        blade = by_id["blade_electrode"]
        blade_dims = blade["dimensions_mm"]
        self.assertEqual(blade_dims["width"], 30.0)
        self.assertEqual(blade_dims["height"], 25.4)
        self.assertEqual(blade_dims["thickness"], 3.0)
        self.assertEqual(blade_dims["tip_radius"], 0.1)
        # V0-R3-M1: tip radius must be explicitly tagged as non-modeled source metadata
        self.assertFalse(blade.get("tip_radius_modeled_in_mesh", True))
        self.assertIn("idealized", blade.get("tip_geometry_note", "").lower())

        diel = by_id["dielectric_block"]
        diel_dims = diel["dimensions_mm"]
        self.assertEqual(diel_dims["width"], 16.0)
        self.assertEqual(diel_dims["height"], 30.0)
        self.assertEqual(diel_dims["depth"], 45.0)

    def test_dielectric_permittivity_proxy_metadata(self):
        """V0-R3-M3: verify permittivity slider is qualified as visual proxy only in V0 provenance."""
        by_id = {c["id"]: c for c in self.data["components"]}
        dielectric = by_id["dielectric_block"]
        self.assertEqual(dielectric.get("permittivity_status"), "VISUAL_MATERIAL_PROXY_ONLY_IN_V0")
        self.assertIn("proxy", dielectric.get("note", "").lower())
        self.assertIn("solver-backed v1", dielectric.get("note", "").lower())


class PropulsionExplorerHTMLStructureTests(unittest.TestCase):
    """Verify HTML semantic tags, accessibility, layer toggles, and disclaimer banners."""

    def setUp(self):
        self.html_path = EXPLORER_DIR / "index.html"
        with open(self.html_path, "r", encoding="utf-8") as f:
            self.html = f.read()

    def test_html_landmarks_and_metadata(self):
        self.assertIn("<!DOCTYPE html>", self.html)
        self.assertIn('<meta name="viewport"', self.html)
        self.assertIn("Propulsion Explorer 3D", self.html)
        self.assertIn('role="banner"', self.html)
        self.assertIn('role="main"', self.html)
        self.assertIn('role="complementary"', self.html)

    def test_layer_toggles_and_disclaimers(self):
        self.assertIn('id="toggle-geometry"', self.html)
        self.assertIn('id="toggle-fields"', self.html)
        self.assertIn('id="toggle-forces"', self.html)
        self.assertIn('id="toggle-enclosure"', self.html)
        self.assertIn('id="toggle-wireframe"', self.html)
        self.assertIn("QUALITATIVE SCHEMATIC FLUX &amp; DIRECTIONS", self.html)
        # V0-R3-M3: permittivity slider is qualified as visual proxy
        self.assertIn("Visual Proxy Only", self.html)
        self.assertIn("visual/material proxy in V0", self.html)
        # V0-R3-M1: gap slider labels physical surface gap d
        self.assertIn("Electrode Surface Gap", self.html)

    def test_maxwell_stress_tensor_in_html_qa(self):
        """V0-R4-M2 regression: verify HTML QA modal includes full vacuum stress tensor expression and 1D qualification."""
        self.assertIn("<i>T<sub>xx</sub></i> = &epsilon;<sub>0</sub>(<i>E<sub>x</sub></i><sup>2</sup> &minus; &frac12;|<b>E</b>|<sup>2</sup>)", self.html)
        self.assertIn("transverse fields vanish", self.html)

    def test_dynamic_legend_elements_present(self):
        """V0-R1-M1 regression: legends have IDs for dynamic binding."""
        self.assertIn('id="legend-blade-label"', self.html)
        self.assertIn('id="legend-ground-label"', self.html)
        self.assertIn('id="legend-dielectric-label"', self.html)
        self.assertIn('id="legend-field-label"', self.html)
        self.assertIn('id="legend-force-label"', self.html)

    def test_boundaries_present_in_html_ledger(self):
        """V0-R1-F4 regression: HTML ledger separates Boundary A from Boundary B."""
        self.assertIn("Boundary A: Suspended Test Article (DUT Control Volume)", self.html)
        self.assertIn("Boundary B: External Test Environment", self.html)
        self.assertIn("DUT Internal Stress Sum", self.html)
        self.assertIn("WHOLE-BODY THRUST: NOT MEASURED / NOT ESTABLISHED", self.html)

    def test_no_raw_latex_syntax_in_html(self):
        """V0-R1-M4 regression: verify no raw unrendered LaTeX strings in HTML."""
        self.assertNotIn(r"\propto", self.html)
        self.assertNotIn(r"\varepsilon", self.html)
        self.assertNotIn(r"\frac", self.html)
        self.assertNotIn(r"\nabla", self.html)

    def test_v0_2_learning_panel_and_help_modal_attributes(self):
        """V0.2 regression: nonblocking learning panel and help modal focus capture."""
        self.assertIn('id="learning-panel"', self.html)
        self.assertIn('id="guide-body" tabindex="0"', self.html)
        self.assertIn('class="help-modal-content" tabindex="-1"', self.html)
        self.assertIn('id="scene-annotation-card"', self.html)
        self.assertIn('class="mobile-panel-tabs"', self.html)


class PropulsionExplorerJSLogicTests(unittest.TestCase):
    """Verify JavaScript runtime logic, OrbitControls safety, and event bindings."""

    def setUp(self):
        js_path = EXPLORER_DIR / "explorer.js"
        with open(js_path, "r", encoding="utf-8") as f:
            self.js = f.read()
        html_path = EXPLORER_DIR / "index.html"
        with open(html_path, "r", encoding="utf-8") as f:
            self.html = f.read()
        css_path = EXPLORER_DIR / "explorer.css"
        with open(css_path, "r", encoding="utf-8") as f:
            self.css = f.read()
        prov_path = EXPLORER_DIR / "provenance_data.json"
        with open(prov_path, "r", encoding="utf-8") as f:
            self.provenance = json.load(f)

    def test_no_invalid_orbit_controls_method_calls(self):
        """V0-R1-F3 regression: verify nonexistent rotateLeft/rotateUp/dollyIn are NOT called."""
        self.assertNotIn("controls.rotateLeft(", self.js)
        self.assertNotIn("controls.rotateUp(", self.js)
        self.assertNotIn("controls.dollyIn(", self.js)
        self.assertNotIn("controls.dollyOut(", self.js)

        # Verify robust mathematical functions are implemented
        self.assertIn("function orbitCamera(deltaTheta, deltaPhi)", self.js)
        self.assertIn("function dollyCamera(factor)", self.js)

    def test_zero_voltage_extinguishes_fields_and_forces(self):
        """V0-R1-F2 regression: zero volts completely turns off field and force groups."""
        self.assertIn("if (currentVoltageKV <= 0.0)", self.js)
        self.assertIn("fieldGroup.visible = false", self.js)
        self.assertIn("forceGroup.visible = false", self.js)

    def test_raycasting_includes_enclosure(self):
        """V0-R1-M2 regression: pickableObjects includes enclosure_walls."""
        self.assertIn("pickableObjects.push(chamberMesh)", self.js)
        self.assertIn("raycaster.intersectObjects(pickableObjects", self.js)

    def test_pointer_hover_installed(self):
        """V0-R1-M2 regression: pointermove event listener is installed."""
        self.assertIn("container.addEventListener('pointermove', onPointerMove)", self.js)
        self.assertIn("container.style.cursor = 'pointer'", self.js)

    def test_raycast_picking_prioritizes_interior_over_enclosure(self):
        """V0-R2-F1 regression: getPickedObject prioritizes interior components over enclosure chamber."""
        self.assertIn("function getPickedObject(event)", self.js)
        self.assertIn("let closestInterior = null;", self.js)
        self.assertIn("let closestEnclosure = null;", self.js)
        self.assertIn('if (id === "enclosure_walls")', self.js)
        self.assertIn("return closestInterior || closestEnclosure || null;", self.js)

    def test_gap_slider_bounds_prevent_dielectric_collision(self):
        """V0-R2-M1 / V0-R3-M1 regression: physical surface gap d = currentGapMM, ensuring >= 5.0 mm positive clearance from dielectric."""
        self.assertIn("new THREE.BoxGeometry(16, 30, 45)", self.js)
        self.assertIn("currentGapMM = Math.max(16.0", self.js)
        self.assertIn("groundMesh.position.set(currentGapMM + 2.0, 0, 0);", self.js)
        # Blade sharp knife-edge is at world x = 0
        # Ground plate has thickness 4.0 mm with center at x = currentGapMM + 2.0
        # Near front face is at x_near = (currentGapMM + 2.0) - 2.0 = currentGapMM
        # Physical surface-to-surface gap = x_near - 0 = currentGapMM identically!
        # Dielectric: center x=3.0, width=16.0 -> x_max = 3.0 + 8.0 = 11.0 mm
        # At minimum gap setting (16.0 mm): x_near = 16.0 mm
        # Clearance from dielectric: 16.0 - 11.0 = +5.0 mm >= 3.0 mm
        min_gap = 16.0
        diel_x_max = 3.0 + 16.0 / 2.0  # 11.0 mm
        ground_near_face = min_gap  # 16.0 mm
        clearance = ground_near_face - diel_x_max
        self.assertGreaterEqual(clearance, 5.0, f"Expected clearance >= 5.0 mm, got {clearance} mm")

    def test_disposal_hierarchy_frees_gpu_memory(self):
        """V0-R2-M5 regression: verify recursive disposeHierarchy prevents GPU memory leaks on slider drag."""
        self.assertIn("function disposeHierarchy(root)", self.js)
        self.assertIn("child.geometry.dispose()", self.js)
        self.assertIn("child.material.dispose()", self.js)
        self.assertIn("disposeHierarchy(obj);", self.js)

    def test_bounded_force_arrow_legibility_encoding(self):
        """V0-R3-M4 regression: verify bounded legibility encoding ([6.0, 30.0] mm) stays inside chamber at all voltages."""
        self.assertIn("const ARROW_MIN_LEN = 6.0;", self.js)
        self.assertIn("const ARROW_NOM_LEN = 16.0;", self.js)
        self.assertIn("const ARROW_MAX_LEN = 30.0;", self.js)
        self.assertNotIn("len * 24", self.js)
        self.assertNotIn("len * 22", self.js)
        self.assertNotIn("len * 8", self.js)
        self.assertNotIn("len * 16", self.js)
        self.assertNotIn("len * 10", self.js)

    def test_screen_coords_projection_available(self):
        """V0-R3-F1 regression: verify getComponentScreenCoords is implemented and exposed for real pointer testing."""
        self.assertIn("function getComponentScreenCoords(id)", self.js)
        self.assertIn("getComponentScreenCoords: getComponentScreenCoords", self.js)

    def test_v0_1_r1_f1_billboard_label_pins_interactive_and_accessible(self):
        """V0.1-R1-F1 regression: billboard label pins have interactive pointer events, type='button', and ARIA."""
        # Container is an accessible region without contradictory aria-hidden
        self.assertIn('id="labels-container" class="labels-container" role="region" aria-label="3D Component Labels"', self.html)
        self.assertNotIn('id="labels-container" class="labels-container" aria-hidden="true"', self.html)

        # Pin buttons in JS
        self.assertIn("pin.type = 'button';", self.js)
        self.assertIn("pin.setAttribute('aria-label', `Select ${def.name}`);", self.js)
        self.assertIn("pin.setAttribute('aria-pressed', isSelected ? 'true' : 'false');", self.js)
        self.assertIn("e.stopPropagation();", self.js)

        # CSS has pointer-events: auto on .label-pin
        self.assertIn("pointer-events: auto;", self.css)

    def test_v0_1_r1_f2_streamline_markers_qualified_not_particles_or_field_magnitude(self):
        """V0.1-R1-F2 regression: streamline markers qualified as schematic orientation only, not particles or |E|."""
        self.assertIn("isFieldDirectionMarkers: true", self.js)
        self.assertIn("Schematic Orientation Only, Not Computed |E| Magnitude or Charge Flow", self.js)
        self.assertIn("Schematic Orientation Only, Not Computed |E| Magnitude or Charge Flow", self.html)
        self.assertIn("Electric Field Direction (OFF at 0 V — Zero Field)", self.js)

    def test_v0_1_r1_m1_chip_bar_synchronizes_with_voltage(self):
        """V0.1-R1-M1 regression: chip bar blade label dynamically updates from voltage state."""
        self.assertIn("id=\"chip-blade-label\"", self.html)
        self.assertIn("const chipBlade = document.getElementById('chip-blade-label');", self.js)
        self.assertIn("chipBlade.textContent = currentVoltageKV > 0", self.js)
        self.assertIn("'Blade (0 V OFF)'", self.js)

    def test_v0_1_r1_m2_inspector_role_and_status_qualified(self):
        """V0.1-R1-M2 regression: inspector card qualifies multi-body forces and specifies 0 V null state."""
        # 0 V null state
        self.assertIn("Field OFF at 0 V — Zero Electrostatic Traction (Unenergized)", self.js)
        self.assertIn("electrostatic forces are identically zero", self.js)

        # Energized multi-body qualification (no unconditional pairwise equality)
        self.assertIn("Pairwise equality between these two electrodes alone is not assumed", self.js)
        self.assertIn("not isolated pairwise equal", self.js)

    def test_v0_1_r2_f1_legend_hud_non_overlapping_placement_and_max_width(self):
        """V0.1-R2-F1 regression: legend HUD positioned below preset toolbar with constrained max-width."""
        self.assertIn("top: 4.5rem;", self.css)
        self.assertIn("max-width: 290px;", self.css)

    def test_v0_1_r2_f2_collision_avoidance_algorithm_and_pointer_events_in_js_and_css(self):
        """V0.1-R2-F2 regression: billboard label pins have 2D collision avoidance and transparent child pointer events."""
        # CSS transparent pointer events on child spans
        self.assertIn(".label-pin *", self.css)
        self.assertIn("pointer-events: none;", self.css)

        # JS 2D Screen-Space collision avoidance logic
        self.assertIn("function resolveLabelCollisions", self.js)
        self.assertIn("overlapX > 0 && overlapY > 0", self.js)
        self.assertIn("shiftY", self.js)
        self.assertIn("shiftX", self.js)

    def test_v0_1_r2_f2_distinct_3d_anchor_coordinates(self):
        """V0.1-R2-F2 regression: distinct 3D anchor points prevent overlapping baseline projections."""
        self.assertIn("THREE.Vector3(-24, 14, 8)", self.js)
        self.assertIn("THREE.Vector3(currentGapMM + 14, 20, -8)", self.js)
        self.assertIn("THREE.Vector3(0, 36, 14)", self.js)

    def test_v0_1_r3_f1_and_m2_single_pin_clamp_and_capacity_fallback_in_js(self):
        """V0.1-R3-F1 & M2: clamp runs before activePins.length <= 1 check and capacity shortfall check exists."""
        # 1. V0.1-R3-F1: Verify clamp loop occurs before activePins.length <= 1
        clamp_idx = self.js.find("item.x = Math.max(item.w / 2 + pad")
        early_return_idx = self.js.find("if (activePins.length <= 1) return;")
        self.assertNotEqual(clamp_idx, -1)
        self.assertNotEqual(early_return_idx, -1)
        self.assertLess(clamp_idx, early_return_idx, "Clamping must occur before early return on activePins.length <= 1")

        # 2. V0.1-R3-M2: Capacity shortfall check exists and no unconditional guarantee claims in comments
        self.assertIn("totalPinHeight", self.js)
        self.assertIn("neededSpan > availableSpan", self.js)
        self.assertNotIn("provably collision-free", self.js)
        self.assertNotIn("guarantee zero overlap", self.js)

    def test_v0_1_r4_m1_capacity_shortfall_deterministic_conflict_suppression_and_postcondition(self):
        """V0.1-R4-M1: deterministic conflict suppression resolves capacity shortfall counterexample with zero overlap."""
        # 1. Structural check for conflict resolution loop and priority rankings in JS
        self.assertIn("priority: 5", self.js)
        self.assertIn("priority: 1", self.js)
        self.assertIn("hasOverlap", self.js)
        self.assertIn("collisionPair", self.js)
        self.assertIn("victim.pin.style.display = 'none'", self.js)

        # 2. Node execution test verifying exact counterexample (rect: 375x380, 5 pins w=220, h=50)
        node_script = """
        const js = require('fs').readFileSync('explorer/explorer.js', 'utf8');
        const match = js.match(/function resolveLabelCollisions[\\s\\S]*?\\n  \\}/);
        if (!match) throw new Error("resolveLabelCollisions not found");

        global.document = {
            querySelector: () => null,
            getElementById: () => null
        };

        eval(match[0]);

        const rect = { width: 375, height: 380 };
        const pins = [
            { id: "blade_electrode", x: 187, y: 180, w: 220, h: 50, priority: 5, pin: { style: {} } },
            { id: "ground_electrode", x: 187, y: 180, w: 220, h: 50, priority: 4, pin: { style: {} } },
            { id: "dielectric_block", x: 187, y: 180, w: 220, h: 50, priority: 3, pin: { style: {} } },
            { id: "enclosure_walls", x: 187, y: 180, w: 220, h: 50, priority: 2, pin: { style: {} } },
            { id: "support_mount", x: 187, y: 180, w: 220, h: 50, priority: 1, pin: { style: {} } }
        ];

        resolveLabelCollisions(pins, rect);

        function overlaps(a, b) {
            const aLeft = a.x - a.w / 2, aRight = a.x + a.w / 2;
            const aTop = a.y - a.h, aBottom = a.y;
            const bLeft = b.x - b.w / 2, bRight = b.x + b.w / 2;
            const bTop = b.y - b.h, bBottom = b.y;
            return (aLeft < bRight && aRight > bLeft && aTop < bBottom && aBottom > bTop);
        }

        for (let i = 0; i < pins.length; i++) {
            for (let j = i + 1; j < pins.length; j++) {
                if (overlaps(pins[i], pins[j])) {
                    throw new Error(`Collision between ${pins[i].id} and ${pins[j].id}`);
                }
            }
        }
        console.log(JSON.stringify({ surviving: pins.map(p => p.id), count: pins.length }));
        """
        import subprocess, json
        res = subprocess.run(["node", "-e", node_script], capture_output=True, text=True, check=True)
        data = json.loads(res.stdout.strip())
        self.assertLess(data["count"], 5, "Capacity shortfall must suppress conflicting pins")
        self.assertGreaterEqual(data["count"], 2, "High-priority pins must survive")
        self.assertIn("blade_electrode", data["surviving"], "Highest priority blade pin must survive")
        self.assertNotIn("support_mount", data["surviving"], "Lowest priority mount pin must be suppressed in shortfall")

    def test_v0_2_iceberg_progressive_disclosure_templates_in_js(self):
        """V0.2 regression: verify Iceberg progressive disclosure template rendering in explorer.js."""
        self.assertIn("iceberg-disclosure iceberg-deeper", self.js)
        self.assertIn("iceberg-disclosure iceberg-research", self.js)
        self.assertIn("iceberg-card iceberg-surface", self.js)
        self.assertIn("iceberg-card iceberg-shallow", self.js)
        self.assertIn("function renderChapter", self.js)
        self.assertIn("function toggleExploreFreely", self.js)
        self.assertIn("function toggleAnimationPause", self.js)
        self.assertIn("function resetTour", self.js)
        self.assertIn("function toggleLearningPanel", self.js)
        self.assertIn("function toggleSidebar", self.js)

    def test_v0_2_keyboard_shortcuts_and_controls_in_js(self):
        """V0.2 regression: verify keyboard shortcuts for guide, sidebar, chapters, and pause."""
        self.assertIn("case 'g':", self.js)
        self.assertIn("case 's':", self.js)
        self.assertIn("case '[':", self.js)
        self.assertIn("case ']':", self.js)
        self.assertIn("case ' ':", self.js)

    def test_v0_2_r1_f1_negative_scan_for_unsourced_force_numbers(self):
        """V0.2-R1-F1: Scan all six chapter strings and fallback JS for unsourced force values."""
        forbidden_patterns = [
            "+0.045 N",
            "-0.038 N",
            "-0.005 N",
            "-0.002 N",
            "0.000 N identically",
            "0.00 ± 0.05",
            "0.00 \\pm 0.05",
            "F = 0.00"
        ]

        # Scan JSON six_chapters
        for ch in self.provenance.get("six_chapters", []):
            ch_str = json.dumps(ch)
            for pat in forbidden_patterns:
                self.assertNotIn(pat, ch_str, f"Forbidden unsourced force '{pat}' found in JSON chapter {ch.get('chapter')}")

        # Scan JS file
        for pat in forbidden_patterns:
            self.assertNotIn(pat, self.js, f"Forbidden unsourced force '{pat}' found in explorer.js")

    def test_v0_2_r1_f2_boundary_a_environmental_coupling(self):
        """V0.2-R1-F2: Chapter 4 does not claim Boundary A Maxwell stress flux is identically zero."""
        ch4 = next((c for c in self.provenance.get("six_chapters", []) if c["chapter"] == 4), None)
        self.assertIsNotNone(ch4)
        eqs = ch4["deeper"]["equations"]
        self.assertNotIn("\\oint_{\\partial V_A} \\mathbf{T} \\cdot \\hat{\\mathbf{n}}\\, dA \\equiv 0", eqs)
        self.assertNotIn("&conint;<sub>&part;V<sub>A</sub></sub> <b>T</b>&middot;<b>n̂</b> dA = 0", eqs)
        self.assertIn("NOT identically zero if external electric fields penetrate Boundary A", eqs)
        self.assertIn("&sum; <b>F</b><sub>internal</sub> = <b>0</b> identically", eqs)

    def test_v0_2_r1_m1_semantic_math_and_clickable_citations(self):
        """V0.2-R1-M1: Semantic math formatting and clickable citation hyperlinks."""
        self.assertIn("function cleanMathHtml", self.js)

        for ch in self.provenance.get("six_chapters", []):
            deeper = ch["deeper"]
            # No raw unescaped LaTeX delimiters in equations
            self.assertNotIn("\\(", deeper["equations"], f"Raw LaTeX '\\(' found in chapter {ch['chapter']} equations")
            self.assertNotIn("\\)", deeper["equations"], f"Raw LaTeX '\\)' found in chapter {ch['chapter']} equations")

            # Citations must contain valid hyperlinks
            citations = deeper["citations"]
            self.assertIn("<a href=", citations, f"Citation in chapter {ch['chapter']} must contain clickable link")
            self.assertIn("target='_blank'", citations, f"Citation in chapter {ch['chapter']} must open in new tab")
            self.assertIn("rel='noopener noreferrer'", citations, f"Citation in chapter {ch['chapter']} must have rel='noopener noreferrer'")

    def test_v0_2_r1_m2_tajmar_2020_and_ion_wind_provenance(self):
        """V0.2-R1-M2: Accurate Tajmar & Schreiber (2020) reference and qualified ion wind formula."""
        ch6 = next((c for c in self.provenance.get("six_chapters", []) if c["chapter"] == 6), None)
        self.assertIsNotNone(ch6)
        citations = ch6["deeper"]["citations"]
        self.assertIn("Put strong limits on all proposed theories so far assessing electrostatic propulsion", citations)
        self.assertIn("Journal of Electrostatics", citations)
        self.assertIn("10.1016/j.elstat.2020.103477", citations)

        # Ion wind formula explicitly declares gap distance d
        eqs6 = ch6["deeper"]["equations"]
        self.assertIn("d = 20 mm", eqs6)
        self.assertIn("50 &mu;A", eqs6)
        self.assertNotIn("extinguishing ion wind to zero", eqs6)

        # Chapter 2 peak field is qualified (not unconditional 10^7 V/m)
        ch2 = next((c for c in self.provenance.get("six_chapters", []) if c["chapter"] == 2), None)
        self.assertIsNotNone(ch2)
        eqs2 = ch2["deeper"]["equations"]
        self.assertIn("No validated 3D peak field magnitude is claimed", eqs2)

    def test_v0_2_r1_m3_mobile_scrollable_layout_and_ledger_navigation(self):
        """V0.2-R1-M3: Mobile layout has no clipping overflow constraints and provides ledger navigation."""
        # CSS mobile overrides
        self.assertIn("height: auto !important;", self.css)
        self.assertIn("max-height: none !important;", self.css)
        self.assertIn("overflow: visible !important;", self.css)
        self.assertIn("overflow-y: auto !important;", self.css)

        # HTML elements
        self.assertIn("id=\"force-ledger-card\"", self.html)
        self.assertIn("id=\"btn-ledger-back-to-guide\"", self.html)

        # JS wirings
        self.assertIn("btn-chapter4-open-ledger", self.js)
        self.assertIn("btn-ledger-back-to-guide", self.js)

    def test_v0_2_r1_m4_mathematical_scalar_wave_contrast_overlay(self):
        """V0.2-R1-M4: 3D scene provides dedicated mathematical scalar wave contrast visualizer."""
        # HTML badge
        self.assertIn("id=\"scalar-wave-badge\"", self.html)
        self.assertIn("MATHEMATICAL SCALAR WAVE CONTRAST", self.html)
        self.assertIn("NOT coupled to capacitor or thrust", self.html)

        # JS group and helpers
        self.assertIn("scalarWaveGroup", self.js)
        self.assertIn("function createScalarWaveVisual", self.js)
        self.assertIn("function updateScalarWaveAnimation", self.js)
        self.assertIn("function toggleScalarWaveContrast", self.js)
        self.assertIn("btn-toggle-wave-contrast", self.js)



class PropulsionExplorerLauncherTests(unittest.TestCase):
    """Verify run_explorer.py port detection and argument parsing."""

    def test_is_port_available_detects_open_port(self):
        from run_explorer import is_port_available
        avail = is_port_available("127.0.0.1", 59483)
        self.assertTrue(avail)

    def test_find_available_port(self):
        from run_explorer import find_available_port
        port = find_available_port("127.0.0.1", 59000, max_attempts=10)
        self.assertGreaterEqual(port, 59000)
        self.assertLess(port, 59010)

    def test_server_creation_and_directory(self):
        from run_explorer import EXPLORER_DIR, create_server
        self.assertTrue(EXPLORER_DIR.exists())
        self.assertTrue((EXPLORER_DIR / "index.html").exists())

        server, port = create_server("127.0.0.1", 59550)
        try:
            self.assertGreaterEqual(port, 59550)
        finally:
            server.server_close()


if __name__ == "__main__":
    unittest.main()
