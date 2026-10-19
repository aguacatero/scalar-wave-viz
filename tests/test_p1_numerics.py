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
        """P1-R1-F3 regression: asymmetric voltages produce demonstrably nonzero enclosure reaction force."""
        cfg = eb.GroundedBoxConfig(
            left_electrode=eb.ElectrodeConfig(center_x_m=-0.008, voltage_v=600.0),
            right_electrode=eb.ElectrodeConfig(center_x_m=0.008, voltage_v=100.0),
            n=81,
        )
        sol = eb.electrode_pair_in_grounded_box(config=cfg)
        budget = en.evaluate_whole_apparatus_force_budget(sol, tolerance_n_per_m=2e-4)

        # Net electrode force is non-zero (asymmetric pull)
        f_elec = budget.left_electrode_fx_n_per_m + budget.right_electrode_fx_n_per_m
        self.assertGreater(abs(f_elec), 1e-4)

        # Enclosure reaction force is demonstrably non-zero and opposes electrode sum
        self.assertGreater(abs(budget.enclosure_reaction_fx_n_per_m), 1e-4)
        self.assertAlmostEqual(
            budget.enclosure_reaction_fx_n_per_m,
            -f_elec,
            places=4,
        )

        # Full system balances without algebraic cancellation
        self.assertTrue(budget.is_force_balanced_to_tolerance)

    def test_force_mesh_convergence(self):
        """P1-R1-F3 regression: individual Maxwell stress forces converge asymptotically under mesh refinement."""
        study = en.force_mesh_convergence_study(n_list=(41, 81, 161))
        self.assertEqual(len(study.rows), 3)
        self.assertTrue(study.is_converged_to_tolerance)
        self.assertLess(study.uncertainty_budget_n_per_m, 5e-4)

        # Verify individual forces are non-zero and converge
        for r in study.rows:
            self.assertGreater(r.left_electrode_fx_n_per_m, 0.0)
            self.assertLess(r.right_electrode_fx_n_per_m, 0.0)

    def test_contour_invariance_in_vacuum(self):
        """P1-R1-F3 regression: Maxwell stress integral is invariant across concentric vacuum loops."""
        sol = eb.electrode_pair_in_grounded_box(n=81)
        res = en.contour_invariance_study(sol, electrode='left', margins_m=(0.0018, 0.0024, 0.0030))
        self.assertTrue(res.is_invariant_to_tolerance)
        self.assertLess(res.max_relative_variation, 0.01)  # < 1% variation across loops


if __name__ == '__main__':
    unittest.main()

