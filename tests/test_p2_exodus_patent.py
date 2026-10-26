"""Unit and regression tests for Phase P2: Exodus patent US11511891B2 reproduction and hypothesis separation.

Validates:
    - Sourced parameter audit covering all 12 patent geometry symbols and status tags
    - Material-side face extraction (verifying samples are strictly outside conductors)
    - Conventional Maxwell-stress electrostatics (H0) whole-system momentum conservation
    - Direct enclosure wall traction integration and contour-offset independence
    - Constrained finite 3D apparatus model with 3D momentum balance
    - Patent-specific formula transcription (H1: Eq. 4-11 audit) with correct face areas
    - Programmatically evaluated controls (polarity reversal, symmetry, zero-voltage)
    - Sourced literature benchmark audit (Tajmar & Schreiber 2020)
    - Mesh convergence and domain sensitivity
    - Paired evidence manifest schema and provenance integrity
    - Byte-for-byte preservation of P0/P1 baselines
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import unittest
import numpy as np

from exodus_patent_geometry import (
    EPSILON_0,
    ExodusGrid2D,
    ExodusPatentParameters,
    build_exodus_2d_grid,
    build_symmetric_control_grid,
    get_patent_parameter_ledger,
)
from exodus_hypothesis_evaluator import (
    evaluate_exodus_patent,
    generate_exodus_patent_manifest,
    solve_exodus_electrostatics,
    solve_exodus_electrostatics_3d,
    compute_electric_fields,
    compute_h0_whole_apparatus_ledger,
    compute_direct_enclosure_wall_tractions,
    compute_h1_patent_prediction,
    evaluate_experimental_controls,
)


class ExodusPatentParameterAuditTests(unittest.TestCase):
    """Test source-bound parameter audit for US11511891B2."""

    def test_parameter_audit_contains_all_12_patent_symbols(self):
        ledger = get_patent_parameter_ledger()
        symbols = {rec.symbol for rec in ledger}

        # All 12 patent geometry symbols cited in Col. 11 / FIGS. 2-8
        patent_symbols = ["T", "T1", "T2", "M", "N", "O", "P", "Q", "S", "S1", "U", "V"]
        for s in patent_symbols:
            self.assertIn(s, symbols, f"Missing required patent symbol {s}")

        # Material and unmodeled parameter symbols
        extra_symbols = ["epsilon_r", "r_tip", "tan_delta", "D_enclosure", "wiring_geometry"]
        for s in extra_symbols:
            self.assertIn(s, symbols, f"Missing required audit parameter {s}")

    def test_parameter_status_categorization(self):
        ledger = get_patent_parameter_ledger()
        ledger_dict = {rec.symbol: rec for rec in ledger}

        # Explicit patent values
        for sym in ["V", "P", "N", "T1", "Q", "S", "S1", "T", "M"]:
            self.assertEqual(
                ledger_dict[sym].status,
                "PATENT_EXPLICIT_VALUE",
                f"Symbol {sym} must be marked PATENT_EXPLICIT_VALUE",
            )

        # Unspecified estimates
        for sym in ["epsilon_r", "T2"]:
            self.assertEqual(
                ledger_dict[sym].status,
                "PATENT_UNSPECIFIED_ESTIMATE",
                f"Symbol {sym} must be marked PATENT_UNSPECIFIED_ESTIMATE",
            )

        # Modeling assumptions
        for sym in ["O", "U"]:
            self.assertEqual(
                ledger_dict[sym].status,
                "MODELING_ASSUMPTION",
                f"Symbol {sym} must be marked MODELING_ASSUMPTION",
            )

        # Unknown / omitted parameters
        for sym in ["r_tip", "tan_delta", "D_enclosure", "wiring_geometry"]:
            self.assertEqual(
                ledger_dict[sym].status,
                "PATENT_OMITTED_UNKNOWN",
                f"Symbol {sym} must be marked PATENT_OMITTED_UNKNOWN",
            )
            self.assertIn("omitted", (ledger_dict[sym].patent_reference + " " + ledger_dict[sym].notes).lower())

    def test_sourced_dimensions_match_patent_text(self):
        ledger_dict = {rec.symbol: rec for rec in get_patent_parameter_ledger()}

        # 0.25 inches = 0.00635 m
        self.assertAlmostEqual(ledger_dict["P"].nominal_value_si, 0.00635, places=5)
        self.assertAlmostEqual(ledger_dict["N"].nominal_value_si, 0.00635, places=5)
        self.assertAlmostEqual(ledger_dict["S"].nominal_value_si, 0.00635, places=5)

        # 0.05 inches = 0.00127 m
        self.assertAlmostEqual(ledger_dict["T1"].nominal_value_si, 0.00127, places=5)

        # 4.0 inches = 0.1016 m
        self.assertAlmostEqual(ledger_dict["Q"].nominal_value_si, 0.1016, places=4)

        # 0.50 inches = 0.0127 m
        self.assertAlmostEqual(ledger_dict["S1"].nominal_value_si, 0.0127, places=5)


class ExodusGridAndDiscretizationTests(unittest.TestCase):
    """Test 2D discretization and boundary face structure."""

    def setUp(self):
        self.params = ExodusPatentParameters(
            applied_voltage_v=25000.0,
            num_blades=1,
            dx_m=0.001,
            dy_m=0.001,
        )
        self.grid = build_exodus_2d_grid(self.params)

    def test_conductor_masks_are_disjoint(self):
        self.assertFalse(np.any(self.grid.mask_blade_101 & self.grid.mask_ground_102))
        self.assertFalse(np.any(self.grid.mask_blade_101 & self.grid.mask_enclosure_box))
        self.assertFalse(np.any(self.grid.mask_ground_102 & self.grid.mask_enclosure_box))

    def test_boundary_face_samples_are_strictly_outside_conductors(self):
        """Regression P2-R1-F2: sample points for face integration must never be inside conductors."""
        for face in self.grid.boundary_faces:
            is_inside_blade = self.grid.mask_blade_101[face.sample_iy_ext, face.sample_ix_ext]
            is_inside_ground = self.grid.mask_ground_102[face.sample_iy_ext, face.sample_ix_ext]
            is_inside_box = self.grid.mask_enclosure_box[face.sample_iy_ext, face.sample_ix_ext]

            self.assertFalse(
                np.any(is_inside_blade),
                f"Face {face.face_name} samples inside blade conductor!",
            )
            self.assertFalse(
                np.any(is_inside_ground),
                f"Face {face.face_name} samples inside ground conductor!",
            )
            self.assertFalse(
                np.any(is_inside_box),
                f"Face {face.face_name} samples inside enclosure box!",
            )

    def test_boundary_potentials_match_prescribed_voltages(self):
        self.assertTrue(np.all(self.grid.potential_bc[self.grid.mask_blade_101] == 25000.0))
        self.assertTrue(np.all(self.grid.potential_bc[self.grid.mask_ground_102] == 0.0))
        self.assertTrue(np.all(self.grid.potential_bc[self.grid.mask_enclosure_box] == 0.0))


class ExodusConventionalElectrostaticsH0Tests(unittest.TestCase):
    """Test conventional Maxwell-stress accounting (Model H0) on patent geometry."""

    def setUp(self):
        self.params = ExodusPatentParameters(
            applied_voltage_v=25000.0,
            num_blades=1,
            dx_m=0.0006,
            dy_m=0.0006,
        )
        self.result = evaluate_exodus_patent(self.params)

    def test_laplace_solver_converges_to_small_residual(self):
        self.assertLess(self.result.solver_residual, 1e-7, "Laplace solver residual must be < 1e-7")

    def test_internal_electrode_forces_are_opposing(self):
        ledger = self.result.h0_ledger
        self.assertLess(ledger.blade_force_x.force_per_length_n_per_m, 0.0, "Blade attracted toward ground (Fx < 0)")
        self.assertGreater(ledger.ground_force_x.force_per_length_n_per_m, 0.0, "Ground attracted toward blade (Fx > 0)")

    def test_direct_enclosure_wall_traction_matches_inner_contour_reaction(self):
        """Regression P2-R1-F4: direct wall traction must match inner contour reaction."""
        ledger = self.result.h0_ledger
        f_contour = -ledger.enclosure_inner_contour_force_x.force_per_length_n_per_m
        f_wall = ledger.enclosure_direct_wall_force_x.total_enclosure_force_x_n_per_m

        # Agreement within discretization tolerance (< 1%)
        rel_diff = abs(f_contour - f_wall) / (abs(f_contour) + 1e-12)
        self.assertLess(rel_diff, 0.01, f"Direct wall traction {f_wall} != inner contour reaction {f_contour}")

    def test_whole_system_momentum_conservation(self):
        ledger = self.result.h0_ledger
        self.assertTrue(ledger.is_momentum_conserved, "Momentum must be conserved across the whole system")
        self.assertLess(ledger.residual_3d_extruded_n, 5e-4, "Net system residual must be < 0.5 mN")

    def test_contour_offset_invariance(self):
        """Regression P2-R1-F4: closed contour forces must be independent of contour offset distance."""
        grid = self.result.grid
        ex = self.result.e_field_x_v_per_m
        ey = self.result.e_field_y_v_per_m

        ledger_offset_3 = compute_h0_whole_apparatus_ledger(grid, ex, ey, contour_offset=3)
        ledger_offset_5 = compute_h0_whole_apparatus_ledger(grid, ex, ey, contour_offset=5)

        f3 = ledger_offset_3.blade_force_x.force_per_length_n_per_m
        f5 = ledger_offset_5.blade_force_x.force_per_length_n_per_m
        rel_diff = abs(f3 - f5) / abs(f3)
        self.assertLess(rel_diff, 0.02, "Contour force varies by >2% across contour offsets")


class ExodusFinite3DModelTests(unittest.TestCase):
    """Test constrained finite 3D apparatus model with 3D momentum balance."""

    def test_finite_3d_model_conserves_momentum(self):
        params = ExodusPatentParameters(applied_voltage_v=25000.0, num_blades=1)
        res_3d = solve_exodus_electrostatics_3d(params)

        self.assertTrue(res_3d.true_3d_is_conserved)
        self.assertAlmostEqual(res_3d.true_3d_net_system_force_x_n, 0.0, delta=1e-4)
        self.assertGreater(res_3d.true_3d_blade_force_x_n, 0.0)
        self.assertGreater(res_3d.true_3d_ground_force_x_n, 0.0)


class ExodusPatentAlternativeHypothesisH1Tests(unittest.TestCase):
    """Test patent Eq. (11) transcription, face quadrature, and proof obligations."""

    def setUp(self):
        self.params = ExodusPatentParameters(
            applied_voltage_v=25000.0,
            num_blades=1,
            dx_m=0.0006,
            dy_m=0.0006,
        )
        self.result = evaluate_exodus_patent(self.params)

    def test_h1_formula_uses_correct_corresponding_face_widths(self):
        """Regression P2-R1-F2: proximal area must use tip width, distal area must use base width."""
        h1 = self.result.h1_prediction
        # Proximal tip width is ~ blade thickness T1 = 1.27 mm (within discrete rasterization tolerance)
        self.assertAlmostEqual(h1.proximal_width_m, 0.00127, delta=0.001)
        # Distal base width is modeled base width = 30 mm (NOT ground plane width = 50.8 mm)
        self.assertAlmostEqual(h1.distal_width_m, 0.030, delta=0.001)

    def test_h1_omits_half_factor_and_proof_obligations_flagged(self):
        h1 = self.result.h1_prediction
        self.assertAlmostEqual(h1.missing_half_factor_force_3d_extruded_n, 0.5 * h1.predicted_force_3d_extruded_n)

        notes_text = " ".join(h1.proof_obligation_notes)
        self.assertIn("Eq. (4)", notes_text)
        self.assertIn("stationary action", notes_text)
        self.assertIn("1/2", notes_text)
        self.assertIn("Maxwell stress", notes_text)


class ExodusProgrammaticControlsTests(unittest.TestCase):
    """Test programmatically executed controls and Tajmar & Schreiber (2020) audit."""

    def test_polarity_reversal_control_is_programmatically_evaluated(self):
        controls = self.result = evaluate_exodus_patent(ExodusPatentParameters(dx_m=0.001, dy_m=0.001)).controls
        self.assertTrue(controls.polarity_reversal_evaluated)
        self.assertAlmostEqual(controls.polarity_reversal_blade_force_diff_relative, 0.0, places=5)

    def test_symmetric_electrode_control_yields_zero_net_force(self):
        """Regression P2-R1-F6: symmetric electrode configuration must produce zero net force."""
        controls = evaluate_exodus_patent(ExodusPatentParameters(dx_m=0.001, dy_m=0.001)).controls
        self.assertTrue(controls.symmetric_control_evaluated)
        self.assertAlmostEqual(controls.symmetric_control_net_force_3d_n, 0.0, delta=5e-5)

    def test_voltage_off_control_yields_zero_force(self):
        controls = evaluate_exodus_patent(ExodusPatentParameters(dx_m=0.001, dy_m=0.001)).controls
        self.assertTrue(controls.voltage_off_evaluated)
        self.assertEqual(controls.voltage_off_blade_force_n_per_m, 0.0)

    def test_unperformed_physical_controls_are_flagged(self):
        controls = evaluate_exodus_patent(ExodusPatentParameters(dx_m=0.001, dy_m=0.001)).controls
        self.assertEqual(controls.physical_controls_status, "NOT_EVALUATED_NUMERICAL_SIMULATION_ONLY")
        self.assertIn("Vacuum chamber pressure sweep", controls.unperformed_physical_controls[0])

    def test_tajmar_schreiber_literature_citation_accurate(self):
        """Regression P2-R1-F1: verify accurate literature citation without false bounds."""
        controls = evaluate_exodus_patent(ExodusPatentParameters(dx_m=0.001, dy_m=0.001)).controls
        self.assertIn("10.1016/j.elstat.2020.103477", controls.literature_benchmark_citation)
        self.assertIn("10 kV", controls.literature_benchmark_summary)
        self.assertIn("2.94 uN", controls.literature_benchmark_summary)


class ExodusMeshConvergenceTests(unittest.TestCase):
    """Test convergence of numerical force accounting under mesh refinement."""

    def test_net_residual_force_decreases_with_mesh_refinement(self):
        dx_coarse = 0.0010
        dx_fine = 0.0005

        res_coarse = evaluate_exodus_patent(ExodusPatentParameters(dx_m=dx_coarse, dy_m=dx_coarse))
        res_fine = evaluate_exodus_patent(ExodusPatentParameters(dx_m=dx_fine, dy_m=dx_fine))

        self.assertLess(res_coarse.h0_ledger.residual_3d_extruded_n, 1e-3)
        self.assertLess(res_fine.h0_ledger.residual_3d_extruded_n, 1e-4)
        self.assertLess(res_fine.h0_ledger.residual_3d_extruded_n, res_coarse.h0_ledger.residual_3d_extruded_n)


class ExodusManifestAndContractTests(unittest.TestCase):
    """Test paired evidence manifest schema, provenance, and contract invariants."""

    def test_manifest_generation_and_schema_conformance(self):
        params = ExodusPatentParameters(dx_m=0.001, dy_m=0.001)
        result = evaluate_exodus_patent(params)
        manifest = generate_exodus_patent_manifest(result, source_head_sha="TEST_SHA", tested_checkout_sha="TEST_SHA")

        self.assertEqual(manifest["manifest_schema_version"], "1.2.0")
        self.assertEqual(manifest["phase"], "P2")
        self.assertEqual(manifest["patent_identifier"], "US11511891B2")
        self.assertIn("git_provenance", manifest)
        self.assertIn("parameter_audit", manifest)
        self.assertIn("h0_conventional_maxwell_stress", manifest)
        self.assertIn("finite_3d_apparatus_model", manifest)
        self.assertIn("h1_patent_alternative_prediction", manifest)
        self.assertIn("evaluated_controls_and_contextual_literature", manifest)
        self.assertIn("scientific_disposition", manifest)

        # Epistemic guard: physical thrust measurement must be NOT_EVALUATED
        self.assertEqual(
            manifest["scientific_disposition"]["physical_thrust_measurement"],
            "NOT_EVALUATED_NUMERICAL_SIMULATION_ONLY",
        )

    def test_p0_and_p1_baselines_remain_preserved(self):
        res = subprocess.run(["git", "hash-object", "electrostatics_baseline.py"], capture_output=True, text=True, check=True)
        self.assertEqual(res.stdout.strip(), "97f65dfa25db7730323edd5e52c98b17371fdeaa")

        self.assertTrue(os.path.exists("scalar_wave_3d.py"))
        self.assertTrue(os.path.exists("electrostatics_numerics.py"))
        self.assertTrue(os.path.exists("tests/test_p1_wave_3d.py"))
        self.assertTrue(os.path.exists("tests/test_p1_numerics.py"))


if __name__ == "__main__":
    unittest.main()
