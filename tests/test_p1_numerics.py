"""Unit and regression tests for P1 advanced numerics and Maxwell stress accounting."""
import unittest
import numpy as np

import electrostatics_baseline as eb
import electrostatics_numerics as en


class HarmonicPolynomialTests(unittest.TestCase):
    def test_cubic_polynomial_exactness_across_grids(self):
        """P1-A: 5-point stencil solves cubic harmonic polynomial to machine precision.

        Potential error is zero (< 1e-10 V).
        Electric field central-difference gradient has exact analytic truncation error (V0/L^3)*h^2.
        """
        results = en.harmonic_polynomial_benchmark(n_list=(21, 41, 81), v_0_v=100.0)
        self.assertEqual(len(results), 3)
        for r in results:
            self.assertTrue(r.is_exact_to_tolerance)
            self.assertLess(r.max_potential_error_v, 1e-10)
            self.assertLess(r.max_discrete_residual_v, 1e-10)

            # Central-difference gradient truncation error on x^3 is exactly (V0/L^3)*h^2,
            # while y-derivative is linear in y and has zero truncation error (< 1e-10 V/m)
            scale = (r.box_width_m / 2.0) ** 3
            expected_truncation_err = (r.v_0_v / scale) * (r.grid_spacing_m ** 2)
            self.assertAlmostEqual(r.max_ex_error_v_per_m, expected_truncation_err, places=8)
            self.assertLess(r.max_ey_error_v_per_m, 1e-9)


class HarmonicTrigConvergenceTests(unittest.TestCase):
    def test_second_order_asymptotic_convergence(self):
        """P1-A: smooth harmonic sine/sinh solution demonstrates O(h^2) convergence rate."""
        results = en.harmonic_trig_benchmark(n_list=(21, 41, 81, 161), v_0_v=100.0)
        self.assertEqual(len(results), 4)

        # Monotonic error reduction
        for i in range(len(results) - 1):
            self.assertLess(results[i + 1].max_potential_error_v, results[i].max_potential_error_v)
            self.assertLess(results[i + 1].l2_potential_error_v, results[i].l2_potential_error_v)
            self.assertLess(results[i + 1].max_field_error_v_per_m, results[i].max_field_error_v_per_m)

        # Check observed asymptotic convergence orders for finest grids
        finest = results[-1]
        self.assertIsNotNone(finest.observed_order_potential)
        self.assertIsNotNone(finest.observed_order_field)
        self.assertAlmostEqual(finest.observed_order_potential, 2.0, delta=0.05)
        self.assertAlmostEqual(finest.observed_order_field, 2.0, delta=0.10)


class EnclosureSensitivityTests(unittest.TestCase):
    def test_grounded_enclosure_sensitivity_sweep(self):
        """P1-A: outer box size sweep demonstrates boundary coupling."""
        results = en.enclosure_size_sensitivity_study(box_widths_m=(0.03, 0.04, 0.06, 0.08))
        self.assertEqual(len(results), 4)

        # Wall fields must decrease monotonically as the grounded walls recede
        for i in range(len(results) - 1):
            self.assertGreater(results[i].max_outer_wall_field_v_per_m, results[i + 1].max_outer_wall_field_v_per_m)

        # Midpoint Ex must be finite and positive; Ey must be negligible relative to Ex (< 0.01% of Ex)
        for r in results:
            self.assertGreater(r.midpoint_ex_v_per_m, 50e3)
            self.assertLess(abs(r.midpoint_ey_v_per_m) / r.midpoint_ex_v_per_m, 1e-4)


