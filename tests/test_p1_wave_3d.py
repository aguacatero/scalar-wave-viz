"""Unit and regression tests for P1-C 3D scalar wave numerics, CFL stability, and boundary absorption."""
import json
from pathlib import Path
import unittest
import numpy as np

import scalar_wave_3d as sw


class WaveGridConfigTests(unittest.TestCase):
    def test_cfl_condition_and_wavelength_calculation(self):
        """P1-C: WaveGridConfig computes CFL-stable timestep and points-per-wavelength."""
        cfg = sw.WaveGridConfig(n_x=48, n_y=48, n_z=48, dx_m=1.0, courant_factor=0.90)
        cfl_max = 1.0 / np.sqrt(3.0)
        actual_cfl = cfg.c_background_m_per_s * cfg.dt_s / cfg.dx_m
        self.assertLessEqual(actual_cfl, cfl_max)
        self.assertAlmostEqual(actual_cfl, 0.90 * cfl_max, places=7)

        # 20 grid cells per wavelength at f=0.05, c=1.0, dx=1.0
        self.assertAlmostEqual(cfg.background_wavelength_m, 20.0)
        self.assertAlmostEqual(cfg.background_points_per_wavelength, 20.0)

    def test_source_inside_sponge_rejected(self):
        """P1-C: Placing source inside boundary sponge raises ValueError."""
        # Sponge width is 8; placing source at x=6 (as in legacy notebook) must raise
        with self.assertRaises(ValueError) as ctx:
            sw.WaveGridConfig(sponge_width=8, source_x=6)
        self.assertIn('inside the 8-cell boundary sponge layer', str(ctx.exception))


class FDTDStepperSafetyTests(unittest.TestCase):
    def test_step_wave_fdtd_rejects_cfl_violation(self):
        """P1-R1-F5 regression: step_wave_fdtd rejects inputs exceeding CFL limit 1/sqrt(3)."""
        n = 16
        phi = np.zeros((n, n, n))
        phi_prev = np.zeros((n, n, n))
        c_field = np.ones((n, n, n))
        sigma_field = np.zeros((n, n, n))
        dx = 1.0
        dt_unstable = 0.60  # 0.60 > 1/sqrt(3) ~= 0.57735

        with self.assertRaises(ValueError) as ctx:
            sw.step_wave_fdtd(phi, phi_prev, c_field, sigma_field, dt=dt_unstable, dx=dx)
        self.assertIn('CFL stability condition violated', str(ctx.exception))

    def test_step_wave_fdtd_rejects_non_positive_or_non_finite_inputs(self):
        """P1-R1-F5 regression: step_wave_fdtd validates positive/finite parameters and fields."""
        n = 8
        phi = np.zeros((n, n, n))
        c_field = np.ones((n, n, n))
        sigma_field = np.zeros((n, n, n))

        # Non-positive dt
        with self.assertRaises(ValueError):
            sw.step_wave_fdtd(phi, phi, c_field, sigma_field, dt=-0.1, dx=1.0)

        # Non-positive dx
        with self.assertRaises(ValueError):
            sw.step_wave_fdtd(phi, phi, c_field, sigma_field, dt=0.1, dx=0.0)

        # Negative wave speed
        bad_c = c_field.copy()
        bad_c[2, 2, 2] = -1.0
        with self.assertRaises(ValueError):
            sw.step_wave_fdtd(phi, phi, bad_c, sigma_field, dt=0.1, dx=1.0)

        # Negative sigma
        bad_sig = sigma_field.copy()
        bad_sig[2, 2, 2] = -0.5
        with self.assertRaises(ValueError):
            sw.step_wave_fdtd(phi, phi, c_field, bad_sig, dt=0.1, dx=1.0)

    def test_step_wave_fdtd_rejects_mismatched_shapes(self):
        """P1-R1-F5 regression: step_wave_fdtd rejects mismatched array shapes."""
        phi = np.zeros((8, 8, 8))
        phi_prev = np.zeros((8, 8, 8))
        bad_c = np.ones((8, 8, 9))
        sigma = np.zeros((8, 8, 8))
        with self.assertRaises(ValueError):
            sw.step_wave_fdtd(phi, phi_prev, bad_c, sigma, dt=0.1, dx=1.0)


class WavelengthResolutionAuditTests(unittest.TestCase):
    def test_materials_library_resolution_audit(self):
        """P1-C: Audit spatial resolution; flag low-speed exotic presets as under-resolved."""
        # Baseline air: c=1.0 -> 20 cells/wavelength
        air = sw.audit_wavelength_resolution('Air (baseline)', 1.00)
        self.assertTrue(air.is_adequately_resolved)
        self.assertEqual(air.status, 'ADEQUATELY_RESOLVED')
        self.assertEqual(air.points_per_wavelength, 20.0)

        # Bismuth: c=0.55 -> 11 cells/wavelength
        bismuth = sw.audit_wavelength_resolution('Bismuth', 0.55)
        self.assertTrue(bismuth.is_adequately_resolved)
        self.assertEqual(bismuth.status, 'ADEQUATELY_RESOLVED')
        self.assertEqual(bismuth.points_per_wavelength, 11.0)

        # Element 115 / Moscovium: c=0.15 -> 3 cells/wavelength (severely under-resolved)
        moscovium = sw.audit_wavelength_resolution('Element 115 — Moscovium', 0.15)
        self.assertFalse(moscovium.is_adequately_resolved)
        self.assertEqual(moscovium.status, 'NUMERICALLY_UNDER_RESOLVED')
        self.assertAlmostEqual(moscovium.points_per_wavelength, 3.0, places=5)
        self.assertIn('WHAT-IF', moscovium.epistemic_label)

        # Metamaterial: c=0.04 -> 0.8 cells/wavelength (aliased / grid-pinned)
        meta = sw.audit_wavelength_resolution('Exotic metamaterial', 0.04)
        self.assertFalse(meta.is_adequately_resolved)
        self.assertEqual(meta.status, 'NUMERICALLY_UNDER_RESOLVED')
        self.assertLess(meta.points_per_wavelength, 1.0)


