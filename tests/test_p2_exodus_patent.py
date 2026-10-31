"""Unit and adversarial regression tests for Phase P2: Exodus patent US11511891B2 reproduction and hypothesis separation.

Validates:
    - Sourced parameter audit covering all 12 patent geometry symbols, 5-category status taxonomy,
      and dynamic synchronization of consumed_value_si with active parameters (P2-R1-F3)
    - Explicit separation of FIGS. 4–8 single-blade schematic vs FIG. 21 9-blade epoxy test article (P2-R1-F3)
    - 1-cell-thick exterior surface masks (100a, 101a, 100b), fencepost-free widths, and material-side sampling (P2-R1-F2)
    - Analytic parallel-plate capacitor Maxwell-stress benchmark (P2-R1-F4)
    - Conventional Maxwell-stress electrostatics (H0) non-tautological whole-system momentum conservation,
      non-overlapping contour-offset sweep, enclosure clearance sweep, and dielectric Korteweg-Helmholtz closure (P2-R1-F4)
    - Constrained finite 3D apparatus model with SPD CG solver convergence, opposing blade/ground forces,
      independent 3D enclosure wall reaction, computed fringing ratio, and 3D mesh refinement convergence (P2-R1-F5)
    - Patent Eq. (11) (H1) analytical uniform-field and nonuniform-field regressions proving face quadrature
      vs spatial-mean plug-in (P2-R1-F2)
    - Programmatically evaluated controls (+V vs -V, V=0, symmetric capacitor, 180-deg spatial inversion BVP,
      asymmetric wall proximity coupling) and adversarial false-positive rejection gates (P2-R1-F6, P2-R1-M1)
    - Sourced literature benchmark audit (Tajmar & Schreiber 2020 Faraday-cage precision balance vs Patent FIG. 21
      air pendulum stand, candidate confounders) (P2-R1-F1)
    - Paired evidence manifest schema 1.2.0 and byte-for-byte preservation of P0/P1 baselines
"""

from __future__ import annotations

from dataclasses import replace
import math
import os
import subprocess
import sys
import unittest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exodus_patent_geometry import (
    EPSILON_0,
    INCHES_TO_METERS,
    ExodusPatentParameters,
    build_exodus_2d_grid,
    build_inverted_180_grid,
    build_symmetric_control_grid,
    get_patent_parameter_ledger,
)
from exodus_hypothesis_evaluator import (
    benchmark_analytic_parallel_plate_maxwell_stress,
    benchmark_analytic_planar_dielectric_slab_force,
    compute_direct_enclosure_wall_tractions,
    compute_direct_enclosure_wall_tractions_3d,
    compute_electric_fields,
    compute_h0_whole_apparatus_ledger,
    compute_h1_patent_prediction,
    evaluate_exodus_patent,
    evaluate_experimental_controls,
    generate_exodus_patent_manifest,
    run_3d_enclosure_clearance_sweep,
    run_3d_end_clearance_sweep,
    run_3d_mesh_convergence_study,
    run_contour_offset_sweep,
    run_enclosure_clearance_sweep,
    run_mesh_convergence_study,
    solve_exodus_electrostatics,
    solve_exodus_electrostatics_3d,
    verify_control_assertions,
)


class ExodusPatentParameterAuditTests(unittest.TestCase):
    """Test source-bound parameter audit and embodiment separation for US11511891B2 (P2-R1-F3)."""

    def test_parameter_audit_contains_all_12_patent_symbols(self):
        ledger = get_patent_parameter_ledger()
        symbols = {rec.symbol for rec in ledger}

        patent_symbols = ["T", "T1", "T2", "M", "N", "O", "P", "Q", "S", "S1", "U", "V"]
        for s in patent_symbols:
            self.assertIn(s, symbols, f"Missing required patent symbol {s}")

        extra_symbols = ["epsilon_r", "r_tip", "tan_delta", "D_enclosure", "wiring_geometry"]
        for s in extra_symbols:
            self.assertIn(s, symbols, f"Missing required audit parameter {s}")

    def test_parameter_status_five_category_taxonomy(self):
        """Regression P2-R1-F3: distinguish explicit, derived, external estimate, assumption, and omitted."""
        ledger_dict = {rec.symbol: rec for rec in get_patent_parameter_ledger()}

        for sym in ["V", "P", "N", "T1", "Q", "S"]:
            self.assertEqual(
                ledger_dict[sym].status,
                "PATENT_EXPLICIT_VALUE",
                f"Symbol {sym} must be marked PATENT_EXPLICIT_VALUE",
            )

        for sym in ["S1", "T", "M"]:
            self.assertEqual(
                ledger_dict[sym].status,
                "DERIVED_FROM_PATENT",
                f"Symbol {sym} must be marked DERIVED_FROM_PATENT",
            )

        for sym in ["epsilon_r", "T2"]:
            self.assertEqual(
                ledger_dict[sym].status,
                "EXTERNAL_ESTIMATE_FOR_UNSPECIFIED",
                f"Symbol {sym} must be marked EXTERNAL_ESTIMATE_FOR_UNSPECIFIED",
            )

        for sym in ["O", "U"]:
            self.assertEqual(
                ledger_dict[sym].status,
                "MODELING_ASSUMPTION",
                f"Symbol {sym} must be marked MODELING_ASSUMPTION",
            )

        for sym in ["r_tip", "tan_delta", "D_enclosure", "wiring_geometry"]:
            self.assertEqual(
                ledger_dict[sym].status,
                "PATENT_OMITTED_UNKNOWN",
                f"Symbol {sym} must be marked PATENT_OMITTED_UNKNOWN",
            )
            self.assertIn("omitted", (ledger_dict[sym].patent_reference + " " + ledger_dict[sym].notes).lower())

    def test_consumed_value_si_synchronizes_with_custom_parameters(self):
        """Regression P2-R1-F3: consumed_value_si must reflect actual solver parameters."""
        custom_params = ExodusPatentParameters(
            applied_voltage_v=18500.0,
            gap_spacing_m=0.008,
            blade_height_m=0.009,
            base_plate_thickness_m=0.003,
            ground_plane_thickness_m=0.0025,
            enclosure_margin_x_m=0.032,
            dielectric_relative_permittivity=4.2,
        )
        ledger_dict = {rec.symbol: rec for rec in get_patent_parameter_ledger(custom_params)}

        self.assertAlmostEqual(ledger_dict["V"].consumed_value_si, 18500.0)
        self.assertAlmostEqual(ledger_dict["S"].consumed_value_si, 0.008)
        self.assertAlmostEqual(ledger_dict["P"].consumed_value_si, 0.009)
        self.assertAlmostEqual(ledger_dict["S1"].consumed_value_si, 0.017)
        self.assertAlmostEqual(ledger_dict["T"].consumed_value_si, 0.020)
        self.assertAlmostEqual(ledger_dict["T2"].consumed_value_si, 0.0025)
        self.assertAlmostEqual(ledger_dict["U"].consumed_value_si, 0.032)
        self.assertAlmostEqual(ledger_dict["epsilon_r"].consumed_value_si, 4.2)

    def test_embodiment_separation_figs_4_to_8_vs_fig_21(self):
        """Regression P2-R1-F3: separate FIGS. 4-8 single-stage vacuum schematic from FIG. 21 9-blade epoxy article."""
        p_schem = ExodusPatentParameters.figs_4_to_8_schematic()
        p_fig21 = ExodusPatentParameters.fig_21_nine_blade_article()

        self.assertEqual(p_schem.embodiment_id, "FIGS_4_TO_8_SINGLE_STAGE_SCHEMATIC")
        self.assertEqual(p_schem.num_blades, 1)
        self.assertAlmostEqual(p_schem.dielectric_relative_permittivity, 1.0)

        self.assertEqual(p_fig21.embodiment_id, "FIG_21_NINE_BLADE_EPOXY_TEST_ARTICLE")
        self.assertEqual(p_fig21.num_blades, 9)
        self.assertAlmostEqual(p_fig21.dielectric_relative_permittivity, 3.8)
        self.assertGreater(p_fig21.base_plate_width_m, p_schem.base_plate_width_m)

    def test_sourced_dimensions_match_patent_text(self):
        ledger_dict = {rec.symbol: rec for rec in get_patent_parameter_ledger()}
        self.assertAlmostEqual(ledger_dict["P"].nominal_value_si, 0.00635, places=5)
        self.assertAlmostEqual(ledger_dict["N"].nominal_value_si, 0.00635, places=5)
        self.assertAlmostEqual(ledger_dict["S"].nominal_value_si, 0.00635, places=5)
        self.assertAlmostEqual(ledger_dict["T1"].nominal_value_si, 0.00127, places=5)
        self.assertAlmostEqual(ledger_dict["Q"].nominal_value_si, 0.1016, places=4)
        self.assertAlmostEqual(ledger_dict["S1"].nominal_value_si, 0.0127, places=5)


