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
    def test_sponge_boundary_reflection_probe_legacy_proxy(self):
        """P1-R1-F2 / P1-R2-F1 / P1-R6-F2 regression: Legacy fixed-window proxy is demonstrably invalid for absorption."""
        res = sw.fixed_window_late_early_probe_amplitude_proxy(
            grid_size=48, sponge_width=10, max_sigma=3.0, n_steps=70
        )
        # P1-R6-F2: Legacy fixed-window proxy must fail closed and flag invalidity
        self.assertTrue(res.legacy_metric_invalid_for_absorption)
        self.assertFalse(res.is_absorbed_to_tolerance)
        self.assertLess(res.power_reflection_coefficient, 0.05)
        self.assertLessEqual(res.final_interior_energy, res.final_total_energy + 1e-12)
        # Legacy masked proxy reproduces the reviewer-identified ~2.51% value
        self.assertAlmostEqual(res.masked_proxy_ratio, 0.0251, delta=0.010)

        # Adversarial negative control: undamped Dirichlet wall (sigma=0) yields the same ~3.2% ratio,
        # confirming that the legacy calculation captures outgoing pulse tail rather than absorption
        res_zero = sw.fixed_window_late_early_probe_amplitude_proxy(
            grid_size=48, sponge_width=10, max_sigma=0.0, n_steps=70
        )
        self.assertTrue(res_zero.legacy_metric_invalid_for_absorption)
        self.assertFalse(res_zero.is_absorbed_to_tolerance)
        self.assertAlmostEqual(res_zero.power_reflection_coefficient, res.power_reflection_coefficient, places=2)

    def test_sponge_boundary_reflection_reference_subtracted(self):
        """P1-R2-F1 / P1-R3-F4 / P1-R4-F1 / P1-R5-F1 / P1-R6-F1 regression: Reference-subtracted reflection with closed discrete energy budget."""
        res = sw.benchmark_sponge_reflection_reference_subtracted(
            grid_size=40, sponge_width=8, max_sigma=3.0, n_steps=80, ref_grid_size=90, probe_offset=6
        )
        # P1-R5-F1: Explicit separation of simulation setup validity and demonstrated absorption
        self.assertTrue(res.is_simulation_setup_valid)
        self.assertTrue(res.is_sponge_absorbed_to_tolerance)
        self.assertTrue(res.is_sponge_benchmark_valid)
        self.assertTrue(res.is_absorbed_to_tolerance)
        self.assertTrue(res.reference_domain_free_of_wall_return)
        self.assertGreater(res.reference_wall_return_step, res.n_steps)
        self.assertGreaterEqual(res.n_steps, res.geometric_peak_return_step)
        self.assertGreater(res.cumulative_incident_outgoing_surface_flux, 0.0)
        self.assertEqual(res.geometric_pre_arrival_step, 10)
        self.assertLess(res.probe_local_peak_squared_proxy, 0.05)
        self.assertLess(res.probe_peak_squared_reflection_proxy, 0.05)
        self.assertLess(res.terminal_interior_reflected_energy_snapshot_proxy, 0.015)
        self.assertLess(res.peak_window_interior_reflected_energy_snapshot_proxy, 0.020)
        # Pre-arrival difference is bounded by Gaussian tail (< 1e-8) before reflected pulse returns
        self.assertLess(res.pre_arrival_difference_max, 1e-8)
        # P1-R4-F1 / P1-R6-F1: Closed discrete energy budget and symmetric surface flux proxy
        self.assertLess(res.discrete_energy_budget_closure_error, 1e-12)
        self.assertGreater(res.sponge_dissipated_energy_fraction, 0.95)
        self.assertLess(res.surface_flux_return_ratio_proxy, 0.05)
        self.assertLess(res.surface_integrated_return_flux_ratio, 0.05)
        self.assertEqual(res.surface_flux_return_ratio_proxy, res.surface_integrated_return_flux_ratio)

    def test_interior_control_volume_flux_continuity_and_residual(self):
        """P1-R6-F1 regression: Symmetric crossing-face flux tracks interior control-volume energy changes."""
        dx = 1.0
        c0 = 1.0
        dt = 0.85 * dx / (c0 * np.sqrt(3.0))
        n_steps = 25
        grid_size = 40
        sponge_width = 8

        c_field = np.full((grid_size, grid_size, grid_size), c0, dtype=float)
        sig_field = np.zeros_like(c_field)

        mid = grid_size // 2
        coords = np.arange(grid_size) * dx
        X, Y, Z = np.meshgrid(coords, coords, coords, indexing='ij')
        r_sq = (X - mid * dx) ** 2 + (Y - mid * dx) ** 2 + (Z - mid * dx) ** 2
        phi0 = np.exp(-r_sq / (2.0 * 2.0 ** 2))
        lap0 = sw.laplacian_3d_clamped(phi0, dx)
        phim1 = phi0 + 0.5 * (dt ** 2) * (c0 ** 2) * lap0

        e_init = sw.compute_interior_energy(phi0, phim1, c_field, dt, dx, sponge_width)
        p, pm = phi0.copy(), phim1.copy()
        cum_flux = 0.0
        for _ in range(n_steps):
            pn = sw.step_wave_fdtd(p, pm, c_field, sig_field, dt, dx)
            flux = sw.compute_enclosing_surface_outward_flux(pn, p, pm, dt, dx, sponge_width)
            cum_flux += flux * dt
            pm, p = p, pn

        e_final = sw.compute_interior_energy(p, pm, c_field, dt, dx, sponge_width)
        delta_e = e_final - e_init
        residual = delta_e + cum_flux

        # Outward flux accounts for the energy lost from Omega_int to within 1% of initial pulse energy
        self.assertLess(abs(residual) / e_init, 0.01)
        self.assertGreater(cum_flux, 0.5)
        self.assertLess(delta_e, -0.5)

    def test_sponge_reflection_parameter_sweep_and_adversarial_ref_domain(self):
        """P1-R3-F4 / P1-R4-F1 / P1-R5-F1 regression: Parameter sweep across ref domain, T_obs, spatial dx refinement, and dt."""
        sweep = sw.benchmark_sponge_reflection_parameter_sweep()
        self.assertTrue(sweep.is_sweep_stable)
        self.assertLess(sweep.reference_domain_invariance_diff, 1e-10)
        self.assertLess(sweep.dt_refinement_relative_diff, 0.15)
        self.assertTrue(sweep.monotonic_with_sponge_width)
        self.assertTrue(sweep.dx_refinement_consistent)
        self.assertTrue(sweep.observation_window_bounded)
        # P1-R5-F1: Inter-grid convergence between well-resolved grids (dx=1.0m vs 0.5m)
        self.assertLess(sweep.dx_snapshot_relative_diff, 0.15)
        self.assertLess(sweep.dx_flux_relative_diff, 0.15)

        # Adversarial negative control: reference domain too small (ref_grid_size=50 for n_steps=80)
        # allows outer reference wall reflection to return before n_steps completes
        contaminated = sw.benchmark_sponge_reflection_reference_subtracted(
            grid_size=40, sponge_width=8, max_sigma=3.0, n_steps=80, ref_grid_size=50, probe_offset=6
        )
        self.assertFalse(contaminated.reference_domain_free_of_wall_return)
        self.assertFalse(contaminated.is_simulation_setup_valid)
        self.assertFalse(contaminated.is_sponge_absorbed_to_tolerance)
        self.assertFalse(contaminated.is_sponge_benchmark_valid)

    def test_sponge_adversarial_zero_absorption_and_short_window_counterexamples(self):
        """P1-R5-F1 regression: Adversarial zero-absorption and short observation window counterexamples."""
        import math

        # 1. Undamped wall (sigma=0) with full observation window:
        # Simulation setup and discrete energy closure are valid, but sponge absorption is demonstrably FALSE
        undamped = sw.benchmark_sponge_reflection_reference_subtracted(
            grid_size=40, sponge_width=8, max_sigma=0.0, n_steps=80, ref_grid_size=90, probe_offset=6
        )
        self.assertTrue(undamped.is_simulation_setup_valid)
        self.assertFalse(undamped.is_sponge_absorbed_to_tolerance)
        self.assertFalse(undamped.is_sponge_benchmark_valid)
        self.assertEqual(undamped.sponge_dissipated_energy_fraction, 0.0)

        # 2. Short observation window (n_steps=1 < geometric_peak_return_step=37):
        # Simulation window is too short to observe any return or incident wave crossing, so setup is invalid
        short_window = sw.benchmark_sponge_reflection_reference_subtracted(
            grid_size=40, sponge_width=8, max_sigma=3.0, n_steps=1, ref_grid_size=90, probe_offset=6
        )
        self.assertFalse(short_window.is_simulation_setup_valid)
        self.assertFalse(short_window.is_sponge_absorbed_to_tolerance)
        self.assertFalse(short_window.is_sponge_benchmark_valid)
        self.assertLess(short_window.n_steps, short_window.geometric_peak_return_step)
        # Denominator is zero -> surface_integrated_return_flux_ratio must be NaN, not 0.0
        self.assertTrue(math.isnan(short_window.surface_integrated_return_flux_ratio))

        # 3. Adversarial zero-absorption with n_steps=1 (P1-R5-F1 adversarial counterexample):
        # Must fail closed: neither setup valid nor absorbed to tolerance
        adv_zero = sw.benchmark_sponge_reflection_reference_subtracted(
            grid_size=40, sponge_width=8, max_sigma=0.0, n_steps=1, ref_grid_size=90, probe_offset=6
        )
        self.assertFalse(adv_zero.is_simulation_setup_valid)
        self.assertFalse(adv_zero.is_sponge_absorbed_to_tolerance)
        self.assertFalse(adv_zero.is_sponge_benchmark_valid)

    def test_sponge_reflection_negative_and_positive_controls(self):
        """P1-R2-F1 / P1-R3-F4 / P1-R4-F1 regression: Negative (sigma=0) and positive sponge controls with dissipation."""
        rows = sw.benchmark_sponge_reflection_controls(
            sigma_list=(0.0, 0.5, 3.0, 15.0), grid_size=40, sponge_width=8, n_steps=80, ref_grid_size=90
        )
        ctrl_map = {r.max_sigma: r for r in rows}

        # 1. Negative control: undamped Dirichlet wall (sigma=0) produces strong reflection and zero sponge dissipation
        self.assertGreater(ctrl_map[0.0].probe_local_peak_squared_proxy, 0.10)
        self.assertGreater(ctrl_map[0.0].terminal_interior_reflected_energy_snapshot_proxy, 0.15)
        self.assertEqual(ctrl_map[0.0].sponge_dissipated_energy_fraction, 0.0)
        self.assertLess(ctrl_map[0.0].discrete_energy_budget_closure_error, 1e-12)

        # 2. Positive control: design sponge damping (sigma=3.0) dissipates > 97% of total energy
        self.assertLess(ctrl_map[3.0].probe_local_peak_squared_proxy, 0.05)
        self.assertLess(ctrl_map[3.0].terminal_interior_reflected_energy_snapshot_proxy, 0.015)
        self.assertGreater(ctrl_map[3.0].sponge_dissipated_energy_fraction, 0.95)
        self.assertLess(ctrl_map[3.0].discrete_energy_budget_closure_error, 1e-12)

        # 3. High-sigma control: impedance mismatch at entrance increases reflection compared to optimal sponge
        self.assertGreater(
            ctrl_map[15.0].terminal_interior_reflected_energy_snapshot_proxy,
            ctrl_map[3.0].terminal_interior_reflected_energy_snapshot_proxy,
        )