class PulsePropagationBenchmarkTests(unittest.TestCase):
    def test_pulse_propagation_speed(self):
        """P1-C: Gaussian wave packet propagates at physical speed c within tolerance."""
        res = sw.benchmark_pulse_propagation_speed(grid_size=40, n_steps=20, c_m_per_s=1.0)
        self.assertTrue(res.is_accurate_to_tolerance)
        self.assertLess(res.relative_speed_error, 0.05)


class BoundaryReflectionBenchmarkTests(unittest.TestCase):
    def test_sponge_boundary_reflection_probe(self):
        """P1-R1-F2 regression: Probe reflection measurement and smooth interior energy without mask-edge artifacts."""
        res = sw.benchmark_sponge_reflection_probe(
            grid_size=48, sponge_width=10, max_sigma=3.0, n_steps=70
        )
        self.assertTrue(res.is_absorbed_to_tolerance)
        self.assertLess(res.power_reflection_coefficient, 0.05)

        # Continuous interior energy density must be <= total domain energy (no artificial interface energy)
        self.assertLessEqual(res.final_interior_energy, res.final_total_energy + 1e-12)

        # Legacy masked proxy reproduces the reviewer-identified ~2.51% value
        self.assertAlmostEqual(res.masked_proxy_ratio, 0.0251, delta=0.010)


class DiscreteEnergyConservationTests(unittest.TestCase):
    def test_energy_conservation_in_undamped_medium(self):
        """P1-C: Discrete wave Hamiltonian is conserved in free space prior to boundary arrival."""
        nx = 40
        dx = 1.0
        c0 = 1.0
        dt = 0.85 * dx / (c0 * np.sqrt(3.0))

        c_field = np.full((nx, nx, nx), c0, dtype=float)
        sigma_field = np.zeros_like(c_field)

        coords = np.arange(nx) * dx
        mid = nx // 2
        x0 = float(mid * dx)
        sigma_pulse = 2.5 * dx

        X, Y, Z = np.meshgrid(coords, coords, coords, indexing='ij')
        r_sq = (X - x0)**2 + (Y - x0)**2 + (Z - x0)**2
        phi_0 = np.exp(-r_sq / (2.0 * sigma_pulse**2))

        lap_0 = sw.laplacian_3d_clamped(phi_0, dx)
        phi_minus_1 = phi_0 + 0.5 * (dt ** 2) * (c0 ** 2) * lap_0

        phi = phi_0.copy()
        phi_prev = phi_minus_1.copy()

        energies = []
        for step in range(15):
            e = sw.compute_discrete_wave_energy(phi, phi_prev, c_field, dt, dx)
            energies.append(e)
            phi_next = sw.step_wave_fdtd(phi, phi_prev, c_field, sigma_field, dt, dx)
            phi_prev, phi = phi, phi_next

        e_initial = energies[0]
        e_final = energies[-1]
        relative_energy_drift = abs(e_final - e_initial) / e_initial
        self.assertLess(relative_energy_drift, 0.05)

    def test_two_material_undamped_energy_conservation(self):
        """P1-R1-F4 regression: Discrete Hamiltonian is conserved across a two-medium interface."""
        res = sw.benchmark_two_material_energy_conservation(
            grid_size=36, n_steps=35, c1=1.0, c2=0.60
        )
        self.assertTrue(res.is_conserved_to_tolerance)
        self.assertLess(res.max_energy_drift_ratio, 0.08)


class NotebookIntegrationTests(unittest.TestCase):
    def test_notebook_and_runner_end_to_end(self):
        """P1-R1-F1 regression: wave_3d.ipynb uses validated runner and no defective legacy primitives."""
        nb_path = Path(__file__).resolve().parent.parent / 'wave_3d.ipynb'
        self.assertTrue(nb_path.exists())

        with open(nb_path, 'r', encoding='utf-8') as f:
            nb_data = json.load(f)

        code_text = ''
        for cell in nb_data.get('cells', []):
            if cell.get('cell_type') == 'code':
                code_text += ''.join(cell.get('source', [])) + '\n'

        # Defective primitives must be purged
        self.assertNotIn('np.roll', code_text, 'wave_3d.ipynb must not use periodic np.roll')
        self.assertNotIn('*= pml', code_text, 'wave_3d.ipynb must not use multiplicative *= pml damping')

        # Must import and call run_3d_simulation
        self.assertIn('run_3d_simulation', code_text)

        # End-to-end execution of production runner
        snapshots, obj_mask, metadata = sw.run_3d_simulation(
            shape='Sphere',
            material='Air (baseline)',
            n=24,
            n_frames=4,
            spf=2,
        )
        self.assertEqual(len(snapshots), 4)
        self.assertEqual(snapshots[0].shape, (24, 24, 24))
        self.assertTrue(np.all(np.isfinite(snapshots[-1])))
        self.assertTrue(metadata['resolution_audit']['is_adequately_resolved'])


if __name__ == '__main__':
    unittest.main()
