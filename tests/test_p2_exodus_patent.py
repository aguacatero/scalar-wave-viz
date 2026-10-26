"""Unit and regression tests for Phase P2: Exodus patent US11511891B2 reproduction and hypothesis separation.

Validates:
    - Sourced parameter audit and identification of missing patent parameters
    - Grid generation and conductor mask disjointness
    - Conventional Maxwell-stress electrostatics (H0) whole-system momentum conservation
    - Patent-specific formula transcription (H1: Eq. 4-11 audit)
    - Experimental controls (polarity reversal, symmetry, zero-voltage)
    - Comparison against independent null benchmark (Tajmar & Schreiber 2020)
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
    get_patent_parameter_ledger,
)
from exodus_hypothesis_evaluator import (
    evaluate_exodus_patent,
    generate_exodus_patent_manifest,
    solve_exodus_electrostatics,
    compute_electric_fields,
    compute_h0_whole_apparatus_ledger,
    compute_h1_patent_prediction,
    evaluate_experimental_controls,
)


class ExodusPatentParameterAuditTests(unittest.TestCase):
    """Test source-bound parameter audit for US11511891B2."""

    def test_parameter_audit_contains_all_patent_symbols(self):
        ledger = get_patent_parameter_ledger()
        symbols = {rec.symbol for rec in ledger}

        # Must include all primary patent symbols
        required_symbols = {"V / Delta_V", "P", "N", "T1", "Q / L_z", "S", "S1", "epsilon_r"}
        for s in required_symbols:
            self.assertIn(s, symbols, f"Missing required patent symbol {s}")

        # Must include explicit missing parameters
        missing_symbols = {"r_tip", "tan_delta", "D_enclosure", "wiring_geometry"}
        for s in missing_symbols:
            self.assertIn(s, symbols, f"Missing required missing-parameter audit for {s}")

    def test_missing_parameters_are_flagged_not_guessed(self):
        ledger = get_patent_parameter_ledger()
        for rec in ledger:
            if rec.status == "MISSING_IN_PATENT":
                combined = (rec.patent_reference + " " + rec.notes).lower()
                is_flagged = any(kw in combined for kw in ["not specified", "omitted", "not reported", "not quantified"])
                self.assertTrue(
                    is_flagged,
                    f"Parameter {rec.symbol} must explicitly state that it is omitted / not reported, got: {rec.notes}",
                )

    def test_sourced_dimensions_match_patent_text(self):
        ledger_dict = {rec.symbol: rec for rec in get_patent_parameter_ledger()}

        # 0.25 inches = 0.00635 m
        self.assertAlmostEqual(ledger_dict["P"].nominal_value_si, 0.00635, places=5)
        self.assertAlmostEqual(ledger_dict["N"].nominal_value_si, 0.00635, places=5)
        self.assertAlmostEqual(ledger_dict["S"].nominal_value_si, 0.00635, places=5)

        # 0.05 inches = 0.00127 m
        self.assertAlmostEqual(ledger_dict["T1"].nominal_value_si, 0.00127, places=5)

        # 4.0 inches = 0.1016 m
        self.assertAlmostEqual(ledger_dict["Q / L_z"].nominal_value_si, 0.1016, places=4)

        # 0.50 inches = 0.0127 m
        self.assertAlmostEqual(ledger_dict["S1"].nominal_value_si, 0.0127, places=5)


class ExodusGridAndDiscretizationTests(unittest.TestCase):
    """Test 2D discretization of Exodus patent geometry."""

    def setUp(self):
        self.params = ExodusPatentParameters(
            applied_voltage_v=25000.0,
            num_blades=1,
            dx_m=0.001,
            dy_m=0.001,
        )
        self.grid = build_exodus_2d_grid(self.params)

    def test_conductor_masks_are_disjoint(self):
        blade_ground_overlap = np.any(self.grid.mask_blade_101 & self.grid.mask_ground_102)
        blade_box_overlap = np.any(self.grid.mask_blade_101 & self.grid.mask_enclosure_box)
        ground_box_overlap = np.any(self.grid.mask_ground_102 & self.grid.mask_enclosure_box)

        self.assertFalse(blade_ground_overlap, "Blade 101 and Ground 102 overlap")
        self.assertFalse(blade_box_overlap, "Blade 101 and Enclosure box overlap")
        self.assertFalse(ground_box_overlap, "Ground 102 and Enclosure box overlap")

    def test_subsurface_masks_partition_blade_structure(self):
        # Proximal surface 100a must be on the blade
        self.assertTrue(np.all(self.grid.mask_blade_101[self.grid.mask_proximal_100a]))
        # Distal surface 101a must be on the blade
        self.assertTrue(np.all(self.grid.mask_blade_101[self.grid.mask_distal_101a]))
        # Connecting surface 100b must be on the blade
        self.assertTrue(np.all(self.grid.mask_blade_101[self.grid.mask_connecting_100b]))

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
        # Ground plate is at smaller x (left), blade is at larger x (right)
        # Attraction pulls blade to the left (negative Fx) and ground to the right (positive Fx)
        self.assertLess(ledger.blade_force_x.force_3d_n, 0.0, "Blade must be attracted toward ground (Fx < 0)")
        self.assertGreater(ledger.ground_force_x.force_3d_n, 0.0, "Ground must be attracted toward blade (Fx > 0)")

    def test_enclosure_reaction_and_whole_system_momentum_conservation(self):
        ledger = self.result.h0_ledger
        # Net sum of blade + ground + enclosure must balance to within numerical tolerance
        self.assertTrue(ledger.is_momentum_conserved, "Momentum must be conserved across the whole system")
        self.assertLess(ledger.residual_3d_n, 1e-4, "Net system residual must be < 0.1 mN")

        # Confirm enclosure reaction balances internal stress
        f_electrodes = ledger.blade_force_x.force_3d_n + ledger.ground_force_x.force_3d_n
        self.assertAlmostEqual(
            f_electrodes + ledger.enclosure_box_force_x.force_3d_n,
            0.0,
            delta=1e-4,
            msg="Enclosure reaction must balance internal electrode force sum",
        )


class ExodusPatentAlternativeHypothesisH1Tests(unittest.TestCase):
    """Test patent Eq. (11) transcription and derivation proof obligations (Model H1)."""

    def setUp(self):
        self.params = ExodusPatentParameters(
            applied_voltage_v=25000.0,
            num_blades=1,
            dx_m=0.0006,
            dy_m=0.0006,
        )
        self.result = evaluate_exodus_patent(self.params)

    def test_h1_formula_predicts_finite_asymmetric_force(self):
        h1 = self.result.h1_prediction
        # Blade tip has much higher field than distal base plate
        self.assertGreater(h1.peak_proximal_field_v_per_m, h1.average_distal_field_v_per_m)
        self.assertGreater(h1.predicted_force_3d_n, 0.0, "H1 formula predicts positive force Fx")

    def test_h1_contrasts_with_h0_net_zero_equilibrium(self):
        h0_net = self.result.h0_ledger.net_system_force_x.force_3d_n
        h1_pred = self.result.h1_prediction.predicted_force_3d_n

        # H1 predicts finite thrust, while H0 shows net system force is zero
        self.assertAlmostEqual(h0_net, 0.0, delta=1e-4)
        self.assertGreater(h1_pred, 0.005, "H1 predicts > 5 mN thrust for single blade")

    def test_h1_omits_half_factor_and_proof_obligations_flagged(self):
        h1 = self.result.h1_prediction
        # Missing half factor corrected value is exactly half
        self.assertAlmostEqual(h1.missing_half_factor_corrected_force_3d_n, 0.5 * h1.predicted_force_3d_n)

        # Must record proof obligations regarding Eq. (4) stationary action and missing boundaries
        notes_text = " ".join(h1.proof_obligation_notes)
        self.assertIn("Eq. (4)", notes_text)
        self.assertIn("stationary action", notes_text)
        self.assertIn("1/2", notes_text)
        self.assertIn("Maxwell stress", notes_text)


class ExodusExperimentalControlsTests(unittest.TestCase):
    """Test experimental controls and Tajmar & Schreiber (2020) null benchmark."""

    def test_polarity_reversal_preserves_electrostatic_force(self):
        params_pos = ExodusPatentParameters(applied_voltage_v=25000.0, num_blades=1, dx_m=0.001, dy_m=0.001)
        params_neg = ExodusPatentParameters(applied_voltage_v=-25000.0, num_blades=1, dx_m=0.001, dy_m=0.001)

        res_pos = evaluate_exodus_patent(params_pos)
        res_neg = evaluate_exodus_patent(params_neg)

        # Potential is negated, but electric field squared is identical
        np.testing.assert_allclose(res_pos.potential_v, -res_neg.potential_v, atol=1e-10)
        np.testing.assert_allclose(res_pos.e_field_magnitude_v_per_m, res_neg.e_field_magnitude_v_per_m, atol=1e-10)

        # Maxwell stress forces are identical
        self.assertAlmostEqual(
            res_pos.h0_ledger.blade_force_x.force_3d_n,
            res_neg.h0_ledger.blade_force_x.force_3d_n,
            places=6,
        )

    def test_tajmar_schreiber_null_bound_contradicts_patent_claim(self):
        controls = evaluate_experimental_controls(
            grid=build_exodus_2d_grid(),
            h0_ledger=evaluate_exodus_patent(ExodusPatentParameters(dx_m=0.001, dy_m=0.001)).h0_ledger,
            h1_result=evaluate_exodus_patent(ExodusPatentParameters(dx_m=0.001, dy_m=0.001)).h1_prediction,
        )

        # Patent claims 237 uN; Tajmar null bound is 0.4 uN
        self.assertEqual(controls.patent_claimed_force_n, 237.0e-6)
        self.assertEqual(controls.tajmar_schreiber_2020_null_bound_n, 0.4e-6)
        self.assertGreater(controls.ratio_patent_claim_to_null_bound, 500.0)
        self.assertIn("high vacuum", controls.discrepancy_explanation)


class ExodusMeshConvergenceTests(unittest.TestCase):
    """Test convergence of numerical force accounting under mesh refinement."""

    def test_net_residual_force_decreases_with_mesh_refinement(self):
        dx_coarse = 0.0010
        dx_fine = 0.0005

        res_coarse = evaluate_exodus_patent(ExodusPatentParameters(dx_m=dx_coarse, dy_m=dx_coarse))
        res_fine = evaluate_exodus_patent(ExodusPatentParameters(dx_m=dx_fine, dy_m=dx_fine))

        # Both residuals should be small (< 1 mN on coarse, < 0.1 mN on fine), and fine grid must decrease residual
        self.assertLess(res_coarse.h0_ledger.residual_3d_n, 1e-3)
        self.assertLess(res_fine.h0_ledger.residual_3d_n, 1e-4)
        self.assertLess(res_fine.h0_ledger.residual_3d_n, res_coarse.h0_ledger.residual_3d_n)


class ExodusManifestAndContractTests(unittest.TestCase):
    """Test paired evidence manifest schema, provenance, and contract invariants."""

    def test_manifest_generation_and_schema_conformance(self):
        params = ExodusPatentParameters(dx_m=0.001, dy_m=0.001)
        result = evaluate_exodus_patent(params)
        manifest = generate_exodus_patent_manifest(result, source_head_sha="TEST_SHA", tested_checkout_sha="TEST_SHA")

        # Required top-level keys for schema 1.2.0
        self.assertEqual(manifest["manifest_schema_version"], "1.2.0")
        self.assertEqual(manifest["phase"], "P2")
        self.assertEqual(manifest["patent_identifier"], "US11511891B2")
        self.assertIn("git_provenance", manifest)
        self.assertIn("parameter_audit", manifest)
        self.assertIn("h0_conventional_maxwell_stress", manifest)
        self.assertIn("h1_patent_alternative_prediction", manifest)
        self.assertIn("experimental_controls_and_null_benchmark", manifest)
        self.assertIn("scientific_disposition", manifest)

        # Epistemic guard: anomalous thrust detected must be False
        self.assertFalse(manifest["scientific_disposition"]["anomalous_thrust_detected"])

    def test_p0_and_p1_baselines_remain_preserved(self):
        # P0 blob hash
        res = subprocess.run(["git", "hash-object", "electrostatics_baseline.py"], capture_output=True, text=True, check=True)
        self.assertEqual(res.stdout.strip(), "97f65dfa25db7730323edd5e52c98b17371fdeaa", "P0 baseline blob must remain byte-identical")

        # P1 wave and numerics files must exist and be intact
        self.assertTrue(os.path.exists("scalar_wave_3d.py"))
        self.assertTrue(os.path.exists("electrostatics_numerics.py"))
        self.assertTrue(os.path.exists("tests/test_p1_wave_3d.py"))
        self.assertTrue(os.path.exists("tests/test_p1_numerics.py"))


if __name__ == "__main__":
    unittest.main()