class MaxwellStressContourTests(unittest.TestCase):
    def test_empty_vacuum_loop_yields_zero_force(self):
        """P1-B: Maxwell stress contour enclosing no charge integrates to zero."""
        sol = eb.electrode_pair_in_grounded_box(n=81)
        # Loop in vacuum between electrodes around origin
        res = en.compute_maxwell_stress_contour(
            sol,
            x_bounds_m=(-0.002, 0.002),
            y_bounds_m=(-0.002, 0.002),
            require_vacuum=True,
        )
        self.assertTrue(res.is_pure_vacuum)
        self.assertEqual(res.units, 'N/m')
        # Stress divergence theorem: empty loop force must be within discretization tolerance
        self.assertLess(res.net_force_magnitude_n_per_m, 1e-4)

    def test_symmetric_electrodes_have_equal_and_opposite_forces(self):
        """P1-B: symmetric electrode pair experiences equal and opposite mutual attraction."""
        sol = eb.electrode_pair_in_grounded_box(n=81)
        budget = en.evaluate_whole_apparatus_force_budget(sol, tolerance_n_per_m=5e-4)

        # Electrodes attract: left electrode pulled toward +x, right toward -x
        self.assertGreater(budget.left_electrode_fx_n_per_m, 0.0)
        self.assertLess(budget.right_electrode_fx_n_per_m, 0.0)

        # Opposite attraction magnitudes match by symmetry
        self.assertAlmostEqual(
            budget.left_electrode_fx_n_per_m,
            -budget.right_electrode_fx_n_per_m,
            places=4,
        )
        # Vertical forces are zero by horizontal symmetry
        self.assertAlmostEqual(budget.left_electrode_fy_n_per_m, 0.0, places=5)
        self.assertAlmostEqual(budget.right_electrode_fy_n_per_m, 0.0, places=5)

    def test_whole_apparatus_force_balance_and_unmodeled_supports(self):
        """P1-B: complete system (electrodes + enclosure) balances; identifies missing supports."""
        sol = eb.electrode_pair_in_grounded_box(n=81)
        budget = en.evaluate_whole_apparatus_force_budget(sol, tolerance_n_per_m=1e-3)

        self.assertEqual(budget.units, 'N/m')
        self.assertIn('supports', budget.unmodeled_reaction_explanation)
        self.assertTrue(budget.is_force_balanced_to_tolerance)

    def test_non_vacuum_contour_rejected_when_strict(self):
        """P1-B: contour cutting through a conductor raises ValueError in strict mode."""
        sol = eb.electrode_pair_in_grounded_box(n=81)
        # Contour through left electrode center (-0.008, 0.0)
        with self.assertRaises(ValueError) as ctx:
            en.compute_maxwell_stress_contour(
                sol,
                x_bounds_m=(-0.009, -0.007),
                y_bounds_m=(-0.001, 0.001),
                require_vacuum=True,
            )
        self.assertIn('intersects non-vacuum', str(ctx.exception))

    def test_asymmetric_voltage_geometry_produces_nonzero_enclosure_reaction(self):
        """P1-R1-F3 / P1-R2-F3 / P1-R3-F1 regression: asymmetric voltages produce nonzero enclosure reaction with full 2D vector residual closure."""
        cfg = eb.GroundedBoxConfig(
            left_electrode=eb.ElectrodeConfig(center_x_m=-0.008, voltage_v=600.0),
            right_electrode=eb.ElectrodeConfig(center_x_m=0.008, voltage_v=100.0),
            n=81,
        )
        sol = eb.electrode_pair_in_grounded_box(config=cfg)
        budget = en.evaluate_whole_apparatus_force_budget(sol, tolerance_n_per_m=1e-6)

        # Net electrode force is non-zero (asymmetric pull)
        f_elec_x = budget.left_electrode_fx_n_per_m + budget.right_electrode_fx_n_per_m
        f_elec_y = budget.left_electrode_fy_n_per_m + budget.right_electrode_fy_n_per_m
        self.assertGreater(abs(f_elec_x), 1e-4)

        # Enclosure reaction force is demonstrably non-zero and opposes electrode sum in both x and y
        self.assertGreater(abs(budget.enclosure_reaction_fx_n_per_m), 1e-4)
        self.assertAlmostEqual(budget.enclosure_reaction_fx_n_per_m, -f_elec_x, places=6)
        self.assertAlmostEqual(budget.enclosure_reaction_fy_n_per_m, -f_elec_y, places=6)

        # P1-R2-F3 & P1-R3-F1: Assert tight bound on full 2D vector residual (fx, fy, and 2D norm)
        res_x = budget.net_electrostatic_force_fx_n_per_m
        res_y = budget.net_electrostatic_force_fy_n_per_m
        res_mag = float(np.hypot(res_x, res_y))
        self.assertLess(abs(res_x), 1e-7)
        self.assertLess(abs(res_y), 1e-7)
        self.assertLess(res_mag, 1e-7)
        self.assertLess(res_mag / abs(f_elec_x), 1e-3)  # < 0.1% relative 2D vector residual

        # Near-zero vertical components on y-symmetric geometry are explicitly bounded
        self.assertLess(abs(budget.left_electrode_fy_n_per_m), 1e-7)
        self.assertLess(abs(budget.right_electrode_fy_n_per_m), 1e-7)
        self.assertLess(abs(budget.enclosure_reaction_fy_n_per_m), 1e-7)

        # Full system balances without algebraic cancellation
        self.assertTrue(budget.is_force_balanced_to_tolerance)

    def test_off_axis_y_asymmetric_geometry_full_vector_balance_and_convergence(self):
        """P1-R3-F1 regression: off-axis y-asymmetric electrodes produce nontrivial Fx and Fy on all conductors with full 6-component convergence."""
        cfg_off_axis = eb.GroundedBoxConfig(
            left_electrode=eb.ElectrodeConfig(center_x_m=-0.008, center_y_m=0.004, voltage_v=600.0),
            right_electrode=eb.ElectrodeConfig(center_x_m=0.008, center_y_m=-0.002, voltage_v=-400.0),
            n=81,
        )
        sol = eb.electrode_pair_in_grounded_box(config=cfg_off_axis)
        budget = en.evaluate_whole_apparatus_force_budget(sol, tolerance_n_per_m=1e-6)

        # All six conductor force components (left Fx/Fy, right Fx/Fy, box Fx/Fy) are demonstrably non-zero
        self.assertGreater(abs(budget.left_electrode_fx_n_per_m), 1e-5)
        self.assertGreater(abs(budget.left_electrode_fy_n_per_m), 1e-5)
        self.assertGreater(abs(budget.right_electrode_fx_n_per_m), 1e-5)
        self.assertGreater(abs(budget.right_electrode_fy_n_per_m), 1e-5)
        self.assertGreater(abs(budget.enclosure_reaction_fx_n_per_m), 1e-5)
        self.assertGreater(abs(budget.enclosure_reaction_fy_n_per_m), 1e-5)

        # Full 2D vector balance
        res_x = budget.net_electrostatic_force_fx_n_per_m
        res_y = budget.net_electrostatic_force_fy_n_per_m
        res_mag = float(np.hypot(res_x, res_y))
        f_box_mag = float(np.hypot(budget.enclosure_reaction_fx_n_per_m, budget.enclosure_reaction_fy_n_per_m))
        self.assertLess(abs(res_x), 1e-7)
        self.assertLess(abs(res_y), 1e-7)
        self.assertLess(res_mag, 1e-7)
        self.assertLess(res_mag / f_box_mag, 1e-3)
        self.assertTrue(budget.is_force_balanced_to_tolerance)

        # Mesh convergence across (41, 81, 161) on off-axis configuration
        study_off = en.force_mesh_convergence_study(
            n_list=(41, 81, 161),
            config=cfg_off_axis,
            tolerance_relative_change=0.05,
            tolerance_residual_n_per_m=1e-7,
        )
        self.assertTrue(study_off.is_converged_to_tolerance)
        self.assertEqual(set(study_off.component_assessments.keys()), {
            'left_fx', 'left_fy', 'right_fx', 'right_fy', 'box_fx', 'box_fy',
        })
        for name, comp in study_off.component_assessments.items():
            self.assertEqual(comp.regime, 'ACTIVE_RELATIVE_AND_ABS', f'{name} should be in active regime')
            self.assertTrue(comp.is_converged, f'{name} failed convergence')
            self.assertIsNotNone(comp.last_step_relative_change)
            self.assertLessEqual(comp.last_step_relative_change, 0.05)

    def test_force_mesh_convergence(self):
        """P1-R1-F3 / P1-R2-F2 / P1-R3-F1 regression: all 6 force components and 2D vector residual converge under mesh refinement."""
        # 1. Symmetric setup (+-500V): Fx active, Fy near-zero and gated by absolute tolerance
        study_sym = en.force_mesh_convergence_study(n_list=(41, 81, 161), tolerance_relative_change=0.05)
        self.assertEqual(len(study_sym.rows), 3)
        self.assertTrue(study_sym.is_converged_to_tolerance)
        self.assertLess(study_sym.max_component_relative_change, 0.05)
        self.assertLess(study_sym.max_component_last_step_diff_n_per_m, 5e-4)
        self.assertLess(study_sym.left_fx_last_step_diff_n_per_m, 5e-4)
        self.assertIn('NOT a formal probabilistic uncertainty budget', study_sym.discretization_error_note)

        # Verify near-zero components (left_fy, right_fy, box_fy, box_fx) are explicitly assessed in NEAR_ZERO_ABSOLUTE regime
        for comp_name in ('left_fy', 'right_fy', 'box_fx', 'box_fy'):
            comp = study_sym.component_assessments[comp_name]
            self.assertEqual(comp.regime, 'NEAR_ZERO_ABSOLUTE')
            self.assertTrue(comp.is_converged)
            self.assertLessEqual(comp.last_step_abs_diff_n_per_m, 1e-6)

        for r in study_sym.rows:
            self.assertGreater(r.left_electrode_fx_n_per_m, 0.0)
            self.assertLess(r.right_electrode_fx_n_per_m, 0.0)
            self.assertLess(r.net_residual_magnitude_n_per_m, 1e-6)

        # 2. Asymmetric setup (+600V / +100V) evaluating nonzero enclosure reaction convergence
        cfg_asym = eb.GroundedBoxConfig(
            left_electrode=eb.ElectrodeConfig(center_x_m=-0.008, voltage_v=600.0),
            right_electrode=eb.ElectrodeConfig(center_x_m=0.008, voltage_v=100.0),
        )
        study_asym = en.force_mesh_convergence_study(
            n_list=(41, 81, 161),
            config=cfg_asym,
            tolerance_relative_change=0.05,
            tolerance_residual_n_per_m=1e-7,
        )
        self.assertTrue(study_asym.is_converged_to_tolerance)
        self.assertLess(study_asym.max_component_relative_change, 0.05)
        self.assertGreater(abs(study_asym.rows[-1].enclosure_reaction_fx_n_per_m), 1e-4)
        self.assertLess(study_asym.rows[-1].net_residual_magnitude_n_per_m, 1e-7)
        self.assertEqual(study_asym.component_assessments['box_fx'].regime, 'ACTIVE_RELATIVE_AND_ABS')
        self.assertTrue(study_asym.component_assessments['box_fx'].is_converged)

    def test_force_convergence_gate_rejects_corrupted_fy_or_near_zero_or_residual(self):
        """P1-R3-F1 adversarial regression: convergence gate fails closed on Fy drift, near-zero drift, or y-residual."""
        study_base = en.force_mesh_convergence_study(n_list=(41, 81, 161))
        self.assertTrue(study_base.is_converged_to_tolerance)
        r0, r1, r2 = study_base.rows

        # Case A: Near-zero component (left_fy) shifts by 5e-6 N/m (> 1e-6 near-zero tolerance) while balanced by box_fy
        r2_bad_near_zero = en.ForceMeshConvergenceRow(
            n=r2.n,
            grid_spacing_m=r2.grid_spacing_m,
            left_electrode_fx_n_per_m=r2.left_electrode_fx_n_per_m,
            right_electrode_fx_n_per_m=r2.right_electrode_fx_n_per_m,
            enclosure_reaction_fx_n_per_m=r2.enclosure_reaction_fx_n_per_m,
            net_residual_fx_n_per_m=r2.net_residual_fx_n_per_m,
            left_electrode_fy_n_per_m=5e-6,
            right_electrode_fy_n_per_m=0.0,
            enclosure_reaction_fy_n_per_m=-5e-6,
            net_residual_fy_n_per_m=0.0,
            net_residual_magnitude_n_per_m=abs(r2.net_residual_fx_n_per_m),
        )
        eval_bad_nz = en.evaluate_force_convergence_from_rows([r0, r1, r2_bad_near_zero])
        self.assertFalse(eval_bad_nz.is_converged_to_tolerance)
        self.assertFalse(eval_bad_nz.component_assessments['left_fy'].is_converged)

        # Case B: Active Fy component shifts by 20% (> 5% relative tolerance)
        r1_active_fy = en.ForceMeshConvergenceRow(
            n=r1.n,
            grid_spacing_m=r1.grid_spacing_m,
            left_electrode_fx_n_per_m=r1.left_electrode_fx_n_per_m,
            right_electrode_fx_n_per_m=r1.right_electrode_fx_n_per_m,
            enclosure_reaction_fx_n_per_m=r1.enclosure_reaction_fx_n_per_m,
            net_residual_fx_n_per_m=r1.net_residual_fx_n_per_m,
            left_electrode_fy_n_per_m=1.0e-4,
            right_electrode_fy_n_per_m=0.0,
            enclosure_reaction_fy_n_per_m=-1.0e-4,
            net_residual_fy_n_per_m=0.0,
            net_residual_magnitude_n_per_m=abs(r1.net_residual_fx_n_per_m),
        )
        r2_bad_active_fy = en.ForceMeshConvergenceRow(
            n=r2.n,
            grid_spacing_m=r2.grid_spacing_m,
            left_electrode_fx_n_per_m=r2.left_electrode_fx_n_per_m,
            right_electrode_fx_n_per_m=r2.right_electrode_fx_n_per_m,
            enclosure_reaction_fx_n_per_m=r2.enclosure_reaction_fx_n_per_m,
            net_residual_fx_n_per_m=r2.net_residual_fx_n_per_m,
            left_electrode_fy_n_per_m=1.3e-4,
            right_electrode_fy_n_per_m=0.0,
            enclosure_reaction_fy_n_per_m=-1.3e-4,
            net_residual_fy_n_per_m=0.0,
            net_residual_magnitude_n_per_m=abs(r2.net_residual_fx_n_per_m),
        )
        eval_bad_fy = en.evaluate_force_convergence_from_rows([r0, r1_active_fy, r2_bad_active_fy])
        self.assertFalse(eval_bad_fy.is_converged_to_tolerance)
        self.assertFalse(eval_bad_fy.component_assessments['left_fy'].is_converged)

        # Case C: Non-zero net_residual_fy violates residual gate even when net_residual_fx is tiny
        r2_bad_res_y = en.ForceMeshConvergenceRow(
            n=r2.n,
            grid_spacing_m=r2.grid_spacing_m,
            left_electrode_fx_n_per_m=r2.left_electrode_fx_n_per_m,
            right_electrode_fx_n_per_m=r2.right_electrode_fx_n_per_m,
            enclosure_reaction_fx_n_per_m=r2.enclosure_reaction_fx_n_per_m,
            net_residual_fx_n_per_m=r2.net_residual_fx_n_per_m,
            left_electrode_fy_n_per_m=5e-7,
            right_electrode_fy_n_per_m=5e-7,
            enclosure_reaction_fy_n_per_m=5e-7,
            net_residual_fy_n_per_m=1.5e-6,
            net_residual_magnitude_n_per_m=float(np.hypot(r2.net_residual_fx_n_per_m, 1.5e-6)),
        )
        eval_bad_res_y = en.evaluate_force_convergence_from_rows(
            [r0, r1, r2_bad_res_y], tolerance_residual_n_per_m=1e-6
        )
        self.assertFalse(eval_bad_res_y.is_converged_to_tolerance)

    def test_virtual_work_force_cross_check(self):
        """P1-R2-F2 / P1-R3-F2 regression: multi-resolution virtual-work cross-check on symmetric and asymmetric (+600V/+100V) setups for both electrodes."""
        # 1. Symmetric (+-500V) convergence & step-size sensitivity across n=(81, 161)
        study_sym = en.virtual_work_convergence_and_sensitivity_study(
            config=eb.GroundedBoxConfig(),
            n_list=(81, 161),
            tolerance_finest_rel_diff=0.07,
        )
        self.assertTrue(study_sym.is_consistent_to_tolerance)
        self.assertTrue(study_sym.all_signs_consistent)
        self.assertTrue(study_sym.left_discrepancy_decreases_with_refinement)
        self.assertTrue(study_sym.right_discrepancy_decreases_with_refinement)
        # Assert n=81 (~8.62%) and refined n=161 (~4.49%) agreement and exact left/right symmetry
        self.assertLess(study_sym.rows[0].left_rel_diff_1h, 0.09)
        self.assertLess(study_sym.rows[-1].left_rel_diff_1h, 0.05)
        self.assertLess(study_sym.rows[-1].right_rel_diff_1h, 0.05)
        self.assertLess(study_sym.rows[-1].left_step_sensitivity_rel, 0.005)
        self.assertAlmostEqual(
            study_sym.rows[-1].left_vw_fx_1h_n_per_m,
            -study_sym.rows[-1].right_vw_fx_1h_n_per_m,
            places=10,
        )

        # 2. Asymmetric (+600V / +100V) convergence & step-size sensitivity across n=(81, 161) for both electrodes
        cfg_asym = eb.GroundedBoxConfig(
            left_electrode=eb.ElectrodeConfig(center_x_m=-0.008, voltage_v=600.0),
            right_electrode=eb.ElectrodeConfig(center_x_m=0.008, voltage_v=100.0),
        )
        study_asym = en.virtual_work_convergence_and_sensitivity_study(
            config=cfg_asym,
            n_list=(81, 161),
            tolerance_finest_rel_diff=0.10,
        )
        self.assertTrue(study_asym.is_consistent_to_tolerance)
        self.assertTrue(study_asym.all_signs_consistent)
        self.assertTrue(study_asym.left_discrepancy_decreases_with_refinement)
        self.assertTrue(study_asym.right_discrepancy_decreases_with_refinement)

        # In +600V/+100V, both left and right electrodes are pulled in -x; enclosure reaction is +x
        finest_asym = study_asym.rows[-1]
        self.assertLess(finest_asym.left_mst_fx_n_per_m, 0.0)
        self.assertLess(finest_asym.left_vw_fx_1h_n_per_m, 0.0)
        self.assertLess(finest_asym.right_mst_fx_n_per_m, 0.0)
        self.assertLess(finest_asym.right_vw_fx_1h_n_per_m, 0.0)
        self.assertLess(finest_asym.left_rel_diff_1h, 0.065)         # ~6.00% at n=161 (down from 11.84% at n=81)
        self.assertLess(finest_asym.right_rel_diff_1h, 0.10)         # ~9.61% at n=161 (down from 18.68% at n=81)
        self.assertLess(finest_asym.net_electrode_rel_diff_1h, 0.07) # ~6.67% on combined electrode pull at n=161 (down from 13.08% at n=81)
        self.assertLess(finest_asym.left_step_sensitivity_rel, 0.01) # ~0.17% step sensitivity (1h vs 2h)
        self.assertLess(finest_asym.right_step_sensitivity_rel, 0.01) # ~0.33% step sensitivity (1h vs 2h)
        self.assertIn('limited electrode-force benchmark', study_asym.epistemic_limitation_note)

    def test_contour_invariance_in_vacuum(self):
        """P1-R1-F3 / P1-R2-F2 regression: Maxwell stress integral is invariant across concentric vacuum loops."""
        # 1. Electrode contour invariance
        sol_sym = eb.electrode_pair_in_grounded_box(n=81)
        res_elec = en.contour_invariance_study(sol_sym, electrode='left', margins_m=(0.0018, 0.0024, 0.0030))
        self.assertTrue(res_elec.is_invariant_to_tolerance)
        self.assertLess(res_elec.max_relative_variation, 0.01)  # < 1% variation across loops

        # 2. Enclosure inner boundary contour invariance on asymmetric geometry
        cfg_asym = eb.GroundedBoxConfig(
            left_electrode=eb.ElectrodeConfig(center_x_m=-0.008, voltage_v=600.0),
            right_electrode=eb.ElectrodeConfig(center_x_m=0.008, voltage_v=100.0),
            n=81,
        )
        sol_asym = eb.electrode_pair_in_grounded_box(config=cfg_asym)
        res_box = en.contour_invariance_study(sol_asym, electrode='enclosure')
        self.assertTrue(res_box.is_invariant_to_tolerance)
        self.assertLess(res_box.max_relative_variation, 0.01)  # < 1% variation across enclosure loops


