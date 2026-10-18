import json
import os
from pathlib import Path
import unittest

import numpy as np

from electrostatics_baseline import (
    EPSILON_0_F_PER_M,
    ElectrodeConfig,
    FieldSolution,
    GroundedBoxConfig,
    MeshRefinementResult,
    ProbeConvergenceAssessment,
    assess_probe_convergence,
    check_configuration_symmetries,
    check_discrete_symmetries,
    coaxial_cylinder_benchmark,
    electrode_pair_in_grounded_box,
    electrode_pair_mesh_study,
    evaluate_conductor_surface_interface,
    format_panel_a_title,
    format_voltage_title,
    parallel_plate_benchmark,
    solve_dirichlet,
    verify_plate_force_virtual_work,
)
from examples.electrostatics_demo import display_field_data, get_git_provenance, render


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

    def test_conductor_surface_interface_face_normals(self):
        """R2-F1 regression: verify face-normal interface traction evaluation."""
        sol = electrode_pair_in_grounded_box(n=101)
        res = evaluate_conductor_surface_interface(sol)
        self.assertGreater(res.face_count, 0)
        self.assertGreater(res.max_normal_field_v_per_m, 100000.0)
        self.assertGreater(res.max_traction_pa, 0.0)
        self.assertIn('Diagnostic one-sided surface-normal', res.diagnostic_note)

    def test_conductor_surface_interface_harmonic_xy_counterexample(self):
        """R2-F1 regression: counterexample V(x,y)=x*y next to grounded plane x=0.

        Exact surface normal field: E_n(0, y) = -y.
        Exact surface traction: T_n = 0.5 * epsilon_0 * y^2.
        At sample (x=h, y=h), centered gradient |E|^2 = 2*h^2 (2x overestimation),
        whereas our face-normal evaluation correctly evaluates E_n = -h and T_n = 0.5 * epsilon_0 * h^2.
        """
        n = 21
        h = 0.001
        coords = (np.arange(n) - 10) * h  # -10h to +10h, center index 10 corresponds to x=0
        x, y = np.meshgrid(coords, coords, indexing='ij')
        exact_pot = x * y

        # Conductor occupies x <= 0 (indices 1 to 10 for interior y)
        conductor = np.zeros((n, n), dtype=bool)
        conductor[1:11, 1:-1] = True
        exact_pot[conductor] = 0.0

        # Boundary is outer box edges (on left edge where x <= 0, potential is 0)
        boundary = np.zeros((n, n), dtype=bool)
        boundary[0, :] = boundary[-1, :] = boundary[:, 0] = boundary[:, -1] = True
        exact_pot[0, :] = 0.0

        fixed = conductor | boundary
        sol = solve_dirichlet(fixed, exact_pot, h, conductor_mask=conductor, boundary_mask=boundary)

        res = evaluate_conductor_surface_interface(sol)
        self.assertGreater(res.face_count, 0)

        # Expected traction at y = h: 0.5 * epsilon_0 * h^2
        expected_traction_at_h = 0.5 * EPSILON_0_F_PER_M * h**2

        # East faces: conductor at (i=10, j) adjacent to vacuum at (i=11, j) with normal (+1, 0)
        east_mask = (res.face_normals[:, 0] == 1.0)
        self.assertTrue(np.any(east_mask))

        # Find face where normal field magnitude is h (at y = h)
        found_match = False
        for e_n, t_n in zip(res.normal_fields_v_per_m[east_mask], res.tractions_pa[east_mask]):
            if np.isclose(abs(e_n), h, atol=1e-10):
                found_match = True
                self.assertAlmostEqual(t_n / expected_traction_at_h, 1.0, places=6)
                # Verify that it is NOT 2x expected (which centered |E|^2 gave)
                self.assertNotAlmostEqual(t_n / expected_traction_at_h, 2.0, places=3)
                break
        self.assertTrue(found_match, "Did not find east interface face at y = h")

    def test_conductor_surface_interface_uniform_field(self):
        """R2-F1 regression: uniform 1D field between parallel plates matches analytic pressure."""
        n = 21
        h = 0.001
        L = (n - 1) * h
        v0 = 100.0
        coords = np.arange(n) * h
        x, y = np.meshgrid(coords, coords, indexing='ij')

        pot = v0 * (1.0 - x / L)

        # Interior plate at column i = 5, spanning rows j = 3 to 17
        conductor = np.zeros((n, n), dtype=bool)
        conductor[5, 3:18] = True
        pot[conductor] = v0 * (1.0 - coords[5] / L)

        boundary = np.zeros((n, n), dtype=bool)
        boundary[0, :] = boundary[-1, :] = boundary[:, 0] = boundary[:, -1] = True

        fixed = conductor | boundary
        sol = solve_dirichlet(fixed, pot, h, conductor_mask=conductor, boundary_mask=boundary)

        res = evaluate_conductor_surface_interface(sol)
        expected_e_n = v0 / L
        expected_traction = 0.5 * EPSILON_0_F_PER_M * expected_e_n**2

        # Check east faces
        east_mask = (res.face_normals[:, 0] == 1.0)
        self.assertTrue(np.any(east_mask))
        for t in res.tractions_pa[east_mask]:
            self.assertAlmostEqual(t, expected_traction, places=10)

    def test_mask_validation_rejects_inconsistent_or_overlapping_masks(self):
        """R2-F4 regression: solve_dirichlet must validate disjointness, partition, and outer boundary."""
        n = 9
        mask = np.zeros((n, n), dtype=bool)
        mask[0, :] = mask[-1, :] = mask[:, 0] = mask[:, -1] = True
        pot = np.zeros((n, n))

        # 1. Boundary mask wrong shape
        bad_shape = np.zeros((5, 5), dtype=bool)
        with self.assertRaises(ValueError):
            solve_dirichlet(mask, pot, 0.01, boundary_mask=bad_shape)

        # 2. Conductor mask wrong shape
        with self.assertRaises(ValueError):
            solve_dirichlet(mask, pot, 0.01, conductor_mask=bad_shape)

        # 3. Overlapping conductor and boundary masks
        overlap_conductor = np.zeros((n, n), dtype=bool)
        overlap_conductor[0, 0] = True  # Overlaps with boundary at (0, 0)
        overlap_boundary = mask.copy()
        with self.assertRaises(ValueError):
            solve_dirichlet(mask, pot, 0.01, conductor_mask=overlap_conductor, boundary_mask=overlap_boundary)

        # 4. Incomplete partition: union does not equal fixed_mask
        partial_boundary = mask.copy()
        partial_conductor = np.zeros((n, n), dtype=bool)
        fixed_with_interior = mask.copy()
        fixed_with_interior[3, 3] = True  # Fixed node not in conductor or boundary
        with self.assertRaises(ValueError):
            solve_dirichlet(fixed_with_interior, pot, 0.01, conductor_mask=partial_conductor, boundary_mask=partial_boundary)

        # 5. Boundary mask missing an outer edge
        broken_boundary = mask.copy()
        broken_boundary[0, :] = False
        with self.assertRaises(ValueError):
            solve_dirichlet(mask, pot, 0.01, boundary_mask=broken_boundary)

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

    def test_symmetry_preconditions_and_central_inversion(self):
        """R4-F1 regression: verify symmetry preconditions and separate central-inversion diagnostic."""
        # 1. Symmetric baseline: both x-reflection and central-inversion hold
        cfg_sym = GroundedBoxConfig(
            n=41,
            box_width_m=0.04,
            left_electrode=ElectrodeConfig(center_x_m=-0.008, center_y_m=0.0, radius_m=0.003, voltage_v=500.0),
            right_electrode=ElectrodeConfig(center_x_m=0.008, center_y_m=0.0, radius_m=0.003, voltage_v=-500.0),
        )
        sym_info_sym = check_configuration_symmetries(cfg_sym)
        self.assertTrue(sym_info_sym['has_x_reflection_antisymmetry'])
        self.assertTrue(sym_info_sym['has_central_inversion_antisymmetry'])
        res_sym = electrode_pair_mesh_study(n_list=(31,), config=cfg_sym)[0]
        self.assertIsNotNone(res_sym.potential_antisymmetry_error_v)
        self.assertLess(res_sym.potential_antisymmetry_error_v, 1e-10)
        self.assertIsNotNone(res_sym.potential_central_inversion_error_v)
        self.assertLess(res_sym.potential_central_inversion_error_v, 1e-10)
        self.assertEqual(res_sym.symmetry_status, 'X_REFLECTION_AND_CENTRAL_INVERSION_ANTISYMMETRIC')

        # 2. Vertically offset opposite-parity pair: x-reflection fails, central-inversion holds
        cfg_offset = GroundedBoxConfig(
            n=41,
            box_width_m=0.04,
            left_electrode=ElectrodeConfig(center_x_m=-0.008, center_y_m=0.003, radius_m=0.003, voltage_v=500.0),
            right_electrode=ElectrodeConfig(center_x_m=0.008, center_y_m=-0.003, radius_m=0.003, voltage_v=-500.0),
        )
        sym_info_offset = check_configuration_symmetries(cfg_offset)
        self.assertFalse(sym_info_offset['has_x_reflection_antisymmetry'])
        self.assertTrue(sym_info_offset['has_central_inversion_antisymmetry'])
        res_offset = electrode_pair_mesh_study(n_list=(31,), config=cfg_offset)[0]
        self.assertIsNone(res_offset.potential_antisymmetry_error_v)
        self.assertIsNotNone(res_offset.potential_central_inversion_error_v)
        self.assertLess(res_offset.potential_central_inversion_error_v, 1e-10)
        self.assertEqual(res_offset.symmetry_status, 'CENTRAL_INVERSION_ANTISYMMETRIC')

        # 3. Vertically shifted same-direction: both fail central inversion, but x-reflection holds
        cfg_shift_same = GroundedBoxConfig(
            n=41,
            box_width_m=0.04,
            left_electrode=ElectrodeConfig(center_x_m=-0.008, center_y_m=0.003, radius_m=0.003, voltage_v=500.0),
            right_electrode=ElectrodeConfig(center_x_m=0.008, center_y_m=0.003, radius_m=0.003, voltage_v=-500.0),
        )
        sym_info_shift = check_configuration_symmetries(cfg_shift_same)
        self.assertTrue(sym_info_shift['has_x_reflection_antisymmetry'])
        self.assertFalse(sym_info_shift['has_central_inversion_antisymmetry'])
        res_shift = electrode_pair_mesh_study(n_list=(31,), config=cfg_shift_same)[0]
        self.assertIsNotNone(res_shift.potential_antisymmetry_error_v)
        self.assertLess(res_shift.potential_antisymmetry_error_v, 1e-10)
        self.assertIsNone(res_shift.potential_central_inversion_error_v)
        self.assertEqual(res_shift.symmetry_status, 'X_REFLECTION_ANTISYMMETRIC')

        # 4. Asymmetric voltages: neither holds
        cfg_asym = GroundedBoxConfig(
            n=41,
            box_width_m=0.04,
            left_electrode=ElectrodeConfig(center_x_m=-0.008, center_y_m=0.0, radius_m=0.003, voltage_v=800.0),
            right_electrode=ElectrodeConfig(center_x_m=0.008, center_y_m=0.0, radius_m=0.003, voltage_v=-350.0),
        )
        sym_info_asym = check_configuration_symmetries(cfg_asym)
        self.assertFalse(sym_info_asym['has_x_reflection_antisymmetry'])
        self.assertFalse(sym_info_asym['has_central_inversion_antisymmetry'])
        res_asym = electrode_pair_mesh_study(n_list=(31,), config=cfg_asym)[0]
        self.assertIsNone(res_asym.potential_antisymmetry_error_v)
        self.assertIsNone(res_asym.potential_central_inversion_error_v)
        self.assertEqual(res_asym.symmetry_status, 'N/A (asymmetric geometry or potentials)')

    def test_mesh_study_probe_inside_conductor_and_strict_json(self):
        """R4-F2 regression: probe inside conductor records None/null and produces valid RFC 8259 JSON."""
        # Electrode centered at (0, 0) covering the probe point (0, 0)
        cfg_probe_in_cond = GroundedBoxConfig(
            n=41,
            box_width_m=0.04,
            left_electrode=ElectrodeConfig(center_x_m=0.0, center_y_m=0.0, radius_m=0.005, voltage_v=500.0),
            right_electrode=ElectrodeConfig(center_x_m=0.015, center_y_m=0.0, radius_m=0.002, voltage_v=-500.0),
        )

        # 1. require_vacuum_probe=True must raise ValueError
        with self.assertRaises(ValueError):
            electrode_pair_mesh_study(
                n_list=(31,),
                probe_xy_m=(0.0, 0.0),
                config=cfg_probe_in_cond,
                require_vacuum_probe=True,
            )

        # 2. Default require_vacuum_probe=False records probe_in_vacuum=False and probe fields as None
        study = electrode_pair_mesh_study(
            n_list=(31,),
            probe_xy_m=(0.0, 0.0),
            config=cfg_probe_in_cond,
            require_vacuum_probe=False,
        )
        self.assertEqual(len(study), 1)
        r = study[0]
        self.assertFalse(r.probe_in_vacuum)
        self.assertIsNone(r.probe_ex_v_per_m)
        self.assertIsNone(r.probe_ey_v_per_m)
        self.assertIn('NON_VACUUM', r.probe_status)

        # 3. Render and manifest generation: must not emit NaN tokens, and must parse under strict RFC 8259 parser
        png_path, json_path = render(
            output_png='test_probe_cond_baseline.png',
            output_json='test_probe_cond_manifest.json',
            config_2d=cfg_probe_in_cond,
        )
        self.assertTrue(json_path.exists())

        raw_json = json_path.read_text(encoding='utf-8')
        # Standard RFC 8259 disallows bare NaN or Infinity
        self.assertNotIn(': NaN', raw_json)
        self.assertNotIn(': Infinity', raw_json)
        self.assertNotIn(': -Infinity', raw_json)

        # Strict JSON parse verifying no NaN constants were accepted
        def no_constants(val):
            raise ValueError(f"Non-compliant JSON token encountered: {val}")

        manifest = json.loads(raw_json, parse_constant=no_constants)
        case1 = manifest['cases']['case_1_grounded_box_2d']
        self.assertIn('probe_convergence_assessment', case1)
        self.assertIn('inside conductor', case1['probe_convergence_assessment'])

        probe_entry = case1['mesh_study_probe_midpoint'][0]
        self.assertFalse(probe_entry['probe_in_vacuum'])
        self.assertIsNone(probe_entry['probe_ex_v_per_m'])
        self.assertIsNone(probe_entry['probe_ey_v_per_m'])
        self.assertIn('NON_VACUUM', probe_entry['probe_status'])

        png_path.unlink(missing_ok=True)
        json_path.unlink(missing_ok=True)


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

        self.assertIn(manifest['schema_version'], ('1.0.0', '1.1.0', '1.2.0'))
        self.assertIn('git_commit', manifest)
        self.assertIn('tested_checkout_sha', manifest)
        self.assertIn('provenance', manifest)
        self.assertIn('pr_source_head_sha', manifest['provenance'])
        self.assertIn('tested_checkout_sha', manifest['provenance'])
        self.assertIn('environment', manifest)
        self.assertIn('packages', manifest['environment'])
        self.assertEqual(manifest['environment']['packages']['numpy'], np.__version__)

        case1 = manifest['cases']['case_1_grounded_box_2d']
        self.assertEqual(case1['validation_status'], 'ILLUSTRATIVE / NON-CONVERGED')
        self.assertIn('mesh_study_probe_midpoint', case1)
        self.assertIn('coaxial_analytic_benchmark', case1)
        self.assertIn('probe_convergence_assessment', case1)

        row0 = case1['mesh_study_probe_midpoint'][0]
        self.assertTrue(row0['probe_in_vacuum'])
        self.assertEqual(row0['probe_status'], 'VALID_VACUUM')
        self.assertIn('potential_central_inversion_error_v', row0)
        self.assertIn('symmetry_status', row0)

        case2 = manifest['cases']['case_2_parallel_plate_1d']
        self.assertEqual(case2['validation_status'], 'ANALYTIC BENCHMARK')
        self.assertEqual(case2['results']['net_pair_force_n'], 0.0)

        # Clean up temporary test files
        png_path.unlink(missing_ok=True)
        json_path.unlink(missing_ok=True)

    def test_manifest_geometry_derived_from_typed_config_including_nondefault(self):
        """R2-F3 regression: manifest geometry must dynamically reflect typed config, including non-default runs."""
        custom_cfg = GroundedBoxConfig(
            n=41,
            box_width_m=0.06,
            left_electrode=ElectrodeConfig(center_x_m=-0.012, center_y_m=0.0, radius_m=0.004, voltage_v=750.0),
            right_electrode=ElectrodeConfig(center_x_m=0.012, center_y_m=0.0, radius_m=0.004, voltage_v=-750.0),
        )
        png_path, json_path = render(
            output_png='test_custom_baseline.png',
            output_json='test_custom_manifest.json',
            config_2d=custom_cfg,
        )
        with open(json_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        geom = manifest['cases']['case_1_grounded_box_2d']['geometry']
        self.assertAlmostEqual(geom['enclosure_width_m'], 0.06)
        self.assertAlmostEqual(geom['left_electrode']['voltage_v'], 750.0)
        self.assertAlmostEqual(geom['left_electrode']['radius_m'], 0.004)
        self.assertAlmostEqual(geom['right_electrode']['voltage_v'], -750.0)

        png_path.unlink(missing_ok=True)
        json_path.unlink(missing_ok=True)

    def test_electrode_y_position_affects_mask_and_manifest(self):
        """R3-F1 regression: verify nonzero center_y_m physically shifts conductor masks and is recorded in manifest."""
        n = 81
        box_width = 0.04
        y_offset_left = 0.005   # +5 mm
        y_offset_right = -0.005 # -5 mm

        cfg = GroundedBoxConfig(
            n=n,
            box_width_m=box_width,
            left_electrode=ElectrodeConfig(center_x_m=-0.008, center_y_m=y_offset_left, radius_m=0.003, voltage_v=500.0),
            right_electrode=ElectrodeConfig(center_x_m=0.008, center_y_m=y_offset_right, radius_m=0.003, voltage_v=-500.0),
        )
        sol = electrode_pair_in_grounded_box(config=cfg)

        coords = np.linspace(-box_width / 2, box_width / 2, n)
        x, y = np.meshgrid(coords, coords, indexing='ij')

        # Check left electrode centroid
        left_mask = sol.conductor_mask & (sol.potential_v > 0)
        self.assertTrue(np.any(left_mask))
        left_mean_y = float(np.mean(y[left_mask]))
        self.assertAlmostEqual(left_mean_y, y_offset_left, delta=sol.grid_spacing_m)

        # Check right electrode centroid
        right_mask = sol.conductor_mask & (sol.potential_v < 0)
        self.assertTrue(np.any(right_mask))
        right_mean_y = float(np.mean(y[right_mask]))
        self.assertAlmostEqual(right_mean_y, y_offset_right, delta=sol.grid_spacing_m)

        # Non-finite y inputs must be rejected
        with self.assertRaises(ValueError):
            ElectrodeConfig(center_x_m=0.0, center_y_m=np.nan, radius_m=0.003, voltage_v=100.0)
        with self.assertRaises(ValueError):
            ElectrodeConfig(center_x_m=0.0, center_y_m=np.inf, radius_m=0.003, voltage_v=100.0)
        with self.assertRaises(ValueError):
            electrode_pair_in_grounded_box(left_center_y_m=np.nan)

        # Verify manifest recording
        png_path, json_path = render(
            output_png='test_y_offset_baseline.png',
            output_json='test_y_offset_manifest.json',
            config_2d=cfg,
        )
        with open(json_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        geom = manifest['cases']['case_1_grounded_box_2d']['geometry']
        self.assertAlmostEqual(geom['left_electrode']['center_y_m'], y_offset_left)
        self.assertAlmostEqual(geom['right_electrode']['center_y_m'], y_offset_right)

        png_path.unlink(missing_ok=True)
        json_path.unlink(missing_ok=True)

    def test_mesh_study_uses_custom_configuration(self):
        """R3-F2 regression: mesh study must use passed config rather than silently falling back to defaults."""
        custom_cfg = GroundedBoxConfig(
            n=41,
            box_width_m=0.05,
            left_electrode=ElectrodeConfig(center_x_m=-0.010, center_y_m=0.002, radius_m=0.004, voltage_v=800.0),
            right_electrode=ElectrodeConfig(center_x_m=0.010, center_y_m=-0.002, radius_m=0.004, voltage_v=-800.0),
        )

        study = electrode_pair_mesh_study(n_list=(31, 51), config=custom_cfg)
        self.assertEqual(len(study), 2)
        # Check that grid spacings match custom box width 0.05
        self.assertAlmostEqual(study[0].grid_spacing_m, 0.05 / 30)
        self.assertAlmostEqual(study[1].grid_spacing_m, 0.05 / 50)

        # R4-F1: custom_cfg has y_left = +0.002, y_right = -0.002.
        # This breaks x-reflection antisymmetry but preserves central inversion.
        self.assertIsNone(study[0].potential_antisymmetry_error_v)
        self.assertIsNotNone(study[0].potential_central_inversion_error_v)
        self.assertLess(study[0].potential_central_inversion_error_v, 1e-10)
        self.assertEqual(study[0].symmetry_status, 'CENTRAL_INVERSION_ANTISYMMETRIC')

        # Check render serializes custom mesh study geometry in manifest
        png_path, json_path = render(
            output_png='test_custom_study_baseline.png',
            output_json='test_custom_study_manifest.json',
            config_2d=custom_cfg,
        )
        with open(json_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        case1 = manifest['cases']['case_1_grounded_box_2d']
        self.assertIn('mesh_study_geometry', case1)
        study_geom = case1['mesh_study_geometry']
        self.assertAlmostEqual(study_geom['enclosure_width_m'], 0.05)
        self.assertAlmostEqual(study_geom['left_electrode']['voltage_v'], 800.0)
        self.assertAlmostEqual(study_geom['left_electrode']['center_y_m'], 0.002)
        self.assertAlmostEqual(study_geom['right_electrode']['voltage_v'], -800.0)
        self.assertAlmostEqual(study_geom['right_electrode']['center_y_m'], -0.002)

        row0 = case1['mesh_study_probe_midpoint'][0]
        self.assertIsNone(row0['potential_antisymmetry_error_v'])
        self.assertIsNotNone(row0['potential_central_inversion_error_v'])
        self.assertEqual(row0['symmetry_status'], 'CENTRAL_INVERSION_ANTISYMMETRIC')

        png_path.unlink(missing_ok=True)
        json_path.unlink(missing_ok=True)

    def test_manifest_provenance_distinguishes_source_head_from_tested_merge(self):
        """R3-F3 regression: verify manifest provenance records both PR source HEAD SHA and tested checkout SHA."""
        # 1. Live git provenance check
        prov_live = get_git_provenance()
        self.assertIn('pr_source_head_sha', prov_live)
        self.assertIn('tested_checkout_sha', prov_live)
        self.assertIn('pr_base_sha', prov_live)
        self.assertIn('is_synthetic_pr_merge', prov_live)

        # 2. Simulated GitHub Actions PR environment
        mock_source_sha = 'a' * 40
        mock_base_sha = 'b' * 40
        old_env = {
            'PR_SOURCE_HEAD_SHA': os.environ.get('PR_SOURCE_HEAD_SHA'),
            'PR_BASE_SHA': os.environ.get('PR_BASE_SHA'),
            'GITHUB_EVENT_NAME': os.environ.get('GITHUB_EVENT_NAME'),
        }
        try:
            os.environ['PR_SOURCE_HEAD_SHA'] = mock_source_sha
            os.environ['PR_BASE_SHA'] = mock_base_sha
            os.environ['GITHUB_EVENT_NAME'] = 'pull_request'

            prov_sim = get_git_provenance()
            self.assertEqual(prov_sim['pr_source_head_sha'], mock_source_sha)
            self.assertEqual(prov_sim['pr_base_sha'], mock_base_sha)
            self.assertEqual(prov_sim['ci_event_name'], 'pull_request')
            # If tested_checkout_sha is actual git repo checkout, it won't equal 'a'*40, so synthetic merge is True
            self.assertTrue(prov_sim['is_synthetic_pr_merge'])

            png_path, json_path = render(
                output_png='test_prov_baseline.png',
                output_json='test_prov_manifest.json',
            )
            with open(json_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            self.assertEqual(manifest['git_commit'], mock_source_sha)
            self.assertEqual(manifest['provenance']['pr_source_head_sha'], mock_source_sha)
            self.assertEqual(manifest['provenance']['pr_base_sha'], mock_base_sha)
            self.assertEqual(manifest['provenance']['ci_event_name'], 'pull_request')
            self.assertTrue(manifest['provenance']['is_synthetic_pr_merge'])
            self.assertIn('provenance_note', manifest['provenance'])

            png_path.unlink(missing_ok=True)
            json_path.unlink(missing_ok=True)
        finally:
            for k, v in old_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

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

    def test_render_unequal_voltages_title_and_manifest(self):
        """R4-F3 / R5-F4 regression: verify asymmetric voltage configurations render with explicit titles and valid JSON."""
        cfg_asym = GroundedBoxConfig(
            n=41,
            box_width_m=0.04,
            left_electrode=ElectrodeConfig(center_x_m=-0.008, center_y_m=0.0, radius_m=0.003, voltage_v=800.0),
            right_electrode=ElectrodeConfig(center_x_m=0.008, center_y_m=0.0, radius_m=0.003, voltage_v=-350.0),
        )

        # R5-F4: Explicitly inspect Panel A title formatting
        expected_title = format_panel_a_title(cfg_asym)
        self.assertIn('V_left=+800 V, V_right=-350 V', expected_title)
        self.assertEqual(expected_title, 'A · Case 1: Grounded Box (V_left=+800 V, V_right=-350 V)\nDirichlet Potential (V)')

        png_path, json_path = render(
            output_png='test_asym_v_baseline.png',
            output_json='test_asym_v_manifest.json',
            config_2d=cfg_asym,
        )
        self.assertTrue(png_path.exists())
        self.assertTrue(json_path.exists())

        with open(json_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        geom = manifest['cases']['case_1_grounded_box_2d']['geometry']
        self.assertAlmostEqual(geom['left_electrode']['voltage_v'], 800.0)
        self.assertAlmostEqual(geom['right_electrode']['voltage_v'], -350.0)

        # Symmetry status in mesh study rows should be N/A
        mesh_study = manifest['cases']['case_1_grounded_box_2d']['mesh_study_probe_midpoint']
        for row in mesh_study:
            self.assertIsNone(row['potential_antisymmetry_error_v'])
            self.assertIsNone(row['potential_central_inversion_error_v'])
            self.assertIn('N/A', row['symmetry_status'])

        # R5-F2: verify probe convergence details recorded in manifest
        case1 = manifest['cases']['case_1_grounded_box_2d']
        self.assertIn('probe_convergence_details', case1)
        conv_details = case1['probe_convergence_details']
        self.assertIn('vacuum_status', conv_details)
        self.assertIn('convergence_status', conv_details)

        png_path.unlink(missing_ok=True)
        json_path.unlink(missing_ok=True)

    def test_r5_f1_exact_antisymmetry_and_near_threshold_geometry(self):
        """R5-F1 regression: np.isclose false assertions rejected; discrete parity verified exactly."""
        # 1. Voltage asymmetry: +500 V vs -499.997 V (0.003 V discrepancy)
        # np.isclose(-499.997, -500.0, rtol=1e-5, atol=1e-8) is True, but exact symmetry must be False!
        self.assertTrue(np.isclose(-499.997, -500.0, rtol=1e-5, atol=1e-8))

        cfg_approx = GroundedBoxConfig(
            n=41,
            box_width_m=0.04,
            left_electrode=ElectrodeConfig(center_x_m=-0.008, center_y_m=0.0, radius_m=0.003, voltage_v=500.0),
            right_electrode=ElectrodeConfig(center_x_m=0.008, center_y_m=0.0, radius_m=0.003, voltage_v=-499.997),
        )
        sym_approx = check_configuration_symmetries(cfg_approx)
        self.assertFalse(sym_approx['has_x_reflection_antisymmetry'])
        self.assertFalse(sym_approx['has_central_inversion_antisymmetry'])

        study_approx = electrode_pair_mesh_study(n_list=(31,), config=cfg_approx)
        self.assertEqual(len(study_approx), 1)
        r = study_approx[0]
        self.assertIsNone(r.potential_antisymmetry_error_v)
        self.assertIsNone(r.potential_central_inversion_error_v)
        self.assertEqual(r.symmetry_status, 'N/A (asymmetric geometry or potentials)')

        # 2. Near-threshold geometry: x_right = 0.0080001 m vs x_left = -0.008 m
        cfg_near_geom = GroundedBoxConfig(
            n=41,
            box_width_m=0.04,
            left_electrode=ElectrodeConfig(center_x_m=-0.008, center_y_m=0.0, radius_m=0.003, voltage_v=500.0),
            right_electrode=ElectrodeConfig(center_x_m=0.0080001, center_y_m=0.0, radius_m=0.003, voltage_v=-500.0),
        )
        sym_near = check_configuration_symmetries(cfg_near_geom)
        self.assertFalse(sym_near['has_x_reflection_antisymmetry'])
        self.assertFalse(sym_near['has_central_inversion_antisymmetry'])

        study_near = electrode_pair_mesh_study(n_list=(31,), config=cfg_near_geom)
        self.assertIsNone(study_near[0].potential_antisymmetry_error_v)
        self.assertIsNone(study_near[0].potential_central_inversion_error_v)
        self.assertEqual(study_near[0].symmetry_status, 'N/A (asymmetric geometry or potentials)')

        # 3. Discrete transformed fixed masks and potentials check
        cfg_exact = GroundedBoxConfig(
            n=41,
            box_width_m=0.04,
            left_electrode=ElectrodeConfig(center_x_m=-0.008, center_y_m=0.0, radius_m=0.003, voltage_v=500.0),
            right_electrode=ElectrodeConfig(center_x_m=0.008, center_y_m=0.0, radius_m=0.003, voltage_v=-500.0),
        )
        sol_exact = electrode_pair_in_grounded_box(config=cfg_exact)
        disc_sym = check_discrete_symmetries(sol_exact, cfg_exact)
        self.assertTrue(disc_sym['has_x_reflection_antisymmetry'])
        self.assertTrue(disc_sym['has_central_inversion_antisymmetry'])

    def test_r5_f2_probe_convergence_assessment_split_and_regressions(self):
        """R5-F2 regression: split vacuum validity from quantitative convergence with all requested regressions."""
        # 1. Insufficient resolutions: 1-row study
        res_1row = electrode_pair_mesh_study(n_list=(41,))
        eval_1row = assess_probe_convergence(res_1row, requested_probe_xy_m=(0.0, 0.0))
        self.assertEqual(eval_1row.vacuum_status, 'ALL_IN_VACUUM')
        self.assertEqual(eval_1row.convergence_status, 'NOT_ASSESSED')
        self.assertFalse(eval_1row.is_converged)
        self.assertIn('Insufficient mesh resolutions (1 row(s) provided)', eval_1row.assessment_summary)

        # 2. Wildly drifting but all-vacuum rows: must fail closed to INCONCLUSIVE
        drifting_rows = [
            MeshRefinementResult(
                n=41,
                grid_spacing_m=0.001,
                probe_x_m=0.0,
                probe_y_m=0.0,
                probe_potential_v=0.0,
                probe_ex_v_per_m=100.0,
                probe_ey_v_per_m=0.0,
                max_vacuum_e_v_per_m=200.0,
                max_conductor_raw_gradient_v_per_m=50.0,
                max_discrete_residual_v=1e-12,
                potential_antisymmetry_error_v=1e-12,
                probe_in_vacuum=True,
                probe_status='VALID_VACUUM',
                requested_probe_x_m=0.0,
                requested_probe_y_m=0.0,
            ),
            MeshRefinementResult(
                n=81,
                grid_spacing_m=0.0005,
                probe_x_m=0.0,
                probe_y_m=0.0,
                probe_potential_v=0.0,
                probe_ex_v_per_m=5000.0,
                probe_ey_v_per_m=0.0,
                max_vacuum_e_v_per_m=6000.0,
                max_conductor_raw_gradient_v_per_m=50.0,
                max_discrete_residual_v=1e-12,
                potential_antisymmetry_error_v=1e-12,
                probe_in_vacuum=True,
                probe_status='VALID_VACUUM',
                requested_probe_x_m=0.0,
                requested_probe_y_m=0.0,
            ),
            MeshRefinementResult(
                n=161,
                grid_spacing_m=0.00025,
                probe_x_m=0.0,
                probe_y_m=0.0,
                probe_potential_v=0.0,
                probe_ex_v_per_m=25000.0,
                probe_ey_v_per_m=0.0,
                max_vacuum_e_v_per_m=30000.0,
                max_conductor_raw_gradient_v_per_m=50.0,
                max_discrete_residual_v=1e-12,
                potential_antisymmetry_error_v=1e-12,
                probe_in_vacuum=True,
                probe_status='VALID_VACUUM',
                requested_probe_x_m=0.0,
                requested_probe_y_m=0.0,
            ),
        ]
        eval_drift = assess_probe_convergence(drifting_rows, requested_probe_xy_m=(0.0, 0.0))
        self.assertEqual(eval_drift.vacuum_status, 'ALL_IN_VACUUM')
        self.assertEqual(eval_drift.convergence_status, 'INCONCLUSIVE')
        self.assertFalse(eval_drift.is_converged)
        self.assertIn('exhibits significant numerical drift', eval_drift.assessment_summary)

        # 3. Off-grid target: sampled coordinates drift across mesh resolutions
        offgrid_study = electrode_pair_mesh_study(
            n_list=(41, 81, 101),
            probe_xy_m=(0.0013, 0.0027),
        )
        eval_offgrid = assess_probe_convergence(offgrid_study, requested_probe_xy_m=(0.0013, 0.0027))
        self.assertEqual(eval_offgrid.vacuum_status, 'ALL_IN_VACUUM')
        self.assertEqual(eval_offgrid.convergence_status, 'INCONCLUSIVE')
        self.assertFalse(eval_offgrid.coords_stable)
        self.assertFalse(eval_offgrid.is_converged)
        self.assertIn('drift or deviate from requested point', eval_offgrid.assessment_summary)

        # 4. Standard on-grid baseline at midpoint (0.0, 0.0)
        baseline_study = electrode_pair_mesh_study(n_list=(41, 81, 101, 161), probe_xy_m=(0.0, 0.0))
        eval_base = assess_probe_convergence(baseline_study, requested_probe_xy_m=(0.0, 0.0))
        self.assertEqual(eval_base.vacuum_status, 'ALL_IN_VACUUM')
        self.assertEqual(eval_base.convergence_status, 'CONVERGED')
        self.assertTrue(eval_base.coords_stable)
        self.assertTrue(eval_base.is_converged)
        self.assertIsNotNone(eval_base.relative_field_drift)
        self.assertLess(eval_base.relative_field_drift, 0.03)
        self.assertIn('converges smoothly', eval_base.assessment_summary)

    def test_r5_f3_continuous_conductor_disjointness_and_enclosure_containment(self):
        """R5-F3 regression: continuous geometry validation rejects overlap/wall penetration before rasterization."""
        # 1. Overlapping continuous disks with disjoint lattice masks on coarse grid:
        # n=11, width=0.04 m, centers -0.004 m and 0.0 m, radii 0.0021 m each.
        # Center distance = 0.004 m < sum of radii 0.0042 m (overlap by 0.2 mm).
        with self.assertRaises(ValueError) as ctx:
            GroundedBoxConfig(
                n=11,
                box_width_m=0.04,
                left_electrode=ElectrodeConfig(center_x_m=-0.004, center_y_m=0.0, radius_m=0.0021, voltage_v=500.0),
                right_electrode=ElectrodeConfig(center_x_m=0.0, center_y_m=0.0, radius_m=0.0021, voltage_v=-500.0),
            )
        self.assertIn('intersect or touch in continuous space', str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            electrode_pair_in_grounded_box(
                n=11,
                box_width_m=0.04,
                left_center_x_m=-0.004,
                left_center_y_m=0.0,
                right_center_x_m=0.0,
                right_center_y_m=0.0,
                left_radius_m=0.0021,
                right_radius_m=0.0021,
            )
        self.assertIn('intersect or touch in continuous space', str(ctx.exception))

        # 2. Continuous wall penetration with untriggered discrete boundary nodes:
        # Disk centered at (0.0177, 0.001) with radius 0.0025 in width 0.04 m enclosure (wall at 0.02 m).
        # Extent = 0.0177 + 0.0025 = 0.0202 m >= 0.0200 m (penetration by 0.2 mm).
        with self.assertRaises(ValueError) as ctx:
            GroundedBoxConfig(
                n=41,
                box_width_m=0.04,
                left_electrode=ElectrodeConfig(center_x_m=-0.008, center_y_m=0.0, radius_m=0.003, voltage_v=500.0),
                right_electrode=ElectrodeConfig(center_x_m=0.0177, center_y_m=0.001, radius_m=0.0025, voltage_v=-500.0),
            )
        self.assertIn('penetrates or touches grounded enclosure boundary', str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            electrode_pair_in_grounded_box(
                n=41,
                box_width_m=0.04,
                left_center_x_m=-0.008,
                left_center_y_m=0.0,
                right_center_x_m=0.0177,
                right_center_y_m=0.001,
                left_radius_m=0.003,
                right_radius_m=0.0025,
            )
        self.assertIn('penetrates or touches grounded enclosure boundary', str(ctx.exception))

    def test_r5_f4_panel_a_title_formatter_and_figure_inspection(self):
        """R5-F4 regression: test extracted voltage title formatter and complete Panel A title on symmetric/asymmetric/near-symmetric inputs."""
        # 1. Exactly symmetric inputs
        self.assertEqual(format_voltage_title(500.0, -500.0), '±500 V')
        self.assertEqual(format_voltage_title(1000.0, -1000.0), '±1000 V')
        self.assertEqual(format_voltage_title(250.5, -250.5), '±250.5 V')

        cfg_sym = GroundedBoxConfig(
            n=41,
            left_electrode=ElectrodeConfig(center_x_m=-0.008, center_y_m=0.0, radius_m=0.003, voltage_v=500.0),
            right_electrode=ElectrodeConfig(center_x_m=0.008, center_y_m=0.0, radius_m=0.003, voltage_v=-500.0),
        )
        self.assertEqual(
            format_panel_a_title(cfg_sym),
            'A · Case 1: Grounded Box (±500 V)\nDirichlet Potential (V)'
        )

        # 2. Asymmetric inputs
        self.assertEqual(format_voltage_title(800.0, -350.0), 'V_left=+800 V, V_right=-350 V')
        cfg_asym = GroundedBoxConfig(
            n=41,
            left_electrode=ElectrodeConfig(center_x_m=-0.008, center_y_m=0.0, radius_m=0.003, voltage_v=800.0),
            right_electrode=ElectrodeConfig(center_x_m=0.008, center_y_m=0.0, radius_m=0.003, voltage_v=-350.0),
        )
        self.assertEqual(
            format_panel_a_title(cfg_asym),
            'A · Case 1: Grounded Box (V_left=+800 V, V_right=-350 V)\nDirichlet Potential (V)'
        )

        # 3. Near-symmetric input (+500 V vs -499.997 V) must NEVER format as ±500 V
        self.assertEqual(format_voltage_title(500.0, -499.997), 'V_left=+500 V, V_right=-499.997 V')
        self.assertNotEqual(format_voltage_title(500.0, -499.997), '±500 V')

        cfg_near = GroundedBoxConfig(
            n=41,
            left_electrode=ElectrodeConfig(center_x_m=-0.008, center_y_m=0.0, radius_m=0.003, voltage_v=500.0),
            right_electrode=ElectrodeConfig(center_x_m=0.008, center_y_m=0.0, radius_m=0.003, voltage_v=-499.997),
        )
        self.assertIn('V_left=+500 V, V_right=-499.997 V', format_panel_a_title(cfg_near))
        self.assertNotIn('±500 V', format_panel_a_title(cfg_near))

        # 4. Zero voltages
        self.assertEqual(format_voltage_title(0.0, 0.0), 'V_left=+0 V, V_right=+0 V')


if __name__ == '__main__':
    unittest.main()