class DiscreteEnergyConservationTests(unittest.TestCase):
    def test_exact_discrete_leapfrog_energy_conservation(self):
        """P1-R2-F4 regression: Exact discrete staggered leapfrog Hamiltonian is conserved to machine precision."""
        nx = 24
        dx = 1.0
        c0 = 1.0
        dt = 0.5 * dx / (c0 * np.sqrt(3.0))

        c_field = np.full((nx, nx, nx), c0, dtype=float)
        sigma_field = np.zeros_like(c_field)

        coords = np.arange(nx) * dx
        mid = nx // 2
        x0 = float(mid * dx)
        sigma_pulse = 2.0 * dx

        X, Y, Z = np.meshgrid(coords, coords, coords, indexing='ij')
        r_sq = (X - x0)**2 + (Y - x0)**2 + (Z - x0)**2
        phi_0 = np.exp(-r_sq / (2.0 * sigma_pulse**2))
        phi_0[0, :, :] = phi_0[-1, :, :] = 0.0
        phi_0[:, 0, :] = phi_0[:, -1, :] = 0.0
        phi_0[:, :, 0] = phi_0[:, :, -1] = 0.0

        lap_0 = sw.laplacian_3d_clamped(phi_0, dx)
        phi_minus_1 = phi_0 + 0.5 * (dt ** 2) * (c0 ** 2) * lap_0

        phi = phi_0.copy()
        phi_prev = phi_minus_1.copy()

        phi_1 = sw.step_wave_fdtd(phi, phi_prev, c_field, sigma_field, dt, dx)
        h_initial = sw.compute_exact_discrete_leapfrog_energy(phi_1, phi, c_field, dt, dx)
        phi_prev, phi = phi, phi_1

        drifts = []
        for _ in range(40):
            phi_next = sw.step_wave_fdtd(phi, phi_prev, c_field, sigma_field, dt, dx)
            h = sw.compute_exact_discrete_leapfrog_energy(phi_next, phi, c_field, dt, dx)
            drifts.append(abs(h - h_initial) / h_initial)
            phi_prev, phi = phi, phi_next

        max_drift = max(drifts)
        self.assertLess(max_drift, 1e-12)  # Exact conservation to machine precision

    def test_two_material_undamped_energy_conservation(self):
        """P1-R1-F4 / P1-R2-F4 / P1-R3-F5 / P1-R4-F2 regression: Exact discrete Hamiltonian and terminal continuum energy."""
        res = sw.benchmark_two_material_energy_conservation(
            grid_size=36, n_steps=35, c1=1.0, c2=0.60
        )
        self.assertTrue(res.is_conserved_to_tolerance)
        self.assertLess(res.max_discrete_hamiltonian_drift_ratio, 1e-10)
        self.assertLess(res.max_continuum_diagnostic_drift_ratio, 0.08)

        # P1-R4-F2: continuum_energy_trajectory has n_steps + 1 entries (steps 0..n_steps)
        self.assertEqual(len(res.continuum_energy_trajectory), 36)
        self.assertEqual(len(res.exact_discrete_hamiltonian_trajectory), 35)

        # P1-R3-F5 / P1-R4-F2: final_energy must be the actual terminal trajectory value, not one step behind
        self.assertAlmostEqual(res.final_energy, res.continuum_energy_trajectory[-1], places=12)
        self.assertNotEqual(res.final_energy, res.continuum_energy_trajectory[-2])
        fabricated_max = res.initial_energy * (1.0 + res.max_continuum_diagnostic_drift_ratio)
        self.assertNotAlmostEqual(res.final_energy, fabricated_max, places=3)
        expected_signed_drift = (res.final_energy - res.initial_energy) / res.initial_energy
        self.assertAlmostEqual(res.terminal_continuum_signed_drift_ratio, expected_signed_drift, places=12)
        self.assertGreater(res.terminal_continuum_signed_drift_ratio, 0.0)

        # Adversarial negative-drift check: at n_steps=31, terminal continuum energy is strictly below initial_energy
        res_neg = sw.benchmark_two_material_energy_conservation(
            grid_size=36, n_steps=31, c1=1.0, c2=0.60
        )
        self.assertEqual(len(res_neg.continuum_energy_trajectory), 32)
        self.assertEqual(len(res_neg.exact_discrete_hamiltonian_trajectory), 31)
        self.assertLess(res_neg.max_discrete_hamiltonian_drift_ratio, 1e-10)
        self.assertAlmostEqual(res_neg.final_energy, res_neg.continuum_energy_trajectory[-1], places=12)
        self.assertNotEqual(res_neg.final_energy, res_neg.continuum_energy_trajectory[-2])
        self.assertLess(res_neg.final_energy, res_neg.initial_energy)
        self.assertLess(res_neg.terminal_continuum_signed_drift_ratio, 0.0)

        # P1-R4-F2: Assert terminal reported energy against independently evaluated diagnostic on evolved fields
        dt = 0.85 * 1.0 / (max(1.0, 0.60) * np.sqrt(3.0))
        c_field = np.full((36, 36, 36), 1.0, dtype=float)
        c_field[18:, :, :] = 0.60
        sig_field = np.zeros_like(c_field)
        coords = np.arange(36) * 1.0
        X, Y, Z = np.meshgrid(coords, coords, coords, indexing='ij')
        x0, y0, z0, sp = 9.0, 18.0, 18.0, 2.5
        p0 = np.exp(-((X - x0)**2 + (Y - y0)**2 + (Z - z0)**2) / (2.0 * sp**2))
        pm1 = np.exp(-((X - (x0 - 1.0 * dt))**2 + (Y - y0)**2 + (Z - z0)**2) / (2.0 * sp**2))
        for arr in (p0, pm1):
            arr[0, :, :] = arr[-1, :, :] = 0.0
            arr[:, 0, :] = arr[:, -1, :] = 0.0
            arr[:, :, 0] = arr[:, :, -1] = 0.0
        p, pm = p0.copy(), pm1.copy()
        for _ in range(35):
            pn = sw.step_wave_fdtd(p, pm, c_field, sig_field, dt, 1.0)
            pm, p = p, pn
        h_indep = sw.compute_sampled_continuum_energy_diagnostic(p, pm, c_field, dt, 1.0)
        self.assertAlmostEqual(res.final_energy, h_indep, places=12)


