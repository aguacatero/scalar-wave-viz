"""Unit and regression tests for P1-C 3D scalar wave numerics, CFL stability, and boundary absorption."""
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
    def test_sponge_boundary_reflection_coefficient(self):
        """P1-C: Quadratic sponge layer absorbs outgoing pulse with R < 5%."""
        res = sw.benchmark_sponge_boundary_reflection(
            grid_size=48, sponge_width=10, max_sigma=3.0, n_steps=70
        )
        self.assertTrue(res.is_absorbed_to_tolerance)
        self.assertLess(res.reflection_coefficient, 0.05)


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

        # 2nd order Taylor expansion for zero initial velocity
        lap_0 = sw.laplacian_3d_periodic_or_clamped(phi_0, dx, clamped=True)
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
        self.assertLess(relative_energy_drift, 0.05)  # < 5% numerical drift over 15 steps before boundary interaction


if __name__ == '__main__':
    unittest.main()
