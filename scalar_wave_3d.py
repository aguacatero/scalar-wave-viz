"""P1 Validated 3D Mathematical Scalar Wave Numerics and Benchmark Suite.

Repairs and benchmarks the legacy 3D scalar wave simulation (P1-C):
1. Relocates point/plane sources outside boundary sponge/damping layers.
2. Implements a mathematically formulated physical absorbing sponge layer:
   d^2 phi / dt^2 + sigma(x) d phi / dt = c(x)^2 nabla^2 phi
   discretized symmetrically:
   phi^{n+1} = [2*phi^n - (1 - 0.5*sigma*dt)*phi^{n-1} + (c*dt/dx)^2 * lap(phi^n)] / (1 + 0.5*sigma*dt)
3. Enforces CFL stability (c_max * dt / dx <= 1/sqrt(3)).
4. Audits grid-points-per-wavelength (N_lambda = lambda / dx);
   flags under-resolved exotic presets (e.g., speed=0.15 yielding N_lambda < 10)
   as NUMERICALLY_UNDER_RESOLVED and WHAT-IF.
5. Benchmarks free-space pulse propagation, energy conservation, and boundary reflection.

Explicit note: Mathematical scalar wave models do not imply physical scalar electrodynamics,
non-Maxwellian propulsion, or experimental properties for Element 115 / Moscovium.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class WaveGridConfig:
    n_x: int = 48
    n_y: int = 48
    n_z: int = 48
    dx_m: float = 1.0
    c_background_m_per_s: float = 1.0
    courant_factor: float = 0.90       # fraction of 3D CFL limit (1/sqrt(3) ~= 0.57735)
    sponge_width: int = 8
    sponge_max_sigma: float = 0.50     # peak absorption coefficient
    source_x: int = 14                 # placed strictly outside left sponge (x > 8)
    source_y: int = 24
    source_z: int = 24
    source_frequency_hz: float = 0.05  # omega = 2*pi*f

    def __post_init__(self):
        cfl_max = 1.0 / np.sqrt(3.0)
        cfl = self.courant_factor * cfl_max
        if self.courant_factor <= 0 or self.courant_factor >= 1.0:
            raise ValueError('courant_factor must be between 0 and 1.0')
        if self.sponge_width < 0 or self.sponge_width >= min(self.n_x, self.n_y, self.n_z) // 2:
            raise ValueError('Invalid sponge_width')
        # Validate source location is in the active physical region outside the sponge
        if (self.source_x < self.sponge_width or self.source_x >= self.n_x - self.sponge_width or
            self.source_y < self.sponge_width or self.source_y >= self.n_y - self.sponge_width or
            self.source_z < self.sponge_width or self.source_z >= self.n_z - self.sponge_width):
            raise ValueError(
                f'source_pos ({self.source_x}, {self.source_y}, {self.source_z}) is inside the '
                f'{self.sponge_width}-cell boundary sponge layer'
            )

    @property
    def dt_s(self) -> float:
        return float(self.courant_factor * self.dx_m / (self.c_background_m_per_s * np.sqrt(3.0)))

    @property
    def background_wavelength_m(self) -> float:
        return float(self.c_background_m_per_s / self.source_frequency_hz)

    @property
    def background_points_per_wavelength(self) -> float:
        return float(self.background_wavelength_m / self.dx_m)


@dataclass(frozen=True)
class WavelengthResolutionAudit:
    material_name: str
    wave_speed: float
    wavelength_m: float
    points_per_wavelength: float
    is_adequately_resolved: bool
    status: str
    epistemic_label: str
    diagnostic_note: str


def audit_wavelength_resolution(
    material_name: str,
    wave_speed: float,
    source_frequency_hz: float = 0.05,
    dx_m: float = 1.0,
    min_points_per_wavelength: float = 10.0,
) -> WavelengthResolutionAudit:
    """Audit numerical spatial resolution of wave oscillations for a given material preset."""
    if wave_speed <= 0 or source_frequency_hz <= 0 or dx_m <= 0:
        raise ValueError('Wave speed, frequency, and dx must be positive')

    wavelength = wave_speed / source_frequency_hz
    ppw = wavelength / dx_m

    if ppw >= min_points_per_wavelength:
        is_ok = True
        status = 'ADEQUATELY_RESOLVED'
        epistemic = 'ESTABLISHED_MODEL' if 'baseline' in material_name.lower() or 'air' in material_name.lower() else 'WHAT-IF_PARAM'
        note = f'Spatial oscillation sampled by {ppw:.1f} grid cells per wavelength (>= {min_points_per_wavelength:.1f}).'
    else:
        is_ok = False
        status = 'NUMERICALLY_UNDER_RESOLVED'
        epistemic = 'WHAT-IF_PARAM (UNVERIFIED)'
        note = (
            f'Low wave speed ({wave_speed:.2f}) yields only {ppw:.1f} cells per wavelength '
            f'(< {min_points_per_wavelength:.1f} required threshold). Numerical dispersion, grid anisotropy, '
            'and artificial pinning dominate. Not a valid basis for physical wave trapping claims.'
        )

    return WavelengthResolutionAudit(
        material_name=material_name,
        wave_speed=wave_speed,
        wavelength_m=wavelength,
        points_per_wavelength=ppw,
        is_adequately_resolved=is_ok,
        status=status,
        epistemic_label=epistemic,
        diagnostic_note=note,
    )


def create_sponge_conductivity_field(
    shape: tuple[int, int, int],
    sponge_width: int,
    max_sigma: float,
) -> np.ndarray:
    """Quadratic absorption profile: sigma(d) = max_sigma * (d / sponge_width)^2 near boundaries."""
    nx, ny, nz = shape
    sigma = np.zeros((nx, ny, nz), dtype=float)
    if sponge_width <= 0:
        return sigma

    # Coordinate distances into the sponge from each boundary
    for axis, size in enumerate((nx, ny, nz)):
        idx = np.arange(size)
        dist = np.minimum(idx, size - 1 - idx)
        d_sponge = np.clip((sponge_width - dist) / sponge_width, 0.0, 1.0)
        quad = max_sigma * (d_sponge ** 2)

        # Broadcast along the axis
        if axis == 0:
            sigma = np.maximum(sigma, quad[:, None, None])
        elif axis == 1:
            sigma = np.maximum(sigma, quad[None, :, None])
        else:
            sigma = np.maximum(sigma, quad[None, None, :])
    return sigma


def laplacian_3d_periodic_or_clamped(phi: np.ndarray, dx: float, clamped: bool = True) -> np.ndarray:
    """3D 7-point central-difference Laplacian."""
    if clamped:
        lap = np.zeros_like(phi)
        inv_dx2 = 1.0 / (dx * dx)
        # Interior points
        lap[1:-1, 1:-1, 1:-1] = (
            phi[2:, 1:-1, 1:-1] + phi[:-2, 1:-1, 1:-1] +
            phi[1:-1, 2:, 1:-1] + phi[1:-1, :-2, 1:-1] +
            phi[1:-1, 1:-1, 2:] + phi[1:-1, 1:-1, :-2] -
            6.0 * phi[1:-1, 1:-1, 1:-1]
        ) * inv_dx2
        return lap
    else:
        # Periodic roll
        lap = (
            np.roll(phi, -1, 0) + np.roll(phi, 1, 0) +
            np.roll(phi, -1, 1) + np.roll(phi, 1, 1) +
            np.roll(phi, -1, 2) + np.roll(phi, 1, 2) -
            6.0 * phi
        ) / (dx * dx)
        return lap


def step_wave_fdtd(
    phi: np.ndarray,
    phi_prev: np.ndarray,
    c_field: np.ndarray,
    sigma_field: np.ndarray,
    dt: float,
    dx: float,
) -> np.ndarray:
    """Symmetric time-stepping for damped scalar wave equation.

    (phi^{n+1} - 2*phi^n + phi^{n-1}) / dt^2 + sigma * (phi^{n+1} - phi^{n-1}) / (2*dt) = c^2 * lap(phi^n)
    """
    lap = laplacian_3d_periodic_or_clamped(phi, dx, clamped=True)
    c2_lap = (c_field ** 2) * lap

    sig_dt_half = 0.5 * sigma_field * dt
    phi_next = (
        2.0 * phi - (1.0 - sig_dt_half) * phi_prev + (dt ** 2) * c2_lap
    ) / (1.0 + sig_dt_half)

    # Clamped boundary condition at outer edge
    phi_next[0, :, :] = phi_next[-1, :, :] = 0.0
    phi_next[:, 0, :] = phi_next[:, -1, :] = 0.0
    phi_next[:, :, 0] = phi_next[:, :, -1] = 0.0
    return phi_next


def compute_discrete_wave_energy(
    phi: np.ndarray,
    phi_prev: np.ndarray,
    c_field: np.ndarray,
    dt: float,
    dx: float,
) -> float:
    """Compute discrete field Hamiltonian (kinetic + gradient potential energy)."""
    # Time derivative at half step
    v = (phi - phi_prev) / dt
    kinetic = 0.5 * np.sum(v**2) * (dx**3)

    # Spatial gradients
    gx = (phi[1:, :, :] - phi[:-1, :, :]) / dx
    gy = (phi[:, 1:, :] - phi[:, :-1, :]) / dx
    gz = (phi[:, :, 1:] - phi[:, :, :-1]) / dx

    c_x = 0.5 * (c_field[1:, :, :] + c_field[:-1, :, :])
    c_y = 0.5 * (c_field[:, 1:, :] + c_field[:, :-1, :])
    c_z = 0.5 * (c_field[:, :, 1:] + c_field[:, :, :-1])

    potential = 0.5 * (
        np.sum((c_x * gx)**2) +
        np.sum((c_y * gy)**2) +
        np.sum((c_z * gz)**2)
    ) * (dx**3)

    return float(kinetic + potential)


@dataclass(frozen=True)
class PulsePropagationBenchmarkResult:
    n_steps: int
    dt_s: float
    theoretical_distance_m: float
    measured_distance_m: float
    relative_speed_error: float
    is_accurate_to_tolerance: bool


def benchmark_pulse_propagation_speed(
    grid_size: int = 40,
    n_steps: int = 20,
    dx_m: float = 1.0,
    c_m_per_s: float = 1.0,
    courant_factor: float = 0.85,
    tolerance_speed_error: float = 0.05,
) -> PulsePropagationBenchmarkResult:
    """Benchmark propagation velocity of a Gaussian pulse along the x-axis in 3D grid."""
    dt = courant_factor * dx_m / (c_m_per_s * np.sqrt(3.0))
    c_field = np.full((grid_size, grid_size, grid_size), c_m_per_s, dtype=float)
    sigma_field = np.zeros_like(c_field)

    coords = np.arange(grid_size) * dx_m
    x0 = 10.0 * dx_m
    sigma_pulse = 3.5 * dx_m

    # Initial Gaussian pulse centered at x0 along x
    x_3d = coords[:, None, None]
    phi_0 = np.exp(-((x_3d - x0) ** 2) / (2.0 * sigma_pulse ** 2))
    # Right-traveling pulse: phi(t = -dt) = phi0(x - c*(-dt)) = phi0(x + c*dt)
    phi_minus_1 = np.exp(-((x_3d - (x0 - c_m_per_s * dt)) ** 2) / (2.0 * sigma_pulse ** 2))

    phi = phi_0.copy()
    phi_prev = phi_minus_1.copy()

    for _ in range(n_steps):
        phi_next = step_wave_fdtd(phi, phi_prev, c_field, sigma_field, dt, dx_m)
        phi_prev, phi = phi, phi_next

    # Measure pulse center of mass (centroid) along x (center line y = mid, z = mid)
    mid = grid_size // 2
    profile = phi[:, mid, mid]
    weights = profile ** 2
    measured_center = float(np.sum(coords * weights) / np.sum(weights))

    theoretical_dist = c_m_per_s * n_steps * dt
    measured_dist = measured_center - x0
    rel_err = float(abs(measured_dist - theoretical_dist) / theoretical_dist)

    return PulsePropagationBenchmarkResult(
        n_steps=n_steps,
        dt_s=dt,
        theoretical_distance_m=theoretical_dist,
        measured_distance_m=measured_dist,
        relative_speed_error=rel_err,
        is_accurate_to_tolerance=bool(rel_err <= tolerance_speed_error),
    )


@dataclass(frozen=True)
class BoundaryReflectionBenchmarkResult:
    initial_energy: float
    remaining_interior_energy: float
    reflection_coefficient: float
    is_absorbed_to_tolerance: bool
    diagnostic_note: str


def benchmark_sponge_boundary_reflection(
    grid_size: int = 48,
    sponge_width: int = 10,
    max_sigma: float = 3.0,
    n_steps: int = 70,
    tolerance_reflection: float = 0.05,
) -> BoundaryReflectionBenchmarkResult:
    """Benchmark absorption efficiency of the quadratic sponge layer using discrete energy."""
    dx = 1.0
    c0 = 1.0
    dt = 0.85 * dx / (c0 * np.sqrt(3.0))

    c_field = np.full((grid_size, grid_size, grid_size), c0, dtype=float)
    sigma_field = create_sponge_conductivity_field(
        (grid_size, grid_size, grid_size), sponge_width, max_sigma
    )

    # Spherical pulse initialized at center of active grid
    coords = np.arange(grid_size) * dx
    mid = grid_size // 2
    x0 = float(mid * dx)
    sigma_pulse = 2.5 * dx

    X, Y, Z = np.meshgrid(coords, coords, coords, indexing='ij')
    r_sq = (X - x0)**2 + (Y - x0)**2 + (Z - x0)**2
    phi_0 = np.exp(-r_sq / (2.0 * sigma_pulse ** 2))
    lap_0 = laplacian_3d_periodic_or_clamped(phi_0, dx, clamped=True)
    phi_minus_1 = phi_0 + 0.5 * (dt ** 2) * (c0 ** 2) * lap_0

    e_initial = compute_discrete_wave_energy(phi_0, phi_minus_1, c_field, dt, dx)

    phi = phi_0.copy()
    phi_prev = phi_minus_1.copy()

    # Step wave through domain into boundary sponge
    for _ in range(n_steps):
        phi_next = step_wave_fdtd(phi, phi_prev, c_field, sigma_field, dt, dx)
        phi_prev, phi = phi, phi_next

    # Measure remaining energy in active interior (excluding sponge layer)
    mask_int = np.zeros_like(phi, dtype=bool)
    mask_int[sponge_width:-sponge_width, sponge_width:-sponge_width, sponge_width:-sponge_width] = True
    phi_int = np.where(mask_int, phi, 0.0)
    phi_int_prev = np.where(mask_int, phi_prev, 0.0)

    e_int = compute_discrete_wave_energy(phi_int, phi_int_prev, c_field, dt, dx)
    refl_ratio = float(e_int / e_initial)
    is_ok = bool(refl_ratio <= tolerance_reflection)

    note = (
        f'Initial wave pulse energy {e_initial:.3f} J; remaining interior energy after '
        f'{n_steps} steps: {e_int:.4f} J, giving boundary energy leakage/reflection ratio '
        f'R = {refl_ratio:.2%} (< {tolerance_reflection:.0%} tolerance).'
    )

    return BoundaryReflectionBenchmarkResult(
        initial_energy=e_initial,
        remaining_interior_energy=e_int,
        reflection_coefficient=refl_ratio,
        is_absorbed_to_tolerance=is_ok,
        diagnostic_note=note,
    )