class WaveMeshConvergenceAndSourceNormalizationTests(unittest.TestCase):
    def test_wave_source_dt_independence(self):
        """P1-R2-F5 regression: Prescribed source injection waveform is invariant under dt refinement."""
        n = 24
        dx = 1.0
        c0 = 1.0
        c_field = np.full((n, n, n), c0)
        sigma_field = np.zeros((n, n, n))

        dt1 = 0.5 * dx / (c0 * np.sqrt(3.0))
        dt2 = dt1 / 2.0
        steps1 = 30
        steps2 = 60

        src = (6, 12, 12)
        obs = (12, 12, 12)
        omega = 2.0 * np.pi * 0.05

        # Evolve with dt1
        phi1 = np.zeros((n, n, n))
        phi1_prev = np.zeros((n, n, n))
        trace1 = []
        for s in range(steps1):
            pn = sw.step_wave_fdtd(phi1, phi1_prev, c_field, sigma_field, dt1, dx)
            pn[src] = np.sin(omega * (s + 1) * dt1)
            phi1_prev, phi1 = phi1, pn
            trace1.append(float(phi1[obs]))

        # Evolve with dt2
        phi2 = np.zeros((n, n, n))
        phi2_prev = np.zeros((n, n, n))
        trace2 = []
        for s in range(steps2):
            pn = sw.step_wave_fdtd(phi2, phi2_prev, c_field, sigma_field, dt2, dx)
            pn[src] = np.sin(omega * (s + 1) * dt2)
            phi2_prev, phi2 = phi2, pn
            trace2.append(float(phi2[obs]))

        p1 = max(trace1)
        p2 = max(trace2)
        rel_diff = abs(p2 - p1) / p1 if p1 > 0 else 0.0
        self.assertLess(rel_diff, 0.01)  # < 1% difference under dt halving (observed 0.056%)

    def test_wave_grid_convergence_second_order(self):
        """P1-R2-F5 regression: 3D wave solver exhibits asymptotic second-order convergence rate p ~= 2.0."""
        res = sw.benchmark_wave_grid_convergence(n_list=(17, 33, 65), T=0.5, c0=1.0, tolerance_min_order=1.70)
        self.assertTrue(res.is_second_order_converged)
        for p in res.observed_orders:
            self.assertGreaterEqual(p, 1.70)
            self.assertLessEqual(p, 2.30)

    def test_two_material_interface_transmission(self):
        """P1-R2-F5 / P1-R3-F3 regression: Analytical reflection & transmission coefficients across planar interface."""
        # 1. High-to-low wave speed (c1=1.0 -> c2=0.6): R_exact = -0.25, T_exact = +0.75
        res_slow = sw.benchmark_two_material_interface_transmission(c1=1.0, c2=0.6, dx_list=(1.0, 0.5, 0.25))
        self.assertTrue(res_slow.is_consistent)
        self.assertTrue(res_slow.errors_decrease_with_refinement)
        self.assertAlmostEqual(res_slow.analytical_r_amp, -0.25, places=12)
        self.assertAlmostEqual(res_slow.analytical_t_amp, 0.75, places=12)
        self.assertLess(res_slow.r_amp_abs_error, 0.005)
        self.assertLess(res_slow.t_amp_abs_error, 0.005)
        self.assertLess(res_slow.energy_partition_abs_error, 0.005)

        # 2. Adversarial low-to-high wave speed (c1=0.6 -> c2=1.0): R_exact = +0.25, T_exact = +1.25 > 1.0
        # Under the old P1-R2 heuristic (0 < T < I), this physically valid case would have failed because T_amp > 1.
        res_fast = sw.benchmark_two_material_interface_transmission(c1=0.6, c2=1.0, dx_list=(1.0, 0.5, 0.25))
        self.assertTrue(res_fast.is_consistent)
        self.assertTrue(res_fast.errors_decrease_with_refinement)
        self.assertAlmostEqual(res_fast.analytical_r_amp, 0.25, places=12)
        self.assertAlmostEqual(res_fast.analytical_t_amp, 1.25, places=12)
        self.assertGreater(res_fast.transmitted_peak, res_fast.incident_peak)
        self.assertLess(res_fast.r_amp_abs_error, 0.005)
        self.assertLess(res_fast.t_amp_abs_error, 0.005)
        self.assertLess(res_fast.energy_partition_abs_error, 0.005)


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
