"""Unit tests for the 3D Propulsion Explorer (V0) assets, provenance, and launcher.

Verifies:
1. File structure and asset completeness for zero-dependency offline operation.
2. Semantic schema and scientific integrity of provenance_data.json.
3. Strict conservation of whole-body forces and fail-closed disclaimer assertions.
4. HTML accessibility, semantic structure, and 4-question educational narrative.
5. run_explorer.py configuration, argument handling, and port discovery.
"""

from __future__ import annotations

import json
import math
import os
import re
import socket
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
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

        # Three.js should be substantial (> 200 KB)
        self.assertGreater(three_path.stat().st_size, 200_000)
        # OrbitControls should be substantial (> 10 KB)
        self.assertGreater(controls_path.stat().st_size, 10_000)

        with open(three_path, "r", encoding="utf-8", errors="ignore") as f:
            three_content = f.read(500)
            self.assertIn("THREE", three_content)

        with open(controls_path, "r", encoding="utf-8", errors="ignore") as f:
            controls_content = f.read(500)
            self.assertIn("OrbitControls", controls_content)


class PropulsionExplorerProvenanceSchemaTests(unittest.TestCase):
    """Verify schema, scientific provenance, and strict whole-body force conservation."""

    def setUp(self):
        self.provenance_path = EXPLORER_DIR / "provenance_data.json"
        with open(self.provenance_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def test_top_level_keys(self):
        expected_keys = {"metadata", "four_questions", "components", "whole_body_ledger", "null_controls"}
        self.assertTrue(expected_keys.issubset(self.data.keys()))

    def test_metadata_scientific_disposition(self):
        meta = self.data["metadata"]
        self.assertEqual(meta["scientific_disposition"], "EDUCATIONAL_3D_EXPLORER_NO_UNVERIFIED_THRUST")
        self.assertEqual(meta["evidence_grade"], "PROVISIONAL_ILLUSTRATIVE_SCENE")
        self.assertIn("US11511891B2", meta["citation"])

    def test_four_questions_narrative_present(self):
        fq = self.data["four_questions"]
        self.assertIn("what_am_i_seeing", fq)
        self.assertIn("why_does_it_happen", fq)
        self.assertIn("what_changes_it", fq)
        self.assertIn("how_could_we_test_it", fq)

        # Content checks
        self.assertIn("US11511891B2", fq["what_am_i_seeing"])
        self.assertIn("Maxwell", fq["why_does_it_happen"])
        self.assertIn("V^2", fq["what_changes_it"])
        self.assertIn("Tajmar", fq["how_could_we_test_it"])

    def test_components_schema_and_provenance_badges(self):
        valid_badges = {
            "ESTABLISHED MODEL",
            "PUBLISHED HYPOTHESIS",
            "WHAT-IF PARAMETER",
            "UNVERIFIED NUMERICAL OUTPUT",
            "EXPERIMENTAL MEASUREMENT",
        }
        components = self.data["components"]
        self.assertGreaterEqual(len(components), 4)

        component_ids = [c["id"] for c in components]
        self.assertIn("blade_electrode", component_ids)
        self.assertIn("ground_electrode", component_ids)
        self.assertIn("dielectric_block", component_ids)
        self.assertIn("enclosure_walls", component_ids)

        for comp in components:
            self.assertIn("id", comp)
            self.assertIn("name", comp)
            self.assertIn("role", comp)
            self.assertIn("citation", comp)
            self.assertIn("provenance_badge", comp)
            self.assertIn(comp["provenance_badge"], valid_badges)
            self.assertIn("status", comp)
            # Ensure no component falsely claims thrust
            self.assertNotIn("thrust achieved", comp["status"].lower())
            self.assertNotIn("propulsion verified", comp["status"].lower())

    def test_whole_body_ledger_strict_conservation(self):
        ledger = self.data["whole_body_ledger"]

        # Whole body thrust must be unestablished
        self.assertEqual(ledger["whole_body_thrust_status"], "NOT MEASURED / NOT ESTABLISHED")

        # Sum of forces in conventional electrostatics must be 0.0
        f_blade = ledger["blade_traction_n"]
        f_ground = ledger["ground_reaction_n"]
        f_diel = ledger["dielectric_traction_n"]
        f_wall = ledger["enclosure_reaction_n"]
        total_sum = f_blade + f_ground + f_diel + f_wall

        self.assertAlmostEqual(total_sum, 0.0, places=4, msg="Action-reaction balance violated in ledger")
        self.assertEqual(ledger["net_closed_system_force_n"], 0.000)

        # Conservation statement must be present and unequivocal
        stmt = ledger["scientific_statement"].lower()
        self.assertIn("sum identically to zero", stmt)
        self.assertIn("does not produce net propellantless thrust", stmt)

    def test_null_controls_comprehensiveness(self):
        controls = self.data["null_controls"]
        self.assertGreaterEqual(len(controls), 3)

        ctrl_names = [c["name"].lower() for c in controls]
        self.assertTrue(any("vacuum" in name for name in ctrl_names), "Missing high-vacuum control")
        self.assertTrue(any("polarity" in name for name in ctrl_names), "Missing polarity inversion control")
        self.assertTrue(any("enclosure" in name or "clearance" in name for name in ctrl_names), "Missing wall clearance control")


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

    def test_layer_toggles_present(self):
        self.assertIn('id="toggle-geometry"', self.html)
        self.assertIn('id="toggle-fields"', self.html)
        self.assertIn('id="toggle-forces"', self.html)
        self.assertIn('id="toggle-enclosure"', self.html)
        self.assertIn('id="toggle-wireframe"', self.html)
        self.assertIn("SCHEMATIC / NOT TO SCALE", self.html)

    def test_what_if_sliders_present(self):
        self.assertIn('id="slider-voltage"', self.html)
        self.assertIn('id="slider-eps"', self.html)
        self.assertIn('id="slider-gap"', self.html)
        self.assertIn("WHAT-IF PARAMETER", self.html)

    def test_whole_body_thrust_banner_not_established(self):
        self.assertIn("WHOLE-BODY THRUST: NOT MEASURED / NOT ESTABLISHED", self.html)
        self.assertIn("internal mechanical stress", self.html.lower())
        self.assertIn("sum to zero", self.html.lower())

    def test_no_fictitious_or_unqualified_thrust_claims(self):
        lower_html = self.html.lower()
        self.assertNotIn("propellantless propulsion achieved", lower_html)
        self.assertNotIn("anomalous thrust measured", lower_html)
        self.assertNotIn("scalar wave thrust detected", lower_html)

    def test_vendor_scripts_loaded_locally(self):
        self.assertIn('src="vendor/three.min.js"', self.html)
        self.assertIn('src="vendor/OrbitControls.js"', self.html)
        self.assertIn('src="explorer.js"', self.html)


class PropulsionExplorerLauncherTests(unittest.TestCase):
    """Verify run_explorer.py port detection and argument parsing."""

    def test_is_port_available_detects_open_port(self):
        from run_explorer import is_port_available
        # An unused high port should be available
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

        # Test creating server on an ephemeral high port
        server, port = create_server("127.0.0.1", 59550)
        try:
            self.assertGreaterEqual(port, 59550)
        finally:
            server.server_close()


if __name__ == "__main__":
    unittest.main()
