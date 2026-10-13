import json
from pathlib import Path
import unittest

import numpy as np

from electrostatics_baseline import (
    EPSILON_0_F_PER_M,
    coaxial_cylinder_benchmark,
    electrode_pair_in_grounded_box,
    electrode_pair_mesh_study,
    evaluate_conductor_surface_interface,
    parallel_plate_benchmark,
    solve_dirichlet,
    verify_plate_force_virtual_work,
)
from examples.electrostatics_demo import display_field_data, render


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

    def test_parallel_plate_net_force_is_computed_sum_of_opposing_reactions(self):
        """F3b regression: verify net force is a non-tautological sum of signed forces."""
        result = parallel_plate_benchmark(500.0, 0.002, 0.0005)
        self.assertGreater(result.force_on_positive_plate_n, 0.0)
        self.assertLess(result.force_on_negative_plate_n, 0.0)
        computed_sum = result.force_on_positive_plate_n + result.force_on_negative_plate_n
        self.assertEqual(result.net_pair_force_n, computed_sum)
        self.assertAlmostEqual(result.net_pair_force_n, 0.0, places=15)

    def test_parallel_plate_virtual_work_independent_crosscheck(self):
        """F3b regression: verify plate attraction independently via energy derivatives."""
        vw = verify_plate_force_virtual_work(1000.0, 0.001, 0.0001)
        expected = vw['expected_magnitude_n']
        self.assertAlmostEqual(vw['virtual_work_fixed_v_n'] / expected, 1.0, places=5)
        self.assertAlmostEqual(vw['virtual_work_fixed_q_n'] / expected, 1.0, places=5)
        self.assertLess(vw['signed_f_gap_fixed_v_n'], 0.0)
        self.assertLess(vw['signed_f_gap_fixed_q_n'], 0.0)

    def test_force_scales_with_voltage_squared_and_gap_inverse_squared(self):
        a = parallel_plate_benchmark(100, 0.002, 1e-4)
        self.assertAlmostEqual(parallel_plate_benchmark(200, 0.002, 1e-4).pressure_pa / a.pressure_pa, 4)
        self.assertAlmostEqual(parallel_plate_benchmark(100, 0.004, 1e-4).pressure_pa / a.pressure_pa, 0.25)
        self.assertAlmostEqual(parallel_plate_benchmark(-100, 0.002, 1e-4).pressure_pa, a.pressure_pa)

    def test_invalid_inputs_rejected(self):
        for bad in (0, -0.1, np.inf, np.nan):
            with self.assertRaises(ValueError):
                parallel_plate_benchmark(100, bad, 0.01)
        with self.assertRaises(ValueError):
            parallel_plate_benchmark(100, 0.01, 0)