class ExodusGridAndSurfaceMaskTests(unittest.TestCase):
    """Test 2D discretization, exterior 1-cell surface masks, and fencepost-free widths (P2-R1-F2, P2-R1-F3)."""

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

    def test_surface_masks_are_strictly_one_cell_thick_exterior_boundaries(self):
        """Regression P2-R1-F2: surface masks 100a, 101a, 100b must be 1-cell exterior boundary layers."""
        # Proximal tip 100a must occupy exactly 1 x-column
        ix_100a = np.unique(np.where(self.grid.mask_proximal_100a)[1])
        self.assertEqual(len(ix_100a), 1, "mask_proximal_100a must be strictly 1 cell thick in X")

        # Distal rear 101a must occupy exactly 1 x-column (the right-most column of the base plate)
        ix_101a = np.unique(np.where(self.grid.mask_distal_101a)[1])
        self.assertEqual(len(ix_101a), 1, "mask_distal_101a must be strictly 1 cell thick in X")

        # Every cell in 100a, 101a, 100b must be adjacent to at least one non-blade exterior cell
        blade = self.grid.mask_blade_101
        has_exterior_neighbor = np.zeros_like(blade)
        has_exterior_neighbor[1:-1, 1:-1] = (
            (~blade[1:-1, 2:])
            | (~blade[1:-1, :-2])
            | (~blade[2:, 1:-1])
            | (~blade[:-2, 1:-1])
        )
        for name, s_mask in [
            ("100a", self.grid.mask_proximal_100a),
            ("101a", self.grid.mask_distal_101a),
            ("100b", self.grid.mask_connecting_100b),
        ]:
            self.assertTrue(np.any(s_mask), f"Surface mask {name} must be non-empty")
            self.assertTrue(
                np.all(has_exterior_neighbor[s_mask]),
                f"Surface mask {name} contains interior solid cells not on the conductor boundary!",
            )

    def test_ground_plane_thickness_parameter_affects_ground_mask(self):
        """Regression P2-R1-F3: ground_plane_thickness_m must control ground electrode mask thickness."""
        g_thin = build_exodus_2d_grid(ExodusPatentParameters(ground_plane_thickness_m=0.001, dx_m=0.001, dy_m=0.001))
        g_thick = build_exodus_2d_grid(ExodusPatentParameters(ground_plane_thickness_m=0.004, dx_m=0.001, dy_m=0.001))

        nx_thin = len(np.unique(np.where(g_thin.mask_ground_102)[1]))
        nx_thick = len(np.unique(np.where(g_thick.mask_ground_102)[1]))
        self.assertEqual(nx_thin, 1)
        self.assertEqual(nx_thick, 4)

    def test_boundary_face_samples_are_strictly_outside_conductors(self):
        """Regression P2-R1-F2: sample points for face integration must never be inside conductors."""
        for face in self.grid.boundary_faces:
            self.assertFalse(np.any(self.grid.mask_blade_101[face.sample_iy_ext, face.sample_ix_ext]))
            self.assertFalse(np.any(self.grid.mask_ground_102[face.sample_iy_ext, face.sample_ix_ext]))
            self.assertFalse(np.any(self.grid.mask_enclosure_box[face.sample_iy_ext, face.sample_ix_ext]))

    def test_boundary_face_widths_have_no_fencepost_bias(self):
        """Regression P2-R1-F2: face widths must equal n_cells * dy without +1 fencepost inflation."""
        face_100a = next(f for f in self.grid.boundary_faces if f.face_name == "proximal_tip_100a")
        face_101a = next(f for f in self.grid.boundary_faces if f.face_name == "distal_rear_101a")

        # At dy = 1.0 mm, base_plate_width_m = 30.0 mm -> exactly 30 cells -> 0.0300 m (not 0.031 m)
        self.assertAlmostEqual(face_101a.length_m, 0.030, places=6)
        self.assertEqual(len(face_101a.sample_iy_ext), 30)
        # At dy = 1.0 mm, blade_thickness_m = 1.5 mm -> round(1.5) = 2 cells -> 0.002 m
        self.assertEqual(len(face_100a.sample_iy_ext) * self.grid.dy, face_100a.length_m)