class IndependentSolverVerificationTests(unittest.TestCase):
    def test_independent_matrix_free_sor_vs_direct_lu_solver(self):
        """P1-R4-F3: Matrix-free Red-Black SOR Laplace solver matches scipy sparse direct LU solver to < 1e-8 V."""
        cfg = eb.GroundedBoxConfig(
            n=81,
            left_electrode=eb.ElectrodeConfig(center_x_m=-0.008, center_y_m=0.004, radius_m=0.003, voltage_v=600.0),
            right_electrode=eb.ElectrodeConfig(center_x_m=0.008, center_y_m=-0.002, radius_m=0.003, voltage_v=-400.0),
        )
        sol_lu = eb.electrode_pair_in_grounded_box(config=cfg)
        sol_sor = en.solve_dirichlet_independent_matrix_free_sor(config=cfg, tolerance_v=1e-10)

        max_pot_diff = float(np.max(np.abs(sol_lu.potential_v - sol_sor.potential_v)))
        self.assertLess(max_pot_diff, 1e-8)
        self.assertLess(sol_sor.max_discrete_residual_v, 1e-8)

        # Force budgets evaluated from both independent solver solutions match to high precision
        b_lu = en.evaluate_whole_apparatus_force_budget(sol_lu)
        b_sor = en.evaluate_whole_apparatus_force_budget(sol_sor)
        self.assertAlmostEqual(b_lu.left_electrode_fx_n_per_m, b_sor.left_electrode_fx_n_per_m, places=7)
        self.assertAlmostEqual(b_lu.left_electrode_fy_n_per_m, b_sor.left_electrode_fy_n_per_m, places=7)
        self.assertAlmostEqual(b_lu.right_electrode_fx_n_per_m, b_sor.right_electrode_fx_n_per_m, places=7)
        self.assertAlmostEqual(b_lu.right_electrode_fy_n_per_m, b_sor.right_electrode_fy_n_per_m, places=7)
        self.assertAlmostEqual(b_lu.enclosure_reaction_fx_n_per_m, b_sor.enclosure_reaction_fx_n_per_m, places=7)
        self.assertAlmostEqual(b_lu.enclosure_reaction_fy_n_per_m, b_sor.enclosure_reaction_fy_n_per_m, places=7)

    def test_independent_mfs_continuous_laplace_solver_and_harmonic_certificate(self):
        """P1-R4-F3: Continuous grid-free Method of Fundamental Solutions satisfies Maximum Principle certificate."""
        cfg = eb.GroundedBoxConfig(
            left_electrode=eb.ElectrodeConfig(center_x_m=-0.008, center_y_m=0.004, radius_m=0.003, voltage_v=600.0),
            right_electrode=eb.ElectrodeConfig(center_x_m=0.008, center_y_m=-0.002, radius_m=0.003, voltage_v=-400.0),
        )
        mfs = en.solve_electrostatics_mfs_boundary_collocation(cfg)

        # Harmonic Maximum Principle certificate: interior potential error is strictly bounded by max boundary error
        self.assertLess(mfs.max_independent_boundary_error_v, 1e-3)
        self.assertLess(mfs.max_independent_boundary_error_v, 1e-9)  # Observed ~8.06e-11 V
        # Whole-apparatus closed contour Maxwell stress integrates to zero
        self.assertLess(mfs.net_residual_magnitude_n_per_m, 1e-8)

    def test_independent_electrostatic_solver_verification_study(self):
        """P1-R4-F3: 5-point Cartesian FDM converges toward grid-free continuous MFS reference with mesh refinement."""
        res = en.benchmark_independent_electrostatic_solver_verification(n_list=(41, 81, 161, 321))
        self.assertTrue(res.is_verified_to_tolerance)
        self.assertTrue(res.errors_decrease_toward_mfs_with_refinement)
        self.assertLess(res.sor_vs_direct_lu_max_potential_diff_v, 1e-8)

        # Monotonic convergence of staircase FDM toward continuous MFS solution across resolutions
        finest = res.fdm_vs_mfs_rows[-1]
        coarsest = res.fdm_vs_mfs_rows[0]
        self.assertEqual(finest.n, 321)
        self.assertLess(finest.left_force_vec_rel_error_vs_mfs, coarsest.left_force_vec_rel_error_vs_mfs)
        self.assertLess(finest.right_force_vec_rel_error_vs_mfs, coarsest.right_force_vec_rel_error_vs_mfs)
        self.assertLess(finest.enclosure_force_vec_rel_error_vs_mfs, coarsest.enclosure_force_vec_rel_error_vs_mfs)
        self.assertLess(finest.midpoint_e_rel_error_vs_mfs, coarsest.midpoint_e_rel_error_vs_mfs)

        # Finest resolution (n=321) agrees with continuous MFS to within 5%
        self.assertLess(finest.left_force_vec_rel_error_vs_mfs, 0.05)
        self.assertLess(finest.right_force_vec_rel_error_vs_mfs, 0.05)
        self.assertLess(finest.enclosure_force_vec_rel_error_vs_mfs, 0.05)
        self.assertLess(finest.midpoint_e_rel_error_vs_mfs, 0.05)

        # Methodological distinction explicitly articulated
        self.assertIn('Methodological distinction', res.methodological_distinction_note)
        self.assertIn('Maxwell stress vs virtual work', res.methodological_distinction_note)
        self.assertIn('sparse direct LU (spsolve) vs matrix-free Red-Black SOR', res.methodological_distinction_note)
        self.assertIn('5-point staircase FDM vs grid-free Method of Fundamental Solutions', res.methodological_distinction_note)


if __name__ == '__main__':
    unittest.main()

