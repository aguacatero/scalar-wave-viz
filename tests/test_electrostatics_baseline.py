import unittest
import numpy as np
from electrostatics_baseline import (
    EPSILON_0_F_PER_M, electrode_pair_in_grounded_box,
    parallel_plate_benchmark, solve_dirichlet,
)


class PlateBenchmarkTests(unittest.TestCase):
    def test_ideal_capacitor_agrees_with_analytic_values(self):
        result = parallel_plate_benchmark(1000.0, 0.001, 0.0001)
        self.assertAlmostEqual(result.electric_field_v_per_m, 1e6)
        self.assertAlmostEqual(result.pressure_pa, 0.5 * EPSILON_0_F_PER_M * 1e12)
        self.assertAlmostEqual(result.force_on_positive_plate_n,
                               -result.force_on_negative_plate_n)
        self.assertEqual(result.net_pair_force_n, 0.0)
        self.assertAlmostEqual(result.stored_energy_j,
                               0.5 * EPSILON_0_F_PER_M * 1e12 * 1e-7)

    def test_force_scales_with_voltage_squared_and_gap_inverse_squared(self):
        a = parallel_plate_benchmark(100, 0.002, 1e-4)
        self.assertAlmostEqual(parallel_plate_benchmark(200,0.002,1e-4).pressure_pa / a.pressure_pa, 4)
        self.assertAlmostEqual(parallel_plate_benchmark(100,0.004,1e-4).pressure_pa / a.pressure_pa, 0.25)
        self.assertAlmostEqual(parallel_plate_benchmark(-100,0.002,1e-4).pressure_pa, a.pressure_pa)

    def test_invalid_inputs_rejected(self):
        for bad in (0, -0.1, np.inf, np.nan):
            with self.assertRaises(ValueError):
                parallel_plate_benchmark(100, bad, 0.01)
        with self.assertRaises(ValueError):
            parallel_plate_benchmark(100, 0.01, 0)


class LaplaceTests(unittest.TestCase):
    def test_linear_potential_is_exact_discrete_harmonic_solution(self):
        n = 21
        x, y = np.meshgrid(np.linspace(-1,1,n), np.linspace(-1,1,n), indexing='ij')
        expected = x + 2*y
        mask = np.zeros((n,n), dtype=bool)
        mask[0,:] = mask[-1,:] = True
        mask[:,0] = mask[:,-1] = True
        result = solve_dirichlet(mask, expected, 0.1)
        self.assertLess(np.max(np.abs(result.potential_v-expected)), 1e-11)
        self.assertLess(result.max_discrete_residual_v, 1e-11)
        self.assertLess(np.max(np.abs(result.ex_v_per_m+1)), 1e-9)
        self.assertLess(np.max(np.abs(result.ey_v_per_m+2)), 1e-9)

    def test_symmetric_pair_has_antisymmetric_potential(self):
        result = electrode_pair_in_grounded_box(n=61)
        self.assertLess(np.max(np.abs(result.potential_v + result.potential_v[::-1,:])), 1e-8)
        self.assertLess(result.max_discrete_residual_v, 1e-8)
        self.assertTrue(np.all(np.isfinite(result.ex_v_per_m)))

    def test_grounded_box_boundary_and_electrode_values(self):
        result = electrode_pair_in_grounded_box(n=51)
        a = result.potential_v
        self.assertTrue(np.all(a[0,:] == 0))
        self.assertTrue(np.all(a[-1,:] == 0))
        self.assertTrue(np.all(a[:,0] == 0))
        self.assertTrue(np.all(a[:,-1] == 0))
        self.assertAlmostEqual(np.max(a), 500)
        self.assertAlmostEqual(np.min(a), -500)

    def test_invalid_outer_boundary_or_geometry_rejected(self):
        mask = np.zeros((5,5), dtype=bool)
        with self.assertRaises(ValueError):
            solve_dirichlet(mask, np.zeros((5,5)), 0.01)
        with self.assertRaises(ValueError):
            electrode_pair_in_grounded_box(left_center_x_m=0, right_center_x_m=0)
        with self.assertRaises(ValueError):
            electrode_pair_in_grounded_box(left_center_x_m=-0.02)


if __name__ == '__main__':
    unittest.main()