class ExodusConventionalElectrostaticsH0Tests(unittest.TestCase):
    """Test conventional Maxwell-stress accounting (Model H0) and analytic benchmarks (P2-R1-F4)."""

    def setUp(self):
        self.params = ExodusPatentParameters(
            applied_voltage_v=25000.0,
            num_blades=1,
            dx_m=0.0006,
            dy_m=0.0006,
        )
        self.result = evaluate_exodus_patent(self.params)

    def test_analytic_parallel_plate_capacitor_maxwell_stress_benchmark(self):
        """Regression P2-R1-F4: verify Maxwell stress integrator against exact 1D parallel-plate solution."""
        bench = benchmark_analytic_parallel_plate_maxwell_stress(
            voltage_v=10000.0, gap_d_m=0.006, plate_width_m=0.060, dx_m=0.0005
        )
        self.assertLess(bench["field_relative_error"], 1e-6)
        self.assertLess(bench["pressure_relative_error"], 1e-6)
        self.assertLess(bench["blade_force_n_per_m"], -0.1)
        self.assertGreater(bench["ground_force_n_per_m"], 0.1)
        self.assertAlmostEqual(
            bench["blade_force_n_per_m"] + bench["ground_force_n_per_m"], 0.0, places=10
        )
        self.assertLess(abs(bench["net_system_force_n_per_m"]), 1e-10)

    def test_analytic_dielectric_slab_benchmark_and_virtual_work(self):
        """Regression P2-R3-F3: verify dielectric force across analytical virtual work, numerical virtual work, and contour stress."""
        bench = benchmark_analytic_planar_dielectric_slab_force(
            voltage_v=1000.0, eps_r=3.8, gap_d_m=0.010, dx_m=0.0005, lz_m=0.100
        )
        self.assertEqual(
            bench.benchmark_status,
            "INDEPENDENT_DIELECTRIC_BENCHMARK_CONTOURS_AND_VIRTUAL_WORK_AGREE",
        )
        # Numerical contour stress and virtual-work perturbation agree tightly (< 5%)
        self.assertLess(bench.relative_difference_contour_to_virtual_work, 0.05)
        # Both agree with idealized 1D analytical formula (< 15% due to 2D fringing)
        self.assertLess(bench.relative_difference_contour_to_analytic, 0.15)
        self.assertLess(bench.numerical_contour_stress_force_n, 0.0)
        self.assertLess(bench.numerical_virtual_work_force_n, 0.0)
        self.assertLess(bench.analytic_virtual_work_force_n, 0.0)

    def test_laplace_solver_converges_to_small_residual(self):
        self.assertLess(self.result.solver_residual, 1e-8)

    def test_internal_electrode_forces_are_opposing(self):
        ledger = self.result.h0_ledger
        self.assertLess(ledger.blade_force_x.force_per_length_n_per_m, 0.0)
        self.assertGreater(ledger.ground_force_x.force_per_length_n_per_m, 0.0)

    def test_direct_enclosure_wall_traction_matches_inner_contour_reaction(self):
        """Regression P2-R1-F4: direct wall traction must match inner contour reaction."""
        ledger = self.result.h0_ledger
        f_contour = -ledger.enclosure_inner_contour_force_x.force_per_length_n_per_m
        f_wall = ledger.enclosure_direct_wall_force_x.total_enclosure_force_x_n_per_m

        rel_diff = abs(f_contour - f_wall) / (abs(f_contour) + 1e-12)
        self.assertLess(rel_diff, 0.01)

    def test_non_tautological_whole_system_momentum_conservation(self):
        """Regression P2-R1-F4: net_system_force_x must sum direct wall traction (non-tautological)."""
        ledger = self.result.h0_ledger
        f_sum = (
            ledger.blade_force_x.force_per_length_n_per_m
            + ledger.ground_force_x.force_per_length_n_per_m
            + ledger.dielectric_force_x.force_per_length_n_per_m
            + ledger.enclosure_direct_wall_force_x.total_enclosure_force_x_n_per_m
        )
        self.assertAlmostEqual(ledger.net_system_force_x.force_per_length_n_per_m, f_sum, places=12)
        self.assertGreater(abs(f_sum), 0.0, "Independent numerical sum must not be a hardcoded tautological 0.0")
        self.assertTrue(ledger.is_momentum_conserved)
        self.assertLess(ledger.residual_3d_extruded_n, 5e-4)
        self.assertLess(ledger.relative_residual_to_blade_force, 0.005)

    def test_non_overlapping_contour_offset_sweep_invariance(self):
        """Regression P2-R1-F4: contours must remain strictly disjoint in the gap and path-independent."""
        grid = self.result.grid
        ex = self.result.e_field_x_v_per_m
        ey = self.result.e_field_y_v_per_m

        for c in (1, 2, 3, 4, 5):
            led = compute_h0_whole_apparatus_ledger(grid, ex, ey, contour_offset=c)
            # Ground right contour index must remain strictly left of blade left contour index
            self.assertLess(led.ground_force_x.ix_max, led.blade_force_x.ix_min)

        rows = run_contour_offset_sweep(grid, ex, ey, offsets=(2, 3, 4))
        f_blades = [r["blade_force_x_n_per_m"] for r in rows]
        max_spread = (max(f_blades) - min(f_blades)) / abs(np.mean(f_blades))
        self.assertLess(max_spread, 0.015, f"Contour spread {max_spread:.4f} exceeds 1.5%")

    def test_enclosure_clearance_sensitivity_sweep(self):
        """Regression P2-R1-F4: quantify wall coupling decay with increasing enclosure clearance U."""
        rows = run_enclosure_clearance_sweep(clearances_m=(0.015, 0.025, 0.040))
        wall_mags = [abs(r["enclosure_wall_force_x_n_per_m"]) for r in rows]
        self.assertGreater(wall_mags[0], wall_mags[1])
        self.assertGreater(wall_mags[1], wall_mags[2])
        for r in rows:
            self.assertLess(abs(r["net_system_force_x_n_per_m"]), 0.005)

    def test_nonuniform_dielectric_korteweg_helmholtz_reaction_closure(self):
        """Regression P2-R1-F4: potted dielectric (eps_r > 1) must include dielectric body force for conservation."""
        p_diel = ExodusPatentParameters(
            applied_voltage_v=25000.0,
            num_blades=1,
            dielectric_relative_permittivity=3.8,
            dx_m=0.001,
            dy_m=0.001,
        )
        g_diel = build_exodus_2d_grid(p_diel)
        pot, _, _ = solve_exodus_electrostatics(g_diel)
        ex, ey, _ = compute_electric_fields(g_diel, pot)
        ledger = compute_h0_whole_apparatus_ledger(g_diel, ex, ey)

        self.assertNotEqual(ledger.dielectric_force_x.force_per_length_n_per_m, 0.0)
        self.assertTrue(ledger.is_momentum_conserved)
        self.assertLess(ledger.relative_residual_to_blade_force, 0.01)