class LaplaceTests(unittest.TestCase):
    def test_linear_potential_is_exact_discrete_harmonic_solution(self):
        n = 21
        x, y = np.meshgrid(np.linspace(-1, 1, n), np.linspace(-1, 1, n), indexing='ij')
        expected = x + 2 * y
        mask = np.zeros((n, n), dtype=bool)
        mask[0, :] = mask[-1, :] = True
        mask[:, 0] = mask[:, -1] = True
        result = solve_dirichlet(mask, expected, 0.1)
        self.assertLess(np.max(np.abs(result.potential_v - expected)), 1e-11)
        self.assertLess(result.max_discrete_residual_v, 1e-11)
        # Vacuum interior cells match analytic gradient exactly
        self.assertLess(np.max(np.abs(result.ex_v_per_m[result.vacuum_mask] + 1)), 1e-9)
        self.assertLess(np.max(np.abs(result.ey_v_per_m[result.vacuum_mask] + 2)), 1e-9)
        # Fixed outer boundary nodes have undefined (NaN) physical vacuum E
        self.assertTrue(np.all(np.isnan(result.ex_v_per_m[result.boundary_mask])))
        self.assertTrue(np.all(np.isnan(result.ey_v_per_m[result.boundary_mask])))

    def test_symmetric_pair_has_antisymmetric_potential(self):
        result = electrode_pair_in_grounded_box(n=61)
        self.assertLess(np.max(np.abs(result.potential_v + result.potential_v[::-1, :])), 1e-8)
        self.assertLess(result.max_discrete_residual_v, 1e-8)
        self.assertTrue(np.all(np.isfinite(result.ex_v_per_m[result.vacuum_mask])))
        self.assertTrue(np.all(np.isfinite(result.ey_v_per_m[result.vacuum_mask])))

    def test_grounded_box_boundary_and_electrode_values(self):
        result = electrode_pair_in_grounded_box(n=51)
        a = result.potential_v
        self.assertTrue(np.all(a[0, :] == 0))
        self.assertTrue(np.all(a[-1, :] == 0))
        self.assertTrue(np.all(a[:, 0] == 0))
        self.assertTrue(np.all(a[:, -1] == 0))
        self.assertAlmostEqual(np.max(a), 500)
        self.assertAlmostEqual(np.min(a), -500)

    def test_invalid_outer_boundary_or_geometry_rejected(self):
        mask = np.zeros((5, 5), dtype=bool)
        with self.assertRaises(ValueError):
            solve_dirichlet(mask, np.zeros((5, 5)), 0.01)
        with self.assertRaises(ValueError):
            electrode_pair_in_grounded_box(left_center_x_m=0, right_center_x_m=0)
        with self.assertRaises(ValueError):
            electrode_pair_in_grounded_box(left_center_x_m=-0.02)

    def test_conductor_cells_have_no_exposed_physical_field(self):
        """F1 regression: fail if physical vacuum E includes non-vacuum cells as finite values."""
        sol = electrode_pair_in_grounded_box(n=101)
        # Verify physical vacuum fields are strictly non-finite (NaN) inside conductors and boundary
        self.assertFalse(np.any(np.isfinite(sol.ex_v_per_m[sol.conductor_mask])))
        self.assertFalse(np.any(np.isfinite(sol.ey_v_per_m[sol.conductor_mask])))
        self.assertFalse(np.any(np.isfinite(sol.ex_v_per_m[sol.boundary_mask])))
        self.assertFalse(np.any(np.isfinite(sol.ey_v_per_m[sol.boundary_mask])))

        # Verify vacuum cells are all finite
        self.assertTrue(np.all(np.isfinite(sol.ex_v_per_m[sol.vacuum_mask])))
        self.assertTrue(np.all(np.isfinite(sol.ey_v_per_m[sol.vacuum_mask])))

        # Check raw gradient had nonzero interface artifact on conductor voxels (~85.6 kV/m)
        raw_mag = np.hypot(sol.raw_gradient_x_v_per_m, sol.raw_gradient_y_v_per_m)
        max_cond_raw = float(np.max(raw_mag[sol.conductor_mask]))
        self.assertGreater(max_cond_raw, 70000.0)
        self.assertLess(max_cond_raw, 100000.0)

    def test_conductor_surface_interface_evaluation(self):
        """F1 regression: check one-sided interface handling and electrostatic traction units."""
        sol = electrode_pair_in_grounded_box(n=101)
        interface_data = evaluate_conductor_surface_interface(sol)
        self.assertGreater(interface_data['interface_vacuum_node_count'], 0)
        self.assertGreater(interface_data['max_interface_field_v_per_m'], 100000.0)
        self.assertGreater(interface_data['max_traction_pa'], 0.0)

    def test_visualization_masks_electrode_and_grounded_boundary_fields(self):
        solution = electrode_pair_in_grounded_box(n=41)
        magnitude, unit_ex, unit_ey = display_field_data(solution)
        for result in (magnitude, unit_ex, unit_ey):
            self.assertTrue(np.all(np.ma.getmaskarray(result)[solution.fixed_mask]))
            self.assertTrue(np.all(np.isfinite(result.compressed())))
        direction_norm = np.hypot(unit_ex.filled(0), unit_ey.filled(0))
        self.assertLessEqual(float(np.max(direction_norm)), 1.000000000001)
        self.assertTrue(np.all(direction_norm[solution.fixed_mask] == 0))


