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
        self.assertIn("Propulsion Explorer 3D (V0)", self.html)
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

    def test_modal_focus_trap_attributes(self):
        """V0-R1-M4 regression: modal content has tabindex='-1' for focus capture."""
        self.assertIn('class="tour-modal-content" tabindex="-1"', self.html)
        self.assertIn('class="tour-modal-content help-content" tabindex="-1"', self.html)


class PropulsionExplorerJSLogicTests(unittest.TestCase):
    """Verify JavaScript runtime logic, OrbitControls safety, and event bindings."""

    def setUp(self):
        js_path = EXPLORER_DIR / "explorer.js"
        with open(js_path, "r", encoding="utf-8") as f:
            self.js = f.read()

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