class ExodusFinite3DModelTests(unittest.TestCase):
    """Test constrained finite 3D apparatus model and 3D mesh convergence (P2-R1-F5, P2-R2-F1..F3)."""

    def test_finite_3d_model_solver_convergence_opposing_forces_and_conservation(self):
        """Regression P2-R1-F5, P2-R2-F2, P2-R2-F3: 3D solver must converge, produce opposing forces, and direct walls."""
        params = ExodusPatentParameters(applied_voltage_v=25000.0, num_blades=1)
        res_3d = solve_exodus_electrostatics_3d(params)

        # 1. Distinguish linear algebra solver residual from discrete momentum closure residual
        self.assertLess(res_3d.solver_residual, 1e-8, "3D SPD CG solver must converge to < 1e-8")
        self.assertLess(
            res_3d.solver_residual,
            1e-7,
            "Linear algebra residual must be orders of magnitude below force residual",
        )

        # 2. Opposing physical electrode forces
        self.assertLess(res_3d.finite_3d_blade_force_x_n, -0.02, "3D blade must be attracted in -x toward ground")
        self.assertGreater(res_3d.finite_3d_ground_force_x_n, 0.02, "3D ground must be attracted in +x toward blade")

        # 3. Direct 6-wall electrostatic surface traction matches diagnostic contour
        self.assertLess(
            res_3d.finite_3d_direct_wall_to_contour_agreement_rel,
            0.01,
            "Direct 6-wall traction must agree with diagnostic inner contour flux to < 1%",
        )

        # 4. Strict scientific tolerance gate against target patent effect scale (237 uN)
        # Coarse grid (dx=2mm) net residual (~593 uN) exceeds 237 uN budget, so it must NOT pass as conserved!
        self.assertGreater(
            abs(res_3d.finite_3d_net_system_force_x_n),
            res_3d.target_effect_scale_n,
            "Coarse 3D grid net residual exceeds 237 uN patent target scale",
        )
        self.assertFalse(
            res_3d.finite_3d_is_conserved,
            "Coarse 3D grid must fail conservation gate when residual exceeds 237 uN budget (P2-R2-F2)",
        )
        self.assertEqual(
            res_3d.finite_3d_conservation_status,
            "RESIDUAL_EXCEEDS_TARGET_EFFECT_SCALE_AT_COARSE_RESOLUTION",
        )

        # 5. Fringing ratio must be genuinely computed from 3D/2D ratio
        expected_ratio = res_3d.finite_3d_blade_force_x_n / res_3d.extruded_2d_blade_force_at_matched_dx_n
        self.assertAlmostEqual(res_3d.end_fringing_ratio_3d_to_extruded_2d, expected_ratio, places=12)
        self.assertGreater(res_3d.end_fringing_ratio_3d_to_extruded_2d, 0.85)
        self.assertLess(res_3d.end_fringing_ratio_3d_to_extruded_2d, 1.05)

    def test_finite_3d_mesh_refinement_convergence(self):
        """Regression P2-R2-F1: verify 3D model relative changes, Richardson extrapolation, and geometry metrics."""
        results = run_3d_mesh_convergence_study(
            spacings=((0.0020, 0.0040), (0.0015, 0.0030), (0.0012, 0.0025))
        )
        self.assertEqual(len(results), 3)

        for r in results:
            self.assertLess(r.solver_residual, 1e-8)
            self.assertLess(r.finite_3d_blade_force_x_n, 0.0)
            self.assertGreater(r.finite_3d_ground_force_x_n, 0.0)
            # Track geometry discretization metrics
            self.assertGreater(r.discretized_tip_width_m, 0.0)
            self.assertGreater(r.discretized_gap_m, 0.0)
            self.assertGreater(r.tip_width_discretization_ratio, 0.0)
            self.assertGreater(r.gap_discretization_ratio, 0.0)

        # Step-to-step relative change delta_k drops monotonically establishing asymptotic convergence
        rel_chgs = [r.relative_change_blade_to_prev for r in results[1:]]
        self.assertLess(rel_chgs[1], rel_chgs[0], "Relative change delta_k must decrease under refinement")

        # Richardson extrapolation limit and estimated truncation uncertainty
        self.assertLess(results[-1].richardson_extrapolated_blade_3d_n, -0.05)
        self.assertGreater(results[-1].estimated_discretization_error_percent, 0.0)
        self.assertLess(results[-1].estimated_discretization_error_percent, 30.0)

    def test_3d_direct_six_wall_surface_traction_matches_inner_contour(self):
        """Regression P2-R2-F3: direct 6-wall electrostatic surface traction matches diagnostic contour."""
        params = ExodusPatentParameters.figs_4_to_8_schematic()
        res = solve_exodus_electrostatics_3d(params, dx_3d_m=0.0015, dy_3d_m=0.0015, dz_3d_m=0.0030)
        walls = res.finite_3d_direct_wall_tractions

        # Tractions exist on all faces
        self.assertNotEqual(walls.left_wall_force_x_n, 0.0)
        self.assertNotEqual(walls.right_wall_force_x_n, 0.0)
        self.assertNotEqual(walls.total_enclosure_force_x_n, 0.0)

        # Direct 6-wall sum matches inner contour outward stress flux to < 0.5% at 1.5mm
        self.assertLess(res.finite_3d_direct_wall_to_contour_agreement_rel, 0.005)

    def test_adversarial_rejection_of_unconverged_or_permissive_3d_force(self):
        """Regression P2-R2-F2: reject arbitrary permissive threshold (1500 uN); enforce 237 uN budget."""
        params = ExodusPatentParameters(applied_voltage_v=25000.0, num_blades=1)
        res_3d = solve_exodus_electrostatics_3d(params, dx_3d_m=0.002, dy_3d_m=0.002, dz_3d_m=0.004)

        # If an unprincipled 1500 uN threshold were used, it would erroneously claim conservation
        erroneous_permissive_gate = abs(res_3d.finite_3d_net_system_force_x_n) < 1.5e-3
        self.assertTrue(erroneous_permissive_gate, "Coarse grid would erroneously pass under 1500 uN")

        # But principled scientific gate against 237 uN target effect scale rejects it
        self.assertFalse(
            res_3d.finite_3d_is_conserved,
            "Must reject coarse grid momentum conservation when residual exceeds 237 uN",
        )
        self.assertEqual(
            res_3d.finite_3d_conservation_status,
            "RESIDUAL_EXCEEDS_TARGET_EFFECT_SCALE_AT_COARSE_RESOLUTION",
        )

    def test_3d_enclosure_clearance_and_end_margin_sweeps(self):
        """Regression P2-R2-F1: sweep domain clearance U and end clearance Z in 3D."""
        u_sweep = run_3d_enclosure_clearance_sweep(clearance_multipliers=(1.0, 1.5))
        self.assertEqual(len(u_sweep), 2)
        for row in u_sweep:
            self.assertIn("blade_force_x_n", row)
            self.assertIn("enclosure_wall_force_x_n", row)
            self.assertLess(row["blade_force_x_n"], 0.0)

        z_sweep = run_3d_end_clearance_sweep(margin_z_values=(0.015, 0.025))
        self.assertEqual(len(z_sweep), 2)
        for row in z_sweep:
            self.assertIn("end_fringing_ratio", row)
            self.assertGreater(row["end_fringing_ratio"], 0.8)

    def test_3d_nine_blade_epoxy_test_article_solve(self):
        """Regression P2-R2-F1: solve 3D finite-difference model for FIG. 21 9-blade potted article."""
        p21 = ExodusPatentParameters.fig_21_nine_blade_article()
        res21 = solve_exodus_electrostatics_3d(p21, dx_3d_m=0.003, dy_3d_m=0.003, dz_3d_m=0.006)

        self.assertEqual(res21.num_blades, 9)
        self.assertEqual(
            res21.dielectric_force_status,
            "INDEPENDENT_BENCHMARK_VALIDATED_2D_VIRTUAL_WORK_APPROXIMATE_3D_CONTOUR",
        )
        self.assertLess(res21.finite_3d_blade_force_x_n, -0.2, "9-blade attraction exceeds 200 mN")
        self.assertGreater(res21.finite_3d_ground_force_x_n, 0.2, "9-blade ground repulsion exceeds 200 mN")
        self.assertNotEqual(res21.finite_3d_dielectric_force_x_n, 0.0, "Dielectric reaction is non-zero")
        self.assertNotEqual(
            res21.finite_3d_enclosure_direct_wall_force_x_n,
            0.0,
            "Outer wall reaction is non-zero",
        )

    def test_3d_uncertainty_budget_and_discrimination_gate(self):
        """Regression P2-R3-F2: 5-part uncertainty budget and strict 23.7 uN physical discrimination gate."""
        res = solve_exodus_electrostatics_3d()
        self.assertAlmostEqual(res.tip_width_discretization_ratio, 1.0, places=4)
        self.assertAlmostEqual(res.gap_discretization_ratio, 1.0, places=4)

        # 5-part uncertainty budget
        self.assertLess(res.linear_algebra_solver_residual_n, 1e-8)
        self.assertGreater(res.discrete_momentum_closure_residual_n, 0.0)
        self.assertGreater(res.mesh_force_discretization_uncertainty_n, 0.0)
        self.assertGreater(res.domain_boundary_clearance_uncertainty_n, 0.0)
        self.assertTrue(len(res.missing_parameter_model_uncertainty_notes) > 20)

        # Strict discrimination threshold: 10% of 237 uN = 23.7 uN
        self.assertEqual(res.discriminating_threshold_n, 2.37e-5)
        self.assertGreater(res.discrete_momentum_closure_residual_n, res.discriminating_threshold_n)
        self.assertEqual(
            res.physical_scale_discrimination_status,
            "NOT_RESOLVED_AT_CURRENT_3D_GRID_RESOLUTION",
        )
        self.assertFalse(res.finite_3d_is_conserved)
        self.assertEqual(
            res.whole_body_3d_mechanical_accounting,
            "UNVERIFIED_PENDING_CONFORMING_INTERFACE_MESHING",
        )

    def test_fig21_nine_blade_commensurate_geometry_and_force_balance(self):
        """Regression P2-R3-F2: FIG. 21 9-blade 3D article on commensurate grid with 1.0000 geometry ratios."""
        p21 = ExodusPatentParameters.fig_21_nine_blade_article()
        res = solve_exodus_electrostatics_3d(p21, dx_3d_m=0.00127, dy_3d_m=0.00127, dz_3d_m=0.00254)

        self.assertEqual(res.num_blades, 9)
        self.assertAlmostEqual(res.tip_width_discretization_ratio, 1.0, places=4)
        self.assertAlmostEqual(res.gap_discretization_ratio, 1.0, places=4)
        self.assertLess(res.finite_3d_direct_wall_to_contour_agreement_rel, 0.005)
        self.assertEqual(
            res.physical_scale_discrimination_status,
            "NOT_RESOLVED_AT_CURRENT_3D_GRID_RESOLUTION",
        )