class ConvergenceAndBenchmarkTests(unittest.TestCase):
    def test_coaxial_benchmark_error_decreases_with_mesh_refinement(self):
        """F2 regression: automated check that field error decreases with refinement for benchmark."""
        benchmarks = coaxial_cylinder_benchmark(n_list=(41, 81, 161), probe_r_m=0.010)
        self.assertEqual(len(benchmarks), 3)

        # Potential error decreases monotonically with refinement
        self.assertGreater(benchmarks[0].potential_error_v, benchmarks[1].potential_error_v)
        self.assertGreater(benchmarks[1].potential_error_v, benchmarks[2].potential_error_v)

        # Electric field error decreases monotonically with refinement
        self.assertGreater(benchmarks[0].field_error_v_per_m, benchmarks[1].field_error_v_per_m)
        self.assertGreater(benchmarks[1].field_error_v_per_m, benchmarks[2].field_error_v_per_m)

        # Final error at n=161 is under 3% of analytic field
        rel_field_error = benchmarks[2].field_error_v_per_m / benchmarks[2].analytic_field_er_v_per_m
        self.assertLess(rel_field_error, 0.03)

    def test_electrode_pair_mesh_study_probe_stability_and_peak_sensitivity(self):
        """F2 regression: probe field converges while peak vacuum field exhibits grid sensitivity."""
        study = electrode_pair_mesh_study(n_list=(41, 81, 101, 161), probe_xy_m=(0.0, 0.0))
        self.assertEqual(len(study), 4)

        # Center probe field Ex(0,0) changes by less than 3% between n=41 and n=161
        ex_vals = [r.probe_ex_v_per_m for r in study]
        probe_drift = (max(ex_vals) - min(ex_vals)) / min(ex_vals)
        self.assertLess(probe_drift, 0.03)

        # Peak vacuum |E| on staircase boundary varies by >30% (unconverged diagnostic numbers)
        max_e_vals = [r.max_vacuum_e_v_per_m for r in study]
        peak_variation = (max(max_e_vals) - min(max_e_vals)) / min(max_e_vals)
        self.assertGreater(peak_variation, 0.30)

        # Antisymmetry of potential remains numerically clean across grids
        for r in study:
            self.assertLess(r.potential_antisymmetry_error_v, 1e-10)


class ManifestAndContractTests(unittest.TestCase):
    def test_manifest_generation_and_schema_conformance(self):
        """F5 regression: CI and demo produce paired JSON manifest with exact provenance."""
        png_path, json_path = render(
            output_png='test_electrostatics_baseline.png',
            output_json='test_electrostatics_manifest.json',
        )
        self.assertTrue(png_path.exists())
        self.assertTrue(json_path.exists())

        with open(json_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        self.assertEqual(manifest['schema_version'], '1.0.0')
        self.assertIn('git_commit', manifest)
        self.assertIn('environment', manifest)
        self.assertIn('packages', manifest['environment'])
        self.assertEqual(manifest['environment']['packages']['numpy'], np.__version__)

        case1 = manifest['cases']['case_1_grounded_box_2d']
        self.assertEqual(case1['validation_status'], 'ILLUSTRATIVE / NON-CONVERGED')
        self.assertIn('mesh_study_probe_midpoint', case1)
        self.assertIn('coaxial_analytic_benchmark', case1)

        case2 = manifest['cases']['case_2_parallel_plate_1d']
        self.assertEqual(case2['validation_status'], 'ANALYTIC BENCHMARK')
        self.assertEqual(case2['results']['net_pair_force_n'], 0.0)

        # Clean up temporary test files
        png_path.unlink(missing_ok=True)
        json_path.unlink(missing_ok=True)

    def test_patent_model_contract_audits_contested_derivations(self):
        """F4 regression: EXODUS_MODEL_CONTRACT.md must document Eq.(4) and Eq.(11) proof obligations."""
        contract_path = Path(__file__).resolve().parents[1] / 'docs' / 'EXODUS_MODEL_CONTRACT.md'
        self.assertTrue(contract_path.exists())
        text = contract_path.read_text(encoding='utf-8')

        self.assertIn('Derivation ledger: US11511891B2 (Eq. 4–11 audit)', text)
        self.assertIn('Eq. (4) assertion of d(Ut) = 0 from stationary action', text)
        self.assertIn('Eq. (11) net force expression', text)
        self.assertIn('Model H0: conventional electrodynamics', text)
        self.assertIn('Model H1: precisely cited patent proposition', text)


if __name__ == '__main__':
    unittest.main()