class ExodusPatentAlternativeHypothesisH1Tests(unittest.TestCase):
    """Test patent Eq. (11) transcription, analytical uniform/nonuniform regressions, and proof obligations (P2-R1-F2)."""

    def setUp(self):
        self.params = ExodusPatentParameters(
            applied_voltage_v=25000.0,
            num_blades=1,
            dx_m=0.0005,
            dy_m=0.0005,
        )
        self.grid = build_exodus_2d_grid(self.params)

    def test_h1_analytical_uniform_field_regression(self):
        """Regression P2-R1-F2: for a uniform field E0, quadrature and mean plug-in must match analytical eps0*E0^2*(w1 - w2)."""
        e0 = 2.0e6  # 2 MV/m uniform field
        ex = np.full((self.grid.ny, self.grid.nx), e0, dtype=float)
        ey = np.zeros_like(ex)
        e_mag = np.abs(ex)

        h1 = compute_h1_patent_prediction(self.grid, ex, ey, e_mag)
        w2 = h1.proximal_width_m
        w1 = h1.distal_width_m

        expected_per_m = -EPSILON_0 * (e0 ** 2) * (w2 - w1)
        self.assertAlmostEqual(h1.predicted_force_per_length_n_per_m, expected_per_m, places=9)
        self.assertAlmostEqual(h1.mean_field_plugin_force_per_length_n_per_m, expected_per_m, places=9)

    def test_h1_analytical_nonuniform_field_regression_proves_quadrature_vs_mean_plugin(self):
        """Regression P2-R1-F2: for a spatially varying field on 100a, quadrature > mean-field plug-in by Cauchy-Schwarz."""
        face_100a = next(f for f in self.grid.boundary_faces if f.face_name == "proximal_tip_100a")
        ex = np.zeros((self.grid.ny, self.grid.nx), dtype=float)
        ey = np.zeros_like(ex)

        # Apply nonuniform field [1, 2, 3] MV/m on the 3 sample points of 100a and 0 on 101a
        vals = np.linspace(1.0e6, 3.0e6, len(face_100a.sample_iy_ext))
        ex[face_100a.sample_iy_ext, face_100a.sample_ix_ext] = vals
        e_mag = np.abs(ex)

        h1 = compute_h1_patent_prediction(self.grid, ex, ey, e_mag)
        expected_int_e2 = float(np.sum(vals ** 2) * self.grid.dy)
        expected_mean_e2 = float((np.mean(vals) ** 2) * h1.proximal_width_m)

        self.assertAlmostEqual(h1.proximal_face_integral_e2_dl, expected_int_e2, places=5)
        self.assertGreater(expected_int_e2, expected_mean_e2)
        self.assertGreater(
            abs(h1.predicted_force_per_length_n_per_m),
            abs(h1.mean_field_plugin_force_per_length_n_per_m),
        )

    def test_h1_formula_uses_correct_corresponding_face_widths(self):
        """Regression P2-R1-F2: proximal area must use tip width, distal area must use base width."""
        result = evaluate_exodus_patent(self.params)
        h1 = result.h1_prediction
        self.assertAlmostEqual(h1.proximal_width_m, 0.0015, places=6)
        self.assertAlmostEqual(h1.distal_width_m, 0.0300, places=6)

    def test_h1_omits_half_factor_and_proof_obligations_flagged(self):
        result = evaluate_exodus_patent(self.params)
        h1 = result.h1_prediction
        self.assertAlmostEqual(h1.missing_half_factor_force_3d_extruded_n, 0.5 * h1.predicted_force_3d_extruded_n)

        notes_text = " ".join(h1.proof_obligation_notes)
        self.assertIn("Eq. (4)", notes_text)
        self.assertIn("stationary action", notes_text)
        self.assertIn("1/2", notes_text)
        self.assertIn("Cauchy-Schwarz", notes_text)
        self.assertIn("tip rounding radius", notes_text)
        self.assertIn("Maxwell stress", notes_text)

    def test_h1_near_tip_field_mesh_refinement_convergence(self):
        """Regression P2-R2-M2: near-tip field scales with mesh resolution due to omitted tip rounding radius r_tip."""
        rows = run_mesh_convergence_study()
        self.assertEqual(len(rows), 4)

        # Tip mean and max electric fields increase as mesh refines corner singularity
        tip_means = [r["tip_mean_field_v_per_m"] for r in rows]
        tip_maxs = [r["tip_max_field_v_per_m"] for r in rows]
        for i in range(len(rows) - 1):
            self.assertLess(tip_means[i], tip_means[i + 1], "Tip mean field must increase as corner is refined")
            self.assertLess(tip_maxs[i], tip_maxs[i + 1], "Tip max field must increase as corner is refined")

        # Verify that proof obligations explicitly flag omitted tip rounding radius
        result = evaluate_exodus_patent(self.params)
        notes = " ".join(result.h1_prediction.proof_obligation_notes)
        self.assertIn("tip rounding radius", notes.lower())
        self.assertIn("singularity", notes.lower())


class ExodusProgrammaticControlsAndAdversarialTests(unittest.TestCase):
    """Test programmatically executed controls, literature accuracy, and adversarial false-positive gates (P2-R1-F1, P2-R1-F6)."""

    @classmethod
    def setUpClass(cls):
        cls.params = ExodusPatentParameters(dx_m=0.001, dy_m=0.001)
        cls.result = evaluate_exodus_patent(cls.params)
        cls.controls = cls.result.controls

    def test_polarity_reversal_control_compares_pos_and_neg_solutions(self):
        """Regression P2-R1-F6: verify +V and -V solutions have opposite potentials, identical |E|, and identical forces."""
        self.assertTrue(self.controls.polarity_reversal_evaluated)
        self.assertLess(self.controls.polarity_reversal_max_field_diff_relative, 1e-9)
        self.assertLess(self.controls.polarity_reversal_blade_force_diff_relative, 1e-9)

        # Direct check that +V and -V potentials are non-identical and exact negatives
        g_neg = build_exodus_2d_grid(replace(self.params, applied_voltage_v=-self.params.applied_voltage_v))
        pot_neg, _, _ = solve_exodus_electrostatics(g_neg)
        self.assertGreater(np.max(np.abs(self.result.potential_v - pot_neg)), 40000.0)
        self.assertLess(np.max(np.abs(self.result.potential_v + pot_neg)), 1e-6)

    def test_180_degree_spatial_inversion_bvp_reverses_force_vector(self):
        """Regression P2-R1-F6: 180-deg geometry inversion must be solved as a BVP and reverse Fx sign."""
        self.assertTrue(self.controls.inversion_180_evaluated)
        self.assertTrue(self.controls.inversion_180_vector_reversed)
        self.assertLess(self.controls.inversion_180_base_blade_force_x_n_per_m, -0.1)
        self.assertGreater(self.controls.inversion_180_inverted_blade_force_x_n_per_m, 0.1)
        self.assertLess(self.controls.inversion_180_relative_reversal_error, 1e-9)

    def test_asymmetric_wall_proximity_control_quantifies_environmental_wall_coupling(self):
        """Regression P2-R1-F6: shifting apparatus near grounded wall induces pair force balanced by wall reaction."""
        self.assertTrue(self.controls.wall_proximity_control_evaluated)
        self.assertGreater(
            abs(self.controls.wall_proximity_asymmetric_pair_force_n_per_m),
            abs(self.controls.wall_proximity_symmetric_pair_force_n_per_m) * 1.5,
        )
        self.assertLess(abs(self.controls.wall_proximity_asymmetric_net_residual_n_per_m), 5e-3)
        self.assertLess(
            abs(self.controls.wall_proximity_asymmetric_net_residual_n_per_m),
            0.02 * abs(self.controls.wall_proximity_asymmetric_wall_reaction_n_per_m),
        )

    def test_symmetric_electrode_control_yields_opposing_internal_and_zero_net_force(self):
        """Regression P2-R1-F6: symmetric capacitor must have opposing plate forces and zero net force."""
        self.assertTrue(self.controls.symmetric_control_evaluated)
        self.assertLess(self.controls.symmetric_blade_force_n_per_m, -0.1)
        self.assertGreater(self.controls.symmetric_ground_force_n_per_m, 0.1)
        self.assertAlmostEqual(self.controls.symmetric_control_net_force_3d_n, 0.0, delta=5e-5)

    def test_voltage_off_control_yields_exact_zero_field_and_force(self):
        self.assertTrue(self.controls.voltage_off_evaluated)
        self.assertEqual(self.controls.voltage_off_max_field_v_per_m, 0.0)
        self.assertEqual(self.controls.voltage_off_blade_force_n_per_m, 0.0)

    def test_adversarial_false_positive_controls_are_rejected_by_gate(self):
        """Regression P2-R1-M1 & F6: verify_control_assertions must reject corrupted control results."""
        self.assertTrue(verify_control_assertions(self.controls, strict=True))

        corrupted_cases = [
            replace(self.controls, polarity_reversal_max_field_diff_relative=0.05),
            replace(self.controls, polarity_reversal_blade_force_diff_relative=0.05),
            replace(self.controls, symmetric_control_net_force_3d_n=0.01),
            replace(self.controls, symmetric_blade_force_n_per_m=0.2),  # wrong sign (repulsive instead of attractive)
            replace(self.controls, voltage_off_blade_force_n_per_m=1e-4),
            replace(self.controls, inversion_180_vector_reversed=False),
            replace(self.controls, inversion_180_inverted_blade_force_x_n_per_m=-0.5),  # failed to reverse sign
            replace(self.controls, inversion_180_relative_reversal_error=0.02),
        ]
        for bad_ctrl in corrupted_cases:
            self.assertFalse(verify_control_assertions(bad_ctrl, strict=False))
            with self.assertRaises(ValueError):
                verify_control_assertions(bad_ctrl, strict=True)

    def test_tajmar_schreiber_literature_audit_accurately_characterizes_apparatus_and_confounders(self):
        """Regression P2-R1-F1: verify accurate apparatus description and candidate confounder framing."""
        lit = self.controls.literature_audit
        self.assertIn("10.1016/j.elstat.2020.103477", lit.tajmar_schreiber_doi)
        self.assertIn("Faraday cage", lit.tajmar_schreiber_apparatus)
        self.assertIn("precision balance", lit.tajmar_schreiber_apparatus)
        self.assertNotIn("torsion", lit.tajmar_schreiber_apparatus.lower())
        self.assertAlmostEqual(lit.tajmar_schreiber_max_voltage_v, 10000.0)
        self.assertAlmostEqual(lit.tajmar_schreiber_mass_accuracy_mg, 0.3)
        self.assertAlmostEqual(lit.tajmar_schreiber_force_accuracy_n * 1e6, 2.94, places=2)
        self.assertEqual(lit.comparison_status, "CONTEXTUAL_QUALITATIVE_ONLY_MISMATCHED_APPARATUS")
        self.assertGreaterEqual(len(lit.candidate_confounders_not_established_causes), 3)
        self.assertIn("candidate confounders", self.controls.literature_benchmark_summary.lower())


class ExodusMeshConvergenceAndManifestTests(unittest.TestCase):
    """Test 2D mesh convergence, manifest schema 1.2.0, and P0/P1 baseline preservation."""

    def test_2d_mesh_convergence_study_monotone_and_conserved(self):
        rows = run_mesh_convergence_study()
        self.assertEqual(len(rows), 4)
        residuals = [r["residual_3d_extruded_n"] for r in rows]
        # Coarse residual is under 250 uN, refined grids achieve < 60 uN (< 0.1% relative residual)
        self.assertLess(residuals[0], 2.5e-4)
        self.assertLess(residuals[1], 6.0e-5)
        self.assertLess(residuals[2], 6.0e-5)
        self.assertLess(residuals[3], 6.0e-5)

        # Step-to-step relative change delta_k drops monotonically (12.18% -> 6.17% -> 2.61%)
        rel_chgs = [r["relative_change_blade_to_prev"] for r in rows[1:]]
        self.assertLess(rel_chgs[1], rel_chgs[0])
        self.assertLess(rel_chgs[2], rel_chgs[1])

        # Commensurate discretization ratios are 1.0
        for r in rows:
            self.assertAlmostEqual(r["tip_width_discretization_ratio"], 1.0, places=4)

        # Observed convergence order p_obs is in [0.2, 0.5] (consistent with r^-1/3 corner singularity)
        self.assertIn("observed_convergence_order_p_obs", rows[-1])
        p_obs = rows[-1]["observed_convergence_order_p_obs"]
        self.assertGreaterEqual(p_obs, 0.2, "Observed order must be >= 0.2")
        self.assertLessEqual(p_obs, 0.5, "Observed order must be <= 0.5")

        # Measured log-log tip field scaling alpha_tip is in [0.2, 0.5]
        for k in range(1, len(rows)):
            alpha = rows[k]["log_log_tip_scaling_alpha"]
            self.assertGreaterEqual(alpha, 0.2, f"Step {k} tip scaling alpha must be >= 0.2")
            self.assertLessEqual(alpha, 0.5, f"Step {k} tip scaling alpha must be <= 0.5")

        # Richardson extrapolation limits and assumed-order labeling
        self.assertTrue(rows[-1]["richardson_is_assumed_order_estimate"])
        self.assertIn("richardson_assumed_p1_estimate_n", rows[-1])
        self.assertIn("richardson_observed_order_extrapolated_n", rows[-1])
        self.assertIn("richardson_extrapolated_blade_3d_n", rows[-1])
        self.assertIn("estimated_discretization_error_percent", rows[-1])
        self.assertLess(rows[-1]["estimated_discretization_error_percent"], 15.0)

    def test_adversarial_rejection_of_stale_pr_or_literature_metadata(self):
        """Regression P2-R2-M1 & P2-R3-M1: PR metadata, literature audit, and manifest must reject stale claims."""
        # 1. Literature benchmark audit rejects torsion balance conflation
        params = ExodusPatentParameters(dx_m=0.001, dy_m=0.001)
        res = evaluate_exodus_patent(params)
        lit = res.controls.literature_audit
        self.assertNotIn("torsion", lit.tajmar_schreiber_apparatus.lower())
        self.assertEqual(lit.tajmar_schreiber_max_voltage_v, 10000.0)

        # 2. Manifest includes separated 3D FIG 21 model, 5-part uncertainty budget, and updated review status
        man = generate_exodus_patent_manifest(res)
        self.assertIn("fig21_nine_blade_3d_finite_model", man)
        self.assertIn("linear_algebra_solver_residual", man["finite_3d_apparatus_model"])
        self.assertIn("discrete_momentum_closure_residual_micro_n", man["finite_3d_apparatus_model"])
        self.assertIn("target_patent_effect_scale_micro_n", man["finite_3d_apparatus_model"])
        self.assertIn("uncertainty_budget_5_part", man["finite_3d_apparatus_model"])
        self.assertIn("uncertainty_budget_5_part", man["fig21_nine_blade_3d_finite_model"])
        self.assertIn(
            "COMMENSURATE_2D_CONVERGENCE_ANALYZED",
            man["scientific_disposition"]["force_convergence_status"],
        )

        # 3. Mechanically verify docs/PR_DESCRIPTION.md has no stale or conflicting claims (P2-R3-M1)
        pr_desc_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "PR_DESCRIPTION.md")
        self.assertTrue(os.path.exists(pr_desc_path), "docs/PR_DESCRIPTION.md must exist")
        with open(pr_desc_path, "r", encoding="utf-8") as f:
            pr_text = f.read()
        self.assertNotIn("in high vacuum", pr_text.lower(), "PR description must not falsely claim Tajmar & Schreiber was in high vacuum")
        self.assertNotIn("o = 2.0 in", pr_text.lower(), "PR description must not conflate overlap O with ground plane width W_gnd")
        self.assertIn("W_{\\text{gnd}} = 2.0", pr_text, "PR description must explicitly identify W_gnd = 2.0 in")
        self.assertIn("o = 0.0", pr_text.lower(), "PR description must state O = 0.0 m lateral offset")
        self.assertIn("NOT_RESOLVED_AT_CURRENT_3D_GRID_RESOLUTION", pr_text)

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
        self.assertIn("separated_fig21_nine_blade_epoxy_embodiment_summary", manifest)
        self.assertIn("fig21_nine_blade_3d_finite_model", manifest)
        self.assertIn("evaluated_controls_and_contextual_literature", manifest)
        self.assertIn("scientific_disposition", manifest)

        self.assertEqual(
            manifest["scientific_disposition"]["physical_thrust_measurement"],
            "NOT_MEASURED_AND_NOT_EVALUATED_NUMERICAL_SIMULATION_ONLY",
        )

    def test_p0_and_p1_baselines_remain_preserved(self):
        res = subprocess.run(
            ["git", "hash-object", "electrostatics_baseline.py"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(res.stdout.strip(), "97f65dfa25db7730323edd5e52c98b17371fdeaa")

        self.assertTrue(os.path.exists("scalar_wave_3d.py"))
        self.assertTrue(os.path.exists("electrostatics_numerics.py"))
        self.assertTrue(os.path.exists("tests/test_p1_wave_3d.py"))
        self.assertTrue(os.path.exists("tests/test_p1_numerics.py"))


if __name__ == "__main__":
    unittest.main()
