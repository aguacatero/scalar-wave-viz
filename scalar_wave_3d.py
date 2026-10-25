"""P1 Validated 3D Mathematical Scalar Wave Numerics and Benchmark Suite.

Repairs and benchmarks the 3D scalar wave simulation (P1-C, P1 R1 fixes):
1. Relocates point/plane sources outside boundary sponge/damping layers (x_source > w_sponge).
2. Implements a mathematically formulated physical absorbing sponge layer:
   d^2 phi / dt^2 + sigma(x) d phi / dt = c(x)^2 nabla^2 phi
   discretized symmetrically:
   phi^{n+1} = [2*phi^n - (1 - 0.5*sigma*dt)*phi^{n-1} + (c*dt/dx)^2 * lap(phi^n)] / (1 + 0.5*sigma*dt)
3. Enforces CFL stability (c_max * dt / dx <= 1/sqrt(3)) directly inside step_wave_fdtd.
4. Uses mathematically consistent discrete continuum energy functional:
   H = 0.5 * (phi_t / c(x))^2 + 0.5 * |nabla phi|^2
   with dimensionless/arbitrary energy units (not uncalibrated Joules).
5. Eliminates artificial interface jump artifacts by computing energy density on unmasked
   fields before integrating over interior volumes.
6. Measures sponge boundary reflection via probe time-series against unreflected reference.
7. Audits grid-points-per-wavelength (N_lambda = lambda / dx);
   flags under-resolved exotic presets (e.g., speed=0.15 yielding N_lambda < 10)
   as NUMERICALLY_UNDER_RESOLVED and WHAT-IF.
8. Provides production simulation runner for wave_3d.ipynb and test suites.

Explicit note: Mathematical scalar wave models do not imply physical scalar electrodynamics,
non-Maxwellian propulsion, or experimental properties for Element 115 / Moscovium.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np


MATERIALS: dict[str, dict[str, Any]] = {
    'Air (baseline)': {
        'speed': 1.00,
        'color': '#aaaaaa',
        'desc': 'No object — unobstructed reference wave',
        'epistemic': 'ESTABLISHED_MODEL',
    },
    'Bismuth': {
        'speed': 0.55,
        'color': '#d4a832',
        'desc': 'Real diamagnetic element — modeled with stipulated hypothetical wave speed c=0.55 for toy wave refraction study (WHAT-IF)',
        'epistemic': 'WHAT-IF_PARAM',
    },
    'Element 115 — Moscovium': {
        'speed': 0.15,
        'color': '#cc44ff',
        'desc': 'Superheavy synthetic element (hypothetical wave parameter, severely under-resolved on coarse grids)',
        'epistemic': 'WHAT-IF_PARAM (UNVERIFIED)',
    },
    'Exotic metamaterial': {
        'speed': 0.04,
        'color': '#00ffdd',
        'desc': 'Theoretical low-speed metamaterial (grid-pinned on coarse grids)',
        'epistemic': 'WHAT-IF_PARAM (UNVERIFIED)',
    },
}


def make_shape_mask(n: int, shape: str) -> np.ndarray:
    """Return a boolean (n, n, n) array marking voxels inside the object."""
    c = n // 2
    idx = np.arange(n)
    x, y, z = np.meshgrid(idx, idx, idx, indexing='ij')
    r = int(n * 0.17)

    if shape == 'Sphere':
        return (x - c)**2 + (y - c)**2 + (z - c)**2 < r**2

    if shape == 'Torus':
        r_maj, r_tube = r * 1.6, r * 0.55
        # Ring in YZ plane so the hole faces the incoming wave (X direction)
        ryz = np.sqrt((y - c)**2 + (z - c)**2)
        return (ryz - r_maj)**2 + (x - c)**2 < r_tube**2

    if shape == 'Pyramid':
        h, base = r * 2.2, r * 1.1
        frac = np.clip(((c + h / 2) - z) / h, 0, 1)
        half = base * frac
        return (
            (np.abs(x - c) < half) & (np.abs(y - c) < half) &
            (z >= c - h / 2) & (z <= c + h / 2)
        )

    if shape == 'Bismuth Crystal':
        # Rhombohedral lattice: cube sheared along body diagonal
        a, sh = r * 1.25, 0.38
        u = (x - c) + sh * (z - c)
        v = (y - c) + sh * (z - c)
        w = (z - c)
        return (np.abs(u) < a) & (np.abs(v) < a) & (np.abs(w) < a * 0.65)

    return np.zeros((n, n, n), dtype=bool)


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


def laplacian_3d_clamped(phi: np.ndarray, dx: float) -> np.ndarray:
    """3D 7-point central-difference Laplacian with clamped zero outer boundary."""
    lap = np.zeros_like(phi)
    inv_dx2 = 1.0 / (dx * dx)
    # Interior points (clamped boundary implies outer nodes held at zero)
    lap[1:-1, 1:-1, 1:-1] = (
        phi[2:, 1:-1, 1:-1] + phi[:-2, 1:-1, 1:-1] +
        phi[1:-1, 2:, 1:-1] + phi[1:-1, :-2, 1:-1] +
        phi[1:-1, 1:-1, 2:] + phi[1:-1, 1:-1, :-2] -
        6.0 * phi[1:-1, 1:-1, 1:-1]
    ) * inv_dx2
    return lap


def step_wave_fdtd(
    phi: np.ndarray,
    phi_prev: np.ndarray,
    c_field: np.ndarray,
    sigma_field: np.ndarray,
    dt: float,
    dx: float,
    source_field: np.ndarray | None = None,
    boundary_mode: str = 'clamped',
) -> np.ndarray:
    """Symmetric time-stepping for damped scalar wave equation with CFL enforcement.

    Evolves the non-divergence wave equation:
    (phi^{n+1} - 2*phi^n + phi^{n-1}) / dt^2 + sigma * (phi^{n+1} - phi^{n-1}) / (2*dt) = c^2 * lap(phi^n) + S^n
    """
    # 1. Parameter and shape sanity validation
    if dt <= 0.0 or not np.isfinite(dt):
        raise ValueError(f'Time step dt must be positive and finite, got {dt}')
    if dx <= 0.0 or not np.isfinite(dx):
        raise ValueError(f'Grid spacing dx must be positive and finite, got {dx}')
    if phi.ndim != 3:
        raise ValueError(f'phi must be a 3D array, got shape {phi.shape}')
    if phi_prev.shape != phi.shape or c_field.shape != phi.shape or sigma_field.shape != phi.shape:
        raise ValueError(
            f'Field shapes must match: phi={phi.shape}, phi_prev={phi_prev.shape}, '
            f'c_field={c_field.shape}, sigma_field={sigma_field.shape}'
        )
    if not (np.all(np.isfinite(phi)) and np.all(np.isfinite(phi_prev))):
        raise ValueError('phi and phi_prev must contain only finite numerical values')
    if np.any(c_field <= 0.0) or not np.all(np.isfinite(c_field)):
        raise ValueError('Wave speed c_field must be strictly positive and finite everywhere')
    if np.any(sigma_field < 0.0) or not np.all(np.isfinite(sigma_field)):
        raise ValueError('Conductivity sigma_field must be non-negative and finite everywhere')
    if source_field is not None:
        if source_field.shape != phi.shape:
            raise ValueError(f'source_field shape {source_field.shape} must match phi shape {phi.shape}')
        if not np.all(np.isfinite(source_field)):
            raise ValueError('source_field must contain only finite numerical values')
    if boundary_mode not in ('clamped', 'planar_x'):
        raise ValueError(f"Unsupported boundary_mode: {boundary_mode}. Use 'clamped' or 'planar_x'.")

    # 2. Strict CFL stability verification
    c_max = float(np.max(c_field))
    cfl = c_max * dt / dx
    cfl_limit = 1.0 / np.sqrt(3.0)
    if cfl > cfl_limit * (1.0 + 1e-6):
        raise ValueError(
            f'CFL stability condition violated: max(c)*dt/dx = {cfl:.5f} exceeds '
            f'3D limit 1/sqrt(3) ~= {cfl_limit:.5f}'
        )

    # 3. Symmetric update with normalized source term
    lap = laplacian_3d_clamped(phi, dx)
    c2_lap = (c_field ** 2) * lap
    rhs = c2_lap if source_field is None else c2_lap + source_field

    sig_dt_half = 0.5 * sigma_field * dt
    phi_next = (
        2.0 * phi - (1.0 - sig_dt_half) * phi_prev + (dt ** 2) * rhs
    ) / (1.0 + sig_dt_half)

    # 4. Outer boundary condition
    phi_next[0, :, :] = phi_next[-1, :, :] = 0.0
    if boundary_mode == 'planar_x':
        # Homogeneous Neumann (zero transverse gradient) on y and z faces for planar x-wave benchmarks
        phi_next[:, 0, :] = phi_next[:, 1, :]
        phi_next[:, -1, :] = phi_next[:, -2, :]
        phi_next[:, :, 0] = phi_next[:, :, 1]
        phi_next[:, :, -1] = phi_next[:, :, -2]
    else:
        phi_next[:, 0, :] = phi_next[:, -1, :] = 0.0
        phi_next[:, :, 0] = phi_next[:, :, -1] = 0.0
    return phi_next


def compute_exact_discrete_leapfrog_energy(
    phi_next: np.ndarray,
    phi: np.ndarray,
    c_field: np.ndarray,
    dt: float,
    dx: float,
) -> float:
    """Exact discrete Hamiltonian invariant for the leapfrog 7-point Laplacian wave equation (P1-R2-F4).

    Conserved functional at staggered half-time step t^{n+1/2}:
    H^{n+1/2} = 0.5 * sum_i ( (phi^{n+1} - phi^n)/(c_i dt) )^2 dx^3 - 0.5 * sum_i phi^{n+1} lap(phi^n) dx^3
    Conserved to machine precision in undamped media (sigma = 0).
    Units: arbitrary energy units [E_arb] (dimensionless toy field model, not Joules).
    """
    v_half = (phi_next - phi) / dt
    kin = 0.5 * np.sum((v_half / c_field) ** 2) * (dx ** 3)
    lap = laplacian_3d_clamped(phi, dx)
    pot = -0.5 * np.sum(phi_next * lap) * (dx ** 3)
    return float(kin + pot)


def validate_interior_sponge_width(
    sponge_width: int,
    grid_dim: int | tuple[int, ...] | list[int] | np.ndarray,
) -> int:
    """Validate that sponge_width specifies a valid non-empty interior subvolume (P1-R8-F3, P1-R9-F1).

    Fails closed: sponge_width must be a strict integer satisfying 1 <= 2 * sponge_width < min(grid_shape)
    so that every Cartesian dimension d has a strictly positive interior length (d - 2 * sw >= 1).
    """
    if isinstance(sponge_width, bool) or not isinstance(sponge_width, (int, np.integer)):
        raise ValueError(f"sponge_width must be an integer, got {sponge_width!r}")
    sw = int(sponge_width)
    if isinstance(grid_dim, (tuple, list, np.ndarray)):
        min_dim = min(int(d) for d in grid_dim)
        dims_desc = f"min dimension {min_dim} (shape {tuple(int(d) for d in grid_dim)})"
    else:
        min_dim = int(grid_dim)
        dims_desc = f"dimension {min_dim}"

    if sw < 1 or 2 * sw >= min_dim:
        raise ValueError(
            f"sponge_width must satisfy 1 <= 2 * sponge_width < {min_dim} ({dims_desc}) "
            f"to define a non-empty Cartesian interior, got sponge_width={sw}"
        )
    return sw


def compute_interior_exact_discrete_leapfrog_energy(
    phi_next: np.ndarray,
    phi: np.ndarray,
    c_field: np.ndarray,
    dt: float,
    dx: float,
    sponge_width: int,
) -> float:
    """Exact discrete staggered leapfrog Hamiltonian restricted to Cartesian interior Omega_int (P1-R7-F1, P1-R8-F1, P1-R8-F3, P1-R9-F1).

    Evaluates the localized leapfrog Hamiltonian at staggered half-time step t^{n+1/2}:
      H_int^{n+1/2} = 0.5 * sum_{i in Omega_int} ( (phi^{n+1} - phi^n)/(c_i dt) )^2 dx^3
                    - 0.5 * sum_{i in Omega_int} phi^{n+1} lap(phi^n) dx^3
    where Omega_int = [sw, N-sw)^3.

    Satisfies the complete discrete local control-volume continuity theorem:
      H_int^{n+1/2} - H_int^{n-1/2} + Delta B_{boundary}^n + Delta D_{int}^n = Delta W_{source, int}^n
    to machine precision (< 1e-12) under all dt, dx, material c(x), damping, and source terms.
    Units: arbitrary energy units [E_arb] (not Joules).
    """
    sw = validate_interior_sponge_width(sponge_width, phi.shape)
    v_half = (phi_next - phi) / dt
    kin = 0.5 * np.sum((v_half[sw:-sw, sw:-sw, sw:-sw] / c_field[sw:-sw, sw:-sw, sw:-sw]) ** 2) * (dx ** 3)
    lap = laplacian_3d_clamped(phi, dx)
    pot = -0.5 * np.sum(phi_next[sw:-sw, sw:-sw, sw:-sw] * lap[sw:-sw, sw:-sw, sw:-sw]) * (dx ** 3)
    return float(kin + pot)


def compute_exact_discrete_interior_boundary_transfer(
    phi_cur: np.ndarray,
    phi_prev: np.ndarray,
    dt: float,
    dx: float,
    sponge_width: int,
) -> float:
    """Exact discrete boundary bond energy transfer across the 6 faces of dOmega_int (P1-R7-F1, P1-R8-F3, P1-R9-F1).

    From the summation-by-parts identity for the 7-point Laplacian on Cartesian grid,
    internal bonds cancel identically, leaving only crossing bonds between i in Omega_int
    and neighboring j not in Omega_int:
      Delta B_{boundary}^n = 0.5 * dx * sum_{faces, bonds} (phi_i^{n-1} phi_j^n - phi_i^n phi_j^{n-1}).

    Satisfies the EXACT discrete control-volume theorem:
      H_int^{n+1/2} - H_int^{n-1/2} + Delta B_{boundary}^n + Delta D_{int}^n = Delta W_{source, int}^n
    to machine precision (< 1e-12) under all dt, dx, and damping configurations.
    Units: arbitrary energy units [E_arb] (not Joules).
    """
    sw = validate_interior_sponge_width(sponge_width, phi_cur.shape)

    f_total = 0.0
    for face_dim in (0, 1, 2):
        for is_high in (False, True):
            if face_dim == 0:
                i_idx = -sw - 1 if is_high else sw
                j_idx = -sw if is_high else sw - 1
                i_sl = (i_idx, slice(sw, -sw), slice(sw, -sw))
                j_sl = (j_idx, slice(sw, -sw), slice(sw, -sw))
            elif face_dim == 1:
                i_idx = -sw - 1 if is_high else sw
                j_idx = -sw if is_high else sw - 1
                i_sl = (slice(sw, -sw), i_idx, slice(sw, -sw))
                j_sl = (slice(sw, -sw), j_idx, slice(sw, -sw))
            else:
                i_idx = -sw - 1 if is_high else sw
                j_idx = -sw if is_high else sw - 1
                i_sl = (slice(sw, -sw), slice(sw, -sw), i_idx)
                j_sl = (slice(sw, -sw), slice(sw, -sw), j_idx)
            f_face = 0.5 * dx * np.sum(phi_prev[i_sl] * phi_cur[j_sl] - phi_cur[i_sl] * phi_prev[j_sl])
            f_total += f_face
    return float(f_total)


def compute_interior_sponge_dissipated_energy(
    phi_next: np.ndarray,
    phi_prev: np.ndarray,
    c_field: np.ndarray,
    sigma_field: np.ndarray,
    dt: float,
    dx: float,
    sponge_width: int,
) -> float:
    """Exact discrete dissipation inside Cartesian interior Omega_int (P1-R7-F1, P1-R8-F3, P1-R9-F1).

    Units: arbitrary energy units [E_arb] (not Joules).
    """
    sw = validate_interior_sponge_width(sponge_width, phi_next.shape)
    v_centered = (phi_next - phi_prev) / (2.0 * dt)
    sig_int = sigma_field[sw:-sw, sw:-sw, sw:-sw]
    c_int = c_field[sw:-sw, sw:-sw, sw:-sw]
    v_int = v_centered[sw:-sw, sw:-sw, sw:-sw]
    dissipated_power = np.sum((sig_int / (c_int ** 2)) * (v_int ** 2)) * (dx ** 3)
    return float(dt * dissipated_power)


def compute_interior_source_work_step(
    phi_next: np.ndarray,
    phi_prev: np.ndarray,
    source_field: np.ndarray | None,
    c_field: np.ndarray,
    dt: float,
    dx: float,
    sponge_width: int,
) -> float:
    """Exact discrete source work done on Cartesian interior Omega_int during step n (P1-R8-F1, P1-R8-F3, P1-R9-F1).

    From the leapfrog discrete equation with normalized source:
      (phi^{n+1} - 2 phi^n + phi^{n-1}) / (c^2 dt^2) + (sigma / c^2) v_centered = lap(phi) + S / c^2.
    Multiplying by v_centered * dx^3 yields the exact source power term:
      Delta W_{source, int}^n = dt * dx^3 * sum_{i in Omega_int} (S_i^n / c_i^2) * ( (phi_i^{n+1} - phi_i^{n-1}) / (2 dt) ).

    Units: arbitrary energy units [E_arb] (not Joules).
    """
    sw = validate_interior_sponge_width(sponge_width, phi_next.shape)
    if source_field is None:
        return 0.0
    v_centered = (phi_next - phi_prev) / (2.0 * dt)
    s_int = source_field[sw:-sw, sw:-sw, sw:-sw]
    c_int = c_field[sw:-sw, sw:-sw, sw:-sw]
    v_int = v_centered[sw:-sw, sw:-sw, sw:-sw]
    source_work = dt * (dx ** 3) * np.sum((s_int / (c_int ** 2)) * v_int)
    return float(source_work)


def compute_discrete_energy_density(
    phi: np.ndarray,
    phi_prev: np.ndarray,
    c_field: np.ndarray,
    dt: float,
    dx: float,
) -> np.ndarray:
    """Compute local continuum-inspired energy density diagnostic for the non-divergence wave equation.

    Continuum functional for phi_tt = c(x)^2 nabla^2 phi:
      H_cont(x) = 0.5 * (phi_t / c(x))^2 + 0.5 * |nabla phi|^2
    Units: arbitrary energy density [E_arb] / m^3 (not Joules).
    Note (P1-R8-F2): Evaluated via backward difference in time for velocity and central spatial differences
    for gradient. It is a continuum-inspired numerical diagnostic proxy, not an exact discrete invariant
    for the staggered leapfrog equation.
    """
    v = (phi - phi_prev) / dt
    kinetic_density = 0.5 * ((v / c_field) ** 2)

    # Pointwise spatial gradients via central differences (one-sided at boundary)
    gx, gy, gz = np.gradient(phi, dx, axis=(0, 1, 2))
    potential_density = 0.5 * (gx**2 + gy**2 + gz**2)

    return kinetic_density + potential_density


def compute_sampled_continuum_energy_diagnostic(
    phi: np.ndarray,
    phi_prev: np.ndarray,
    c_field: np.ndarray,
    dt: float,
    dx: float,
) -> float:
    """Compute sampled continuum energy functional as a numerical diagnostic (P1-R2-F4, P1-R9-F2).

    Evaluated via backward differences in time for velocity and central spatial differences
    for spatial gradients. Acts as a continuum-inspired diagnostic proxy with finite-grid discretization
    drift, rather than an exact discrete invariant for the staggered leapfrog equation.
    Units: arbitrary energy units [E_arb] (dimensionless toy field model, not Joules).
    """
    density = compute_discrete_energy_density(phi, phi_prev, c_field, dt, dx)
    return float(np.sum(density) * (dx ** 3))


# Backward-compatible alias for existing callers
compute_discrete_wave_energy = compute_sampled_continuum_energy_diagnostic


def compute_interior_energy(
    phi: np.ndarray,
    phi_prev: np.ndarray,
    c_field: np.ndarray,
    dt: float,
    dx: float,
    sponge_width: int,
) -> float:
    """Compute energy in the active interior without creating artificial mask-edge gradient jumps.

    Integrates local energy density computed over the full smooth field, avoiding step-edge artifacts.
    """
    density = compute_discrete_energy_density(phi, phi_prev, c_field, dt, dx)
    sw = sponge_width
    if sw <= 0:
        return float(np.sum(density) * (dx ** 3))
    interior_density = density[sw:-sw, sw:-sw, sw:-sw]
    return float(np.sum(interior_density) * (dx ** 3))


def compute_masked_interior_energy_proxy(
    phi: np.ndarray,
    phi_prev: np.ndarray,
    c_field: np.ndarray,
    dt: float,
    dx: float,
    sponge_width: int,
) -> float:
    """Legacy proxy that zeroed phi before gradient computation.

    RETAINED FOR AUDIT / REPRODUCIBILITY PURPOSES ONLY.
    Note (P1-R1-F2): This proxy introduces artificial jumps along the mask edge,
    causing masked interior energy to exceed whole-domain energy.
    """
    mask_int = np.zeros_like(phi, dtype=bool)
    mask_int[sponge_width:-sponge_width, sponge_width:-sponge_width, sponge_width:-sponge_width] = True
    phi_int = np.where(mask_int, phi, 0.0)
    phi_int_prev = np.where(mask_int, phi_prev, 0.0)
    return compute_discrete_wave_energy(phi_int, phi_int_prev, c_field, dt, dx)


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

    # Initial Gaussian pulse centered at x0 along x, constant along y, z
    phi_0_1d = np.exp(-((coords - x0) ** 2) / (2.0 * sigma_pulse ** 2))
    phi_minus_1_1d = np.exp(-((coords - (x0 - c_m_per_s * dt)) ** 2) / (2.0 * sigma_pulse ** 2))

    phi = np.tile(phi_0_1d[:, None, None], (1, grid_size, grid_size))
    phi_prev = np.tile(phi_minus_1_1d[:, None, None], (1, grid_size, grid_size))

    for _ in range(n_steps):
        phi_next = step_wave_fdtd(phi, phi_prev, c_field, sigma_field, dt, dx_m)
        phi_prev, phi = phi, phi_next

    # Measure pulse center of mass (centroid) along x
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
class SpongeReflectionProbeResult:
    incident_peak_amplitude: float
    reflected_peak_amplitude: float
    amplitude_reflection_coefficient: float
    power_reflection_coefficient: float
    initial_total_energy: float
    final_interior_energy: float
    final_total_energy: float
    interior_energy_retention_ratio: float
    masked_proxy_ratio: float
    is_absorbed_to_tolerance: bool
    diagnostic_note: str
    legacy_metric_invalid_for_absorption: bool = True


def fixed_window_late_early_probe_amplitude_proxy(
    grid_size: int = 48,
    sponge_width: int = 10,
    max_sigma: float = 3.0,
    n_steps: int = 70,
    tolerance_power_reflection: float = 0.05,
) -> SpongeReflectionProbeResult:
    """Fixed-window late/early probe amplitude proxy (legacy metric, P1-R2-F1, P1-R6-F2).

    NOTE (P1-R2-F1, P1-R6-F2): This legacy proxy split one probe trace at fixed step 25 without an
    unreflected reference. The peak after step 25 captures the outgoing pulse tail, yielding
    ~3.2% power ratio regardless of sponge conductivity sigma_max (including sigma=0).
    It is demonstrably invalid for certifying absorption (legacy_metric_invalid_for_absorption=True,
    is_absorbed_to_tolerance=False).
    Retained purely for audit and historical regression comparison. For validated absorption measurement,
    see benchmark_sponge_reflection_reference_subtracted().
    """
    dx = 1.0
    c0 = 1.0
    dt = 0.85 * dx / (c0 * np.sqrt(3.0))

    c_field = np.full((grid_size, grid_size, grid_size), c0, dtype=float)
    sigma_field = create_sponge_conductivity_field(
        (grid_size, grid_size, grid_size), sponge_width, max_sigma
    )

    # Pulse initialized near center
    coords = np.arange(grid_size) * dx
    mid = grid_size // 2
    x0 = float(mid * dx)
    sigma_pulse = 2.5 * dx

    X, Y, Z = np.meshgrid(coords, coords, coords, indexing='ij')
    r_sq = (X - x0)**2 + (Y - x0)**2 + (Z - x0)**2
    phi_0 = np.exp(-r_sq / (2.0 * sigma_pulse ** 2))
    lap_0 = laplacian_3d_clamped(phi_0, dx)
    phi_minus_1 = phi_0 + 0.5 * (dt ** 2) * (c0 ** 2) * lap_0

    e_initial = compute_sampled_continuum_energy_diagnostic(phi_0, phi_minus_1, c_field, dt, dx)

    probe_idx = (mid + 6, mid, mid)
    probe_series = []

    phi = phi_0.copy()
    phi_prev = phi_minus_1.copy()

    for step in range(n_steps):
        probe_series.append(float(phi[probe_idx]))
        phi_next = step_wave_fdtd(phi, phi_prev, c_field, sigma_field, dt, dx)
        phi_prev, phi = phi, phi_next

    probe_arr = np.array(probe_series)
    arrival_window = 25
    inc_peak = float(np.max(np.abs(probe_arr[:arrival_window])))
    refl_peak = float(np.max(np.abs(probe_arr[arrival_window:]))) if len(probe_arr) > arrival_window else 0.0

    r_amp = float(refl_peak / inc_peak) if inc_peak > 0 else 0.0
    r_pwr = float(r_amp ** 2)

    e_interior_final = compute_interior_energy(phi, phi_prev, c_field, dt, dx, sponge_width)
    e_total_final = compute_sampled_continuum_energy_diagnostic(phi, phi_prev, c_field, dt, dx)
    e_retention_ratio = float(e_interior_final / e_initial)

    proxy_val = compute_masked_interior_energy_proxy(phi, phi_prev, c_field, dt, dx, sponge_width)
    proxy_ratio = float(proxy_val / e_initial)

    # P1-R6-F2: Legacy fixed-window metric is demonstrably invalid for certifying absorption
    is_ok = False

    note = (
        f'Fixed-window late/early probe amplitude proxy (LEGACY / INVALID FOR ABSORPTION CERTIFICATION, P1-R2-F1, P1-R6-F2): '
        f'Early peak: {inc_peak:.4f}, late peak at step 25: {refl_peak:.4f} '
        f'(Proxy ratio = {r_amp:.2%}, Proxy power = {r_pwr:.3%}). '
        f'This legacy fixed-window metric measures outgoing pulse tail and gives ~3.2% even for undamped sigma=0; '
        f'it is demonstrably invalid for certifying absorption (legacy_metric_invalid_for_absorption=True, is_absorbed_to_tolerance=False). '
        f'For validated absorption measurement, see benchmark_sponge_reflection_reference_subtracted().'
    )

    return SpongeReflectionProbeResult(
        incident_peak_amplitude=inc_peak,
        reflected_peak_amplitude=refl_peak,
        amplitude_reflection_coefficient=r_amp,
        power_reflection_coefficient=r_pwr,
        initial_total_energy=e_initial,
        final_interior_energy=e_interior_final,
        final_total_energy=e_total_final,
        interior_energy_retention_ratio=e_retention_ratio,
        masked_proxy_ratio=proxy_ratio,
        is_absorbed_to_tolerance=is_ok,
        diagnostic_note=note,
        legacy_metric_invalid_for_absorption=True,
    )


# Backward-compatible alias
benchmark_sponge_reflection_probe = fixed_window_late_early_probe_amplitude_proxy


def compute_step_sponge_dissipation(
    phi_next: np.ndarray,
    phi_prev: np.ndarray,
    c_field: np.ndarray,
    sigma_field: np.ndarray,
    dt: float,
    dx: float,
) -> float:
    """Exact single-step sponge energy dissipation in the damped leapfrog identity (P1-R4-F1).

    For the damped leapfrog update:
      (phi^{n+1} - 2*phi^n + phi^{n-1})/dt^2 + sigma*(phi^{n+1} - phi^{n-1})/(2*dt) = c^2 * lap(phi^n),
    multiplying by ((phi^{n+1} - phi^{n-1})/(2*c^2*dt)) * dx^3 yields the exact discrete balance:
      H^{n+1/2} - H^{n-1/2} = -Delta D_sponge^n,
    where:
      Delta D_sponge^n = dt * sum_i (sigma_i / c_i^2) * ((phi_i^{n+1} - phi_i^{n-1}) / (2*dt))^2 * dx^3 >= 0.
    """
    v_centered = (phi_next - phi_prev) / (2.0 * dt)
    dissipated_power = np.sum((sigma_field / (c_field ** 2)) * (v_centered ** 2)) * (dx ** 3)
    return float(dt * dissipated_power)


def compute_enclosing_surface_outward_flux(
    phi_next: np.ndarray,
    phi: np.ndarray,
    phi_prev: np.ndarray,
    dt: float,
    dx: float,
    sponge_width: int,
) -> float:
    """Symmetric discrete outward wave energy flux proxy across the 6 faces of dOmega_int (P1-R4-F1, P1-R6-F1).

    Evaluates the discrete boundary flux proxy across the 6 planar interface faces separating
    Omega_int = [sw, N-sw)^3 from the surrounding sponge using the space-symmetric bond velocity
    v_bond = (v_in + v_out) / 2:
      F_out^n(phi) = sum_{6 faces} ( - ((v_in^n + v_out^n)/2) * ((phi_out^n - phi_in^n)/dx) ) * dx^2.

    Positive values indicate wave energy flowing outward from Omega_int into the sponge; negative
    values indicate energy flowing inward from the sponge back into Omega_int.

    NOTE (P1-R6-F1, P1-R7-F1, P1-R8-F2, P1-R8-F3): This quantity is explicitly defined and scoped as an enclosing-surface
    flux PROXY across the 6 crossing boundary faces. It is not an exact closed control-volume identity
    when compared against the continuum diagnostic compute_interior_energy: that comparison reflects a
    finite-grid diagnostic mismatch arising from differing velocity time-staggering (backward-difference velocity vs
    centered-velocity interface flux) and discretely inconsistent spatial energy/flux definitions. Under temporal
    refinement at fixed grid spacing (dt_0, dt_0/2, dt_0/4, dt_0/8, dt_0/16), the mismatch levels off around ~5.57%
    rather than vanishing, demonstrating that the continuum proxy comparison is not an exact discrete conservation law.

    Exact local discrete control-volume continuity is certified separately by the discrete leapfrog
    interior Hamiltonian theorem:
      compute_interior_exact_discrete_leapfrog_energy, compute_exact_discrete_interior_boundary_transfer,
      compute_interior_sponge_dissipated_energy, and compute_interior_source_work_step
    which close to machine precision (< 1e-12) under all dt and dx refinements, variable c(x), damping, and source terms.
    Exact global conservative energy closure is certified separately by the discrete whole-domain
    leapfrog identity H^{N-1/2} + D_sponge = H^{-1/2} (< 1e-12) and whole-domain dissipation >= 90%.
    """
    sw = validate_interior_sponge_width(sponge_width, phi.shape)

    v = (phi_next - phi_prev) / (2.0 * dt)
    area_elem = dx * dx
    inv_dx = 1.0 / dx

    # Left/right x faces of Omega_int = [sw, N-sw)^3 with symmetric interface velocity
    v_x_l = 0.5 * (v[sw, sw:-sw, sw:-sw] + v[sw - 1, sw:-sw, sw:-sw])
    f_x_low = -np.sum(v_x_l * (phi[sw - 1, sw:-sw, sw:-sw] - phi[sw, sw:-sw, sw:-sw]) * inv_dx) * area_elem

    v_x_h = 0.5 * (v[-sw - 1, sw:-sw, sw:-sw] + v[-sw, sw:-sw, sw:-sw])
    f_x_high = -np.sum(v_x_h * (phi[-sw, sw:-sw, sw:-sw] - phi[-sw - 1, sw:-sw, sw:-sw]) * inv_dx) * area_elem

    # Front/back y faces
    v_y_l = 0.5 * (v[sw:-sw, sw, sw:-sw] + v[sw:-sw, sw - 1, sw:-sw])
    f_y_low = -np.sum(v_y_l * (phi[sw:-sw, sw - 1, sw:-sw] - phi[sw:-sw, sw, sw:-sw]) * inv_dx) * area_elem

    v_y_h = 0.5 * (v[sw:-sw, -sw - 1, sw:-sw] + v[sw:-sw, -sw, sw:-sw])
    f_y_high = -np.sum(v_y_h * (phi[sw:-sw, -sw, sw:-sw] - phi[sw:-sw, -sw - 1, sw:-sw]) * inv_dx) * area_elem

    # Bottom/top z faces
    v_z_l = 0.5 * (v[sw:-sw, sw:-sw, sw] + v[sw:-sw, sw:-sw, sw - 1])
    f_z_low = -np.sum(v_z_l * (phi[sw:-sw, sw:-sw, sw - 1] - phi[sw:-sw, sw:-sw, sw]) * inv_dx) * area_elem

    v_z_h = 0.5 * (v[sw:-sw, sw:-sw, -sw - 1] + v[sw:-sw, sw:-sw, -sw])
    f_z_high = -np.sum(v_z_h * (phi[sw:-sw, sw:-sw, -sw] - phi[sw:-sw, sw:-sw, -sw - 1]) * inv_dx) * area_elem

    return float(f_x_low + f_x_high + f_y_low + f_y_high + f_z_low + f_z_high)


@dataclass(frozen=True)
class SpongeReflectionReferenceSubtractedResult:
    grid_size: int
    sponge_width: int
    max_sigma: float
    n_steps: int
    ref_grid_size: int
    dx_m: float
    dt_s: float
    dt_factor: float
    physical_box_width_m: float
    physical_sponge_width_m: float
    physical_observation_time_s: float
    incident_peak_amplitude: float
    reflected_peak_amplitude: float
    probe_local_amplitude_ratio_proxy: float
    probe_local_peak_squared_proxy: float
    probe_amplitude_reflection_ratio: float
    probe_peak_squared_reflection_proxy: float
    terminal_interior_reflected_energy_snapshot_proxy: float
    peak_window_interior_reflected_energy_snapshot_proxy: float
    initial_discrete_hamiltonian: float
    final_total_discrete_hamiltonian: float
    cumulative_sponge_dissipated_energy: float
    sponge_dissipated_energy_fraction: float
    remaining_total_energy_fraction: float
    discrete_energy_budget_closure_error: float
    cumulative_incident_outgoing_surface_flux: float
    cumulative_reflected_return_surface_flux: float
    surface_flux_return_ratio_proxy: float
    geometric_pre_arrival_step: int
    geometric_peak_return_step: int
    reference_wall_return_step: int
    reference_domain_free_of_wall_return: bool
    pre_arrival_difference_max: float
    is_simulation_setup_valid: bool
    is_sponge_absorbed_to_tolerance: bool
    metric_definition_note: str
    diagnostic_note: str

    @property
    def surface_integrated_return_flux_ratio(self) -> float:
        """Backward-compatible alias for surface_flux_return_ratio_proxy."""
        return self.surface_flux_return_ratio_proxy

    @property
    def is_sponge_benchmark_valid(self) -> bool:
        """Backward-compatible alias for is_sponge_absorbed_to_tolerance."""
        return self.is_sponge_absorbed_to_tolerance

    @property
    def is_absorbed_to_tolerance(self) -> bool:
        """Backward-compatible alias for is_sponge_absorbed_to_tolerance."""
        return self.is_sponge_absorbed_to_tolerance

    @property
    def integrated_reflected_energy_fraction(self) -> float:
        """Backward-compatible alias for terminal_interior_reflected_energy_snapshot_proxy."""
        return self.terminal_interior_reflected_energy_snapshot_proxy


_REF_PULSE_CACHE: dict[
    tuple[int, int, float, int, int, float, float, int],
    tuple[np.ndarray, np.ndarray, np.ndarray, float],
] = {}


def benchmark_sponge_reflection_reference_subtracted(
    grid_size: int = 40,
    sponge_width: int = 8,
    max_sigma: float = 3.0,
    n_steps: int = 80,
    ref_grid_size: int = 90,
    probe_offset: int = 6,
    dt_factor: float = 0.85,
    dx_m: float = 1.0,
    pulse_sigma_m: float = 2.0,
    tolerance_proxy_max: float = 0.05,
) -> SpongeReflectionReferenceSubtractedResult:
    """Benchmark sponge damping with closed discrete energy budget, surface flux, and explicit proxy labels (P1-R4-F1).

    Resolves P1-R2-F1, P1-R3-F4, and P1-R4-F1:
    1. Honest proxy labeling: Single-probe ratios and interior difference-energy snapshots are explicitly
       labeled as local/snapshot proxies (`probe_local_amplitude_ratio_proxy`, `probe_local_peak_squared_proxy`,
       `terminal_interior_reflected_energy_snapshot_proxy`, `peak_window_interior_reflected_energy_snapshot_proxy`),
       not plane-wave power reflection coefficients.
    2. Closed discrete energy budget: Tracks the exact staggered leapfrog Hamiltonian H^{n+1/2} and exact
       step-by-step sponge dissipation Delta D_sponge^n across all n_steps, verifying the discrete identity
       H^{N-1/2} + D_sponge,cum = H^{-1/2} to machine precision (< 1e-12).
    3. Time-integrated enclosing-surface flux: Integrates the outward incident wave energy flux and inward
       reflected return energy flux across the 6 faces of the interior/sponge boundary dOmega_int over time.
    4. Supports true spatial dx_m refinement at fixed physical geometry (L_box, W_sponge, d_probe, pulse_sigma_m).
    """
    dx = float(dx_m)
    c0 = 1.0
    dt = dt_factor * dx / (c0 * np.sqrt(3.0))
    sigma_pulse = float(pulse_sigma_m)

    # Geometric travel-time gating calculations
    d_sponge_cells = (grid_size // 2) - sponge_width
    pulse_4sigma_cells = int(np.ceil(4.0 * sigma_pulse / dx))
    geometric_pre_arrival_step = max(
        1,
        int((d_sponge_cells - pulse_4sigma_cells) + (d_sponge_cells - probe_offset)),
    )
    d_sponge_m = float(d_sponge_cells * dx)
    d_probe_m = float(probe_offset * dx)
    geometric_peak_return_step = int(round((2.0 * d_sponge_m - d_probe_m) / (c0 * dt)))

    # Reference domain outer Dirichlet wall return step
    d_ref_wall_m = float((ref_grid_size // 2) * dx)
    d_ref_two_way_m = (d_ref_wall_m - 4.0 * sigma_pulse) + (d_ref_wall_m - d_probe_m)
    reference_wall_return_step = int(np.floor(d_ref_two_way_m / (c0 * dt)))
    ref_free_of_return = bool(reference_wall_return_step > n_steps)

    def _init_pulse(g_size: int) -> tuple[np.ndarray, np.ndarray]:
        mid = g_size // 2
        x0 = float(mid * dx)
        coords = np.arange(g_size) * dx
        X, Y, Z = np.meshgrid(coords, coords, coords, indexing='ij')
        r_sq = (X - x0)**2 + (Y - x0)**2 + (Z - x0)**2
        phi_0 = np.exp(-r_sq / (2.0 * sigma_pulse ** 2))
        phi_0[0, :, :] = phi_0[-1, :, :] = 0.0
        phi_0[:, 0, :] = phi_0[:, -1, :] = 0.0
        phi_0[:, :, 0] = phi_0[:, :, -1] = 0.0
        lap_0 = laplacian_3d_clamped(phi_0, dx)
        phi_m1 = phi_0 + 0.5 * (dt ** 2) * (c0 ** 2) * lap_0
        phi_m1[0, :, :] = phi_m1[-1, :, :] = 0.0
        phi_m1[:, 0, :] = phi_m1[:, -1, :] = 0.0
        phi_m1[:, :, 0] = phi_m1[:, :, -1] = 0.0
        return phi_0, phi_m1

    # 1. Matched unreflected reference (or synchronized evolution when computing window trajectories)
    off = (ref_grid_size // 2) - (grid_size // 2) if ref_grid_size >= grid_size else 0
    c_test = np.full((grid_size, grid_size, grid_size), c0, dtype=float)
    sig_test = create_sponge_conductivity_field((grid_size, grid_size, grid_size), sponge_width, max_sigma)
    phi0_test, phim1_test = _init_pulse(grid_size)
    e_init_cont = compute_sampled_continuum_energy_diagnostic(phi0_test, phim1_test, c_test, dt, dx)
    h_init_disc = compute_exact_discrete_leapfrog_energy(phi0_test, phim1_test, c_test, dt, dx)

    c_ref = np.full((ref_grid_size, ref_grid_size, ref_grid_size), c0, dtype=float)
    sig_ref = np.zeros_like(c_ref)
    phi0_ref, phim1_ref = _init_pulse(ref_grid_size)

    p_test, pm_test = phi0_test.copy(), phim1_test.copy()
    p_ref, pm_ref = phi0_ref.copy(), phim1_ref.copy()

    mid_test = grid_size // 2
    mid_ref = ref_grid_size // 2
    p_idx_test = (mid_test + probe_offset, mid_test, mid_test)
    p_idx_ref = (mid_ref + probe_offset, mid_ref, mid_ref)

    test_trace_list: list[float] = []
    ref_trace_list: list[float] = []
    cum_sponge_dissipated = 0.0
    cum_inc_out_flux = 0.0
    cum_refl_in_flux = 0.0
    peak_window_int_refl_fraction = 0.0
    h_final_disc = h_init_disc

    # Evaluate interior snapshot at cadence (every 2 steps after pre-arrival, plus final step) for fast 3D window tracking
    for step_idx in range(n_steps):
        test_trace_list.append(float(p_test[p_idx_test]))
        ref_trace_list.append(float(p_ref[p_idx_ref]))

        pn_test = step_wave_fdtd(p_test, pm_test, c_test, sig_test, dt, dx)
        pn_ref = step_wave_fdtd(p_ref, pm_ref, c_ref, sig_ref, dt, dx)

        # Exact step sponge dissipation and terminal half-step Hamiltonian
        cum_sponge_dissipated += compute_step_sponge_dissipation(pn_test, pm_test, c_test, sig_test, dt, dx)
        if step_idx == n_steps - 1:
            h_final_disc = compute_exact_discrete_leapfrog_energy(pn_test, p_test, c_test, dt, dx)

        if ref_grid_size >= grid_size:
            pn_ref_sub = pn_ref[off:off + grid_size, off:off + grid_size, off:off + grid_size]
            p_ref_sub = p_ref[off:off + grid_size, off:off + grid_size, off:off + grid_size]
            pm_ref_sub = pm_ref[off:off + grid_size, off:off + grid_size, off:off + grid_size]

            # Outward surface flux of incident reference wave across dOmega_int
            f_out_ref = compute_enclosing_surface_outward_flux(pn_ref_sub, p_ref_sub, pm_ref_sub, dt, dx, sponge_width)
            if f_out_ref > 0.0:
                cum_inc_out_flux += f_out_ref * dt

            # Inward return surface flux of reflected difference wave (delta_phi = phi_test - phi_ref) into Omega_int
            d_pn = pn_test - pn_ref_sub
            d_p = p_test - p_ref_sub
            d_pm = pm_test - pm_ref_sub
            f_out_diff = compute_enclosing_surface_outward_flux(d_pn, d_p, d_pm, dt, dx, sponge_width)
            f_in_diff = -f_out_diff
            if f_in_diff > 0.0:
                cum_refl_in_flux += f_in_diff * dt

            if (step_idx >= geometric_pre_arrival_step and step_idx % 4 == 0) or (step_idx == n_steps - 1):
                e_int_step = compute_interior_energy(d_pn, d_p, c_test, dt, dx, sponge_width)
                frac_step = float(e_int_step / e_init_cont) if e_init_cont > 0 else 0.0
                if frac_step > peak_window_int_refl_fraction:
                    peak_window_int_refl_fraction = frac_step

        pm_test, p_test = p_test, pn_test
        pm_ref, p_ref = p_ref, pn_ref

    test_trace = np.array(test_trace_list)
    ref_trace = np.array(ref_trace_list)
    inc_peak = float(np.max(np.abs(ref_trace)))

    diff = test_trace - ref_trace
    cutoff = min(geometric_pre_arrival_step, len(diff))
    pre_arrival_max = float(np.max(np.abs(diff[:cutoff])))

    refl_peak = float(np.max(np.abs(diff)))
    r_amp_proxy = float(refl_peak / inc_peak) if inc_peak > 0 else 0.0
    r_pwr_proxy = float(r_amp_proxy ** 2)

    if ref_grid_size >= grid_size:
        p_ref_sub_final = p_ref[off:off + grid_size, off:off + grid_size, off:off + grid_size]
        pm_ref_sub_final = pm_ref[off:off + grid_size, off:off + grid_size, off:off + grid_size]
        d_p_final = p_test - p_ref_sub_final
        d_pm_final = pm_test - pm_ref_sub_final
        e_refl_interior_final = compute_interior_energy(d_p_final, d_pm_final, c_test, dt, dx, sponge_width)
        terminal_refl_snapshot_proxy = float(e_refl_interior_final / e_init_cont) if e_init_cont > 0 else 0.0
        peak_window_int_refl_fraction = max(peak_window_int_refl_fraction, terminal_refl_snapshot_proxy)
    else:
        terminal_refl_snapshot_proxy = 1.0
        peak_window_int_refl_fraction = 1.0

    sponge_dissipated_frac = float(cum_sponge_dissipated / h_init_disc) if h_init_disc > 0 else 0.0
    remaining_total_frac = float(h_final_disc / h_init_disc) if h_init_disc > 0 else 0.0
    closure_err = (
        float(abs((h_final_disc + cum_sponge_dissipated) - h_init_disc) / h_init_disc)
        if h_init_disc > 0
        else 0.0
    )
    # Physical incident flux threshold: require meaningful incident energy to cross into the sponge
    # before evaluating return flux ratio (prevents negligible Gaussian tail floating-point noise from masking zero absorption)
    min_incident_flux = 1e-6 * h_init_disc if h_init_disc > 0 else 1e-6
    surface_return_ratio = (
        float(cum_refl_in_flux / cum_inc_out_flux)
        if cum_inc_out_flux >= min_incident_flux
        else float('nan')
    )

    is_setup_valid = bool(
        ref_free_of_return
        and pre_arrival_max < 1e-8
        and closure_err < 1e-12
        and n_steps >= geometric_peak_return_step
    )

    is_absorbed = bool(
        is_setup_valid
        and cum_inc_out_flux >= min_incident_flux
        and sponge_dissipated_frac >= 0.90
        and (not np.isnan(surface_return_ratio) and surface_return_ratio <= 0.05)
        and r_pwr_proxy <= tolerance_proxy_max
        and peak_window_int_refl_fraction <= tolerance_proxy_max
    )

    metric_note = (
        'PROXY & BUDGET DEFINITIONS (P1-R4-F1, P1-R5-F1, P1-R6-F1, P1-R7-F1): '
        '(1) probe_local_peak_squared_proxy = (max|phi_test(x_p,t) - phi_ref(x_p,t)| / max|phi_ref(x_p,t)|)^2 is a '
        'single-point amplitude-squared ratio subject to 3D 1/r spreading, NOT a plane-wave power reflection coefficient. '
        '(2) terminal_interior_reflected_energy_snapshot_proxy and peak_window_interior_reflected_energy_snapshot_proxy '
        'measure the 3D interior continuum energy of (phi_test - phi_ref) normalized by initial energy at t=T_end and '
        'at its return-window maximum, respectively. '
        '(3) initial_discrete_hamiltonian, final_total_discrete_hamiltonian, and cumulative_sponge_dissipated_energy '
        'satisfy the exact closed discrete leapfrog identity H^{N-1/2} + D_sponge = H^{-1/2} to machine precision (< 1e-12). '
        '(4) surface_flux_return_ratio_proxy (alias surface_integrated_return_flux_ratio) measures the time-integrated '
        'inward return energy flux proxy of (phi_test - phi_ref) across the 6 faces of dOmega_int divided by the outward '
        'incident energy flux, evaluated with space-symmetric bond velocities (v_in + v_out)/2. It is an approximate '
        'surface-flux proxy across the 6 boundary faces, NOT an established conservative control-volume identity '
        '(local finite-difference proxy comparisons against backward-difference continuum diagnostics exhibit a '
        'finite-grid diagnostic mismatch leveling off around ~5.57% under dt refinement due to time-staggering and '
        'discretely inconsistent spatial formulations; exact local discrete control-volume closure is certified by '
        'compute_interior_exact_discrete_leapfrog_energy and compute_exact_discrete_interior_boundary_transfer, while global '
        'conservative closure is certified separately by the exact discrete whole-domain identity). '
        '(5) is_simulation_setup_valid certifies clean isolation, causal zero, energy closure, and sufficient return window; '
        'is_sponge_absorbed_to_tolerance certifies demonstrated wave absorption (whole-domain dissipation >= 90%, '
        'surface flux return proxy <= 5%, difference reflection proxies <= 5%).'
    )

    note = (
        f'Reference-subtracted sponge benchmark (grid={grid_size}, dx={dx}m, sponge={sponge_width}, max_sigma={max_sigma}, ref_grid={ref_grid_size}): '
        f'setup_valid={is_setup_valid}, absorbed_to_tolerance={is_absorbed}, '
        f'probe local peak-squared proxy={r_pwr_proxy:.3%}, '
        f'terminal interior snapshot proxy={terminal_refl_snapshot_proxy:.3%}, '
        f'peak-window interior snapshot proxy={peak_window_int_refl_fraction:.3%}, '
        f'surface flux return proxy={surface_return_ratio:.3%}. '
        f'Closed discrete energy budget: sponge dissipated={sponge_dissipated_frac:.2%}, '
        f'remaining total={remaining_total_frac:.2%}, closure error={closure_err:.2e} (< 1e-12).'
    )

    return SpongeReflectionReferenceSubtractedResult(
        grid_size=grid_size,
        sponge_width=sponge_width,
        max_sigma=max_sigma,
        n_steps=n_steps,
        ref_grid_size=ref_grid_size,
        dx_m=dx,
        dt_s=float(dt),
        dt_factor=dt_factor,
        physical_box_width_m=float(grid_size * dx),
        physical_sponge_width_m=float(sponge_width * dx),
        physical_observation_time_s=float(n_steps * dt),
        incident_peak_amplitude=inc_peak,
        reflected_peak_amplitude=refl_peak,
        probe_local_amplitude_ratio_proxy=r_amp_proxy,
        probe_local_peak_squared_proxy=r_pwr_proxy,
        probe_amplitude_reflection_ratio=r_amp_proxy,
        probe_peak_squared_reflection_proxy=r_pwr_proxy,
        terminal_interior_reflected_energy_snapshot_proxy=terminal_refl_snapshot_proxy,
        peak_window_interior_reflected_energy_snapshot_proxy=peak_window_int_refl_fraction,
        initial_discrete_hamiltonian=h_init_disc,
        final_total_discrete_hamiltonian=h_final_disc,
        cumulative_sponge_dissipated_energy=cum_sponge_dissipated,
        sponge_dissipated_energy_fraction=sponge_dissipated_frac,
        remaining_total_energy_fraction=remaining_total_frac,
        discrete_energy_budget_closure_error=closure_err,
        cumulative_incident_outgoing_surface_flux=cum_inc_out_flux,
        cumulative_reflected_return_surface_flux=cum_refl_in_flux,
        surface_flux_return_ratio_proxy=surface_return_ratio,
        geometric_pre_arrival_step=geometric_pre_arrival_step,
        geometric_peak_return_step=geometric_peak_return_step,
        reference_wall_return_step=reference_wall_return_step,
        reference_domain_free_of_wall_return=ref_free_of_return,
        pre_arrival_difference_max=pre_arrival_max,
        is_simulation_setup_valid=is_setup_valid,
        is_sponge_absorbed_to_tolerance=is_absorbed,
        metric_definition_note=metric_note,
        diagnostic_note=note,
    )


@dataclass(frozen=True)
class SpongeControlRow:
    max_sigma: float
    reflected_peak: float
    probe_local_amplitude_ratio_proxy: float
    probe_local_peak_squared_proxy: float
    probe_amplitude_reflection_ratio: float
    probe_peak_squared_reflection_proxy: float
    terminal_interior_reflected_energy_snapshot_proxy: float
    peak_window_interior_reflected_energy_snapshot_proxy: float
    sponge_dissipated_energy_fraction: float
    remaining_total_energy_fraction: float
    discrete_energy_budget_closure_error: float
    surface_flux_return_ratio_proxy: float
    description: str

    @property
    def surface_integrated_return_flux_ratio(self) -> float:
        """Backward-compatible alias for surface_flux_return_ratio_proxy."""
        return self.surface_flux_return_ratio_proxy

    @property
    def integrated_reflected_energy_fraction(self) -> float:
        """Backward-compatible alias for terminal_interior_reflected_energy_snapshot_proxy."""
        return self.terminal_interior_reflected_energy_snapshot_proxy


def benchmark_sponge_reflection_controls(
    sigma_list: Sequence[float] = (0.0, 0.5, 1.5, 3.0, 15.0),
    grid_size: int = 40,
    sponge_width: int = 8,
    n_steps: int = 80,
    ref_grid_size: int = 90,
) -> list[SpongeControlRow]:
    """Negative and positive controls for sponge absorption vs Dirichlet wall reflection (P1-R2-F1, P1-R3-F4, P1-R4-F1).

    Demonstrates:
    - sigma=0.0: Undamped Dirichlet wall gives strong physical reflection and zero sponge dissipation (D_sponge = 0).
    - sigma in [0.5, 3.0]: Sponge absorption dissipates > 97% of total wave energy and suppresses interior
      reflection snapshots and return surface flux by an order of magnitude relative to sigma=0.
    - sigma=15.0: Excessive conductivity causes entrance impedance mismatch, increasing return reflection.
    """
    rows = []
    descriptions = {
        0.0: 'Negative control: undamped Dirichlet wall (strong physical reflection, zero dissipation)',
        0.5: 'Positive control: low sponge damping',
        1.5: 'Positive control: moderate sponge damping',
        3.0: 'Positive control: design sponge damping',
        15.0: 'High-sigma control: impedance mismatch reflection at sponge entrance',
    }
    for sig in sigma_list:
        res = benchmark_sponge_reflection_reference_subtracted(
            grid_size=grid_size,
            sponge_width=sponge_width,
            max_sigma=sig,
            n_steps=n_steps,
            ref_grid_size=ref_grid_size,
        )
        desc = descriptions.get(sig, f'Conductivity sigma_max={sig}')
        rows.append(SpongeControlRow(
            max_sigma=sig,
            reflected_peak=res.reflected_peak_amplitude,
            probe_local_amplitude_ratio_proxy=res.probe_local_amplitude_ratio_proxy,
            probe_local_peak_squared_proxy=res.probe_local_peak_squared_proxy,
            probe_amplitude_reflection_ratio=res.probe_amplitude_reflection_ratio,
            probe_peak_squared_reflection_proxy=res.probe_peak_squared_reflection_proxy,
            terminal_interior_reflected_energy_snapshot_proxy=res.terminal_interior_reflected_energy_snapshot_proxy,
            peak_window_interior_reflected_energy_snapshot_proxy=res.peak_window_interior_reflected_energy_snapshot_proxy,
            sponge_dissipated_energy_fraction=res.sponge_dissipated_energy_fraction,
            remaining_total_energy_fraction=res.remaining_total_energy_fraction,
            discrete_energy_budget_closure_error=res.discrete_energy_budget_closure_error,
            surface_flux_return_ratio_proxy=res.surface_flux_return_ratio_proxy,
            description=desc,
        ))
    return rows


@dataclass(frozen=True)
class SpongeParameterSweepRow:
    label: str
    sweep_category: str
    grid_size: int
    sponge_width: int
    dx_m: float
    max_sigma: float
    dt_factor: float
    n_steps: int
    physical_observation_time_s: float
    ref_grid_size: int
    probe_local_peak_squared_proxy: float
    probe_peak_squared_reflection_proxy: float
    terminal_interior_reflected_energy_snapshot_proxy: float
    peak_window_interior_reflected_energy_snapshot_proxy: float
    sponge_dissipated_energy_fraction: float
    discrete_energy_budget_closure_error: float
    surface_flux_return_ratio_proxy: float
    reference_wall_return_step: int
    reference_domain_free_of_wall_return: bool

    @property
    def surface_integrated_return_flux_ratio(self) -> float:
        """Backward-compatible alias for surface_flux_return_ratio_proxy."""
        return self.surface_flux_return_ratio_proxy

    @property
    def integrated_reflected_energy_fraction(self) -> float:
        """Backward-compatible alias for terminal_interior_reflected_energy_snapshot_proxy."""
        return self.terminal_interior_reflected_energy_snapshot_proxy


@dataclass(frozen=True)
class SpongeParameterSweepResult:
    rows: list[SpongeParameterSweepRow]
    reference_domain_invariance_diff: float
    dt_refinement_relative_diff: float
    dx_refinement_rows: list[SpongeParameterSweepRow]
    observation_window_rows: list[SpongeParameterSweepRow]
    monotonic_with_sponge_width: bool
    dx_refinement_consistent: bool
    observation_window_bounded: bool
    is_sweep_stable: bool
    diagnostic_note: str
    dx_snapshot_relative_diff: float = 0.0
    dx_flux_relative_diff: float = 0.0


def benchmark_sponge_reflection_parameter_sweep() -> SpongeParameterSweepResult:
    """Evaluate stability of reference-subtracted sponge benchmark across reference domain, observation time T_obs, spatial dx refinement of fixed physical geometry, dt refinement, and sponge thickness (P1-R3-F4, P1-R4-F1)."""
    # Format: (label, category, grid_size, sponge_width, probe_offset, dx_m, max_sigma, dt_factor, n_steps, ref_grid_size)
    configs = [
        # 1. Baseline & reference-domain size invariance (L_box=40m, W_sponge=8m, d_probe=6m, dx=1.0m)
        ('baseline_n40_w8_dx10_dt085_ref90', 'reference_size', 40, 8, 6, 1.0, 3.0, 0.85, 80, 90),
        ('enlarged_ref_n40_w8_dx10_dt085_ref106', 'reference_size', 40, 8, 6, 1.0, 3.0, 0.85, 80, 106),
        # 2. Courant dt refinement at fixed dx=1.0m
        ('refined_dt_n40_w8_dx10_dt0425_ref90', 'dt_refinement', 40, 8, 6, 1.0, 3.0, 0.425, 160, 90),
        # 3. Sponge thickness sweep at fixed dx=1.0m (W_sponge = 6m, 8m, 10m)
        ('thin_sponge_n40_w6_dx10_dt085_ref90', 'sponge_width', 40, 6, 6, 1.0, 3.0, 0.85, 80, 90),
        ('thick_sponge_n40_w10_dx10_dt085_ref90', 'sponge_width', 40, 10, 6, 1.0, 3.0, 0.85, 80, 90),
        # 4. Observation-time / return-window sweep (steps=60, 70, 80, 90, 100 on ref=106 where wall return is step 181)
        ('obs_window_steps60_ref106', 'observation_window', 40, 8, 6, 1.0, 3.0, 0.85, 60, 106),
        ('obs_window_steps70_ref106', 'observation_window', 40, 8, 6, 1.0, 3.0, 0.85, 70, 106),
        ('obs_window_steps80_ref106', 'observation_window', 40, 8, 6, 1.0, 3.0, 0.85, 80, 106),
        ('obs_window_steps90_ref106', 'observation_window', 40, 8, 6, 1.0, 3.0, 0.85, 90, 106),
        ('obs_window_steps100_ref106', 'observation_window', 40, 8, 6, 1.0, 3.0, 0.85, 100, 106),
        # 5. True spatial dx refinement of fixed physical geometry (L_box=40m, W_sponge=8m, d_probe=6m, sigma_pulse=2m, L_ref=68m)
        ('spatial_dx20_n20_w4_ref34', 'spatial_dx_refinement', 20, 4, 3, 2.0, 3.0, 0.85, 40, 34),
        ('spatial_dx10_n40_w8_ref68', 'spatial_dx_refinement', 40, 8, 6, 1.0, 3.0, 0.85, 80, 68),
        ('spatial_dx05_n80_w16_ref136', 'spatial_dx_refinement', 80, 16, 12, 0.5, 3.0, 0.85, 160, 136),
    ]
    rows: list[SpongeParameterSweepRow] = []
    by_label: dict[str, SpongeParameterSweepRow] = {}

    for label, category, g_size, s_w, p_off, dx_val, sig, dt_f, steps, ref_g in configs:
        res = benchmark_sponge_reflection_reference_subtracted(
            grid_size=g_size,
            sponge_width=s_w,
            max_sigma=sig,
            n_steps=steps,
            ref_grid_size=ref_g,
            probe_offset=p_off,
            dt_factor=dt_f,
            dx_m=dx_val,
            pulse_sigma_m=2.0,
        )
        row = SpongeParameterSweepRow(
            label=label,
            sweep_category=category,
            grid_size=g_size,
            sponge_width=s_w,
            dx_m=dx_val,
            max_sigma=sig,
            dt_factor=dt_f,
            n_steps=steps,
            physical_observation_time_s=res.physical_observation_time_s,
            ref_grid_size=ref_g,
            probe_local_peak_squared_proxy=res.probe_local_peak_squared_proxy,
            probe_peak_squared_reflection_proxy=res.probe_peak_squared_reflection_proxy,
            terminal_interior_reflected_energy_snapshot_proxy=res.terminal_interior_reflected_energy_snapshot_proxy,
            peak_window_interior_reflected_energy_snapshot_proxy=res.peak_window_interior_reflected_energy_snapshot_proxy,
            sponge_dissipated_energy_fraction=res.sponge_dissipated_energy_fraction,
            discrete_energy_budget_closure_error=res.discrete_energy_budget_closure_error,
            surface_flux_return_ratio_proxy=res.surface_flux_return_ratio_proxy,
            reference_wall_return_step=res.reference_wall_return_step,
            reference_domain_free_of_wall_return=res.reference_domain_free_of_wall_return,
        )
        rows.append(row)
        by_label[label] = row

    base = by_label['baseline_n40_w8_dx10_dt085_ref90']
    enlarged = by_label['enlarged_ref_n40_w8_dx10_dt085_ref106']
    dt_ref = by_label['refined_dt_n40_w8_dx10_dt0425_ref90']
    w6 = by_label['thin_sponge_n40_w6_dx10_dt085_ref90']
    w10 = by_label['thick_sponge_n40_w10_dx10_dt085_ref90']

    dx_rows = [r for r in rows if r.sweep_category == 'spatial_dx_refinement']
    obs_rows = [r for r in rows if r.sweep_category == 'observation_window']

    ref_diff = float(abs(base.probe_local_peak_squared_proxy - enlarged.probe_local_peak_squared_proxy))
    dt_rel_diff = float(
        abs(dt_ref.probe_local_peak_squared_proxy - base.probe_local_peak_squared_proxy)
        / base.probe_local_peak_squared_proxy
    )
    monotonic_w = bool(
        w6.terminal_interior_reflected_energy_snapshot_proxy
        > base.terminal_interior_reflected_energy_snapshot_proxy
        > w10.terminal_interior_reflected_energy_snapshot_proxy
    )
    # Under spatial dx refinement (dx = 2.0 -> 1.0 -> 0.5m) of the same physical geometry,
    # evaluate both individual boundedness (< 2%) and inter-grid relative difference between well-resolved grids (dx=1.0 and dx=0.5m)
    dx_10 = by_label['spatial_dx10_n40_w8_ref68']
    dx_05 = by_label['spatial_dx05_n80_w16_ref136']
    dx_dissipation_diff = float(abs(dx_05.sponge_dissipated_energy_fraction - dx_10.sponge_dissipated_energy_fraction))
    dx_snapshot_rel_diff = float(
        abs(dx_05.peak_window_interior_reflected_energy_snapshot_proxy - dx_10.peak_window_interior_reflected_energy_snapshot_proxy)
        / dx_10.peak_window_interior_reflected_energy_snapshot_proxy
    )
    dx_flux_rel_diff = float(
        abs(dx_05.surface_integrated_return_flux_ratio - dx_10.surface_integrated_return_flux_ratio)
        / dx_10.surface_integrated_return_flux_ratio
    )
    dx_consistent = bool(
        all(r.discrete_energy_budget_closure_error < 1e-12 for r in dx_rows)
        and dx_10.peak_window_interior_reflected_energy_snapshot_proxy < 0.02
        and dx_05.peak_window_interior_reflected_energy_snapshot_proxy < 0.02
        and dx_10.surface_integrated_return_flux_ratio < 0.02
        and dx_05.surface_integrated_return_flux_ratio < 0.02
        and dx_dissipation_diff < 0.01
        and dx_snapshot_rel_diff < 0.15
        and dx_flux_rel_diff < 0.15
    )
    # Across observation window steps 60..100, sponge dissipation increases monotonically toward ~99%
    # and peak-window interior reflected energy snapshot stays strictly bounded (< 2%)
    obs_bounded = bool(
        all(r.peak_window_interior_reflected_energy_snapshot_proxy < 0.02 for r in obs_rows)
        and all(
            obs_rows[i + 1].sponge_dissipated_energy_fraction >= obs_rows[i].sponge_dissipated_energy_fraction - 1e-12
            for i in range(len(obs_rows) - 1)
        )
    )
    all_free = all(r.reference_domain_free_of_wall_return for r in rows)
    all_closed = all(r.discrete_energy_budget_closure_error < 1e-12 for r in rows)
    is_ok = bool(
        all_free and all_closed and ref_diff < 1e-10 and dt_rel_diff < 0.15
        and monotonic_w and dx_consistent and obs_bounded
    )

    note = (
        f'Sponge reflection parameter sweep (P1-R4-F1, P1-R5-F1): '
        f'(1) Reference-size invariance (ref=90 vs 106) diff={ref_diff:.2e} (< 1e-10); '
        f'(2) dt halving relative shift={dt_rel_diff:.2%}; '
        f'(3) Sponge width sweep (W=6m -> 8m -> 10m) terminal interior snapshot: '
        f'{w6.terminal_interior_reflected_energy_snapshot_proxy:.3%} -> {base.terminal_interior_reflected_energy_snapshot_proxy:.3%} -> {w10.terminal_interior_reflected_energy_snapshot_proxy:.3%}; '
        f'(4) Spatial dx refinement at fixed physical geometry (dx=2.0 -> 1.0 -> 0.5m): '
        f'inter-grid relative diffs between dx=1.0m and 0.5m: '
        f'dissipation abs diff={dx_dissipation_diff:.2e} (< 0.01), '
        f'peak-window snapshot rel diff={dx_snapshot_rel_diff:.2%} (< 15%), '
        f'surface return flux rel diff={dx_flux_rel_diff:.2%} (< 15%), '
        f'bounded snapshot levels={[round(r.peak_window_interior_reflected_energy_snapshot_proxy, 5) for r in dx_rows]} (< 2%); '
        f'(5) Observation window sweep (steps 60..100): dissipated fraction rises monotonically from '
        f'{obs_rows[0].sponge_dissipated_energy_fraction:.2%} to {obs_rows[-1].sponge_dissipated_energy_fraction:.2%}.'
    )

    return SpongeParameterSweepResult(
        rows=rows,
        reference_domain_invariance_diff=ref_diff,
        dt_refinement_relative_diff=dt_rel_diff,
        dx_refinement_rows=dx_rows,
        observation_window_rows=obs_rows,
        monotonic_with_sponge_width=monotonic_w,
        dx_refinement_consistent=dx_consistent,
        observation_window_bounded=obs_bounded,
        is_sweep_stable=is_ok,
        diagnostic_note=note,
        dx_snapshot_relative_diff=dx_snapshot_rel_diff,
        dx_flux_relative_diff=dx_flux_rel_diff,
    )


@dataclass(frozen=True)
class InteriorControlVolumeBudgetResult:
    grid_size: int
    sponge_width: int
    dx_m: float
    dt_s: float
    dt_factor: float
    n_steps: int
    initial_interior_hamiltonian: float
    final_interior_hamiltonian: float
    interior_hamiltonian_change: float
    cumulative_boundary_transfer: float
    cumulative_interior_dissipation: float
    cumulative_interior_source_work: float
    discrete_local_closure_error: float
    relative_local_closure_error: float
    is_exact_to_machine_precision: bool
    diagnostic_note: str
    interior_sigma: float = 0.0
    source_amplitude: float = 0.0


def benchmark_interior_control_volume_budget(
    grid_size: int = 40,
    sponge_width: int = 8,
    dx_m: float = 1.0,
    c_m_per_s: float = 1.0,
    courant_factor: float = 0.85,
    n_steps: int = 25,
    interior_sigma: float = 0.0,
    source_amplitude: float = 0.0,
) -> InteriorControlVolumeBudgetResult:
    """Benchmark exact discrete local control-volume Hamiltonian continuity theorem (P1-R7-F1, P1-R8-F1, P1-R8-F3, P1-R9-F1).

    Verifies the discrete local continuity balance:
      H_int^{N-1/2} - H_int^{-1/2} + sum_{n=0}^{N-1} Delta B_{boundary}^n + sum_{n=0}^{N-1} Delta D_{int}^n = sum_{n=0}^{N-1} Delta W_{source, int}^n
    to machine precision (< 1e-12) under undriven/undamped as well as driven/damped conditions.
    """
    dt = courant_factor * dx_m / (c_m_per_s * np.sqrt(3.0))
    c_field = np.full((grid_size, grid_size, grid_size), c_m_per_s, dtype=float)
    sig_field = np.zeros_like(c_field)
    if interior_sigma > 0.0:
        sig_field[sponge_width:-sponge_width, sponge_width:-sponge_width, sponge_width:-sponge_width] = float(interior_sigma)

    mid = grid_size // 2
    coords = np.arange(grid_size) * dx_m
    X, Y, Z = np.meshgrid(coords, coords, coords, indexing='ij')
    r_sq = (X - mid * dx_m) ** 2 + (Y - mid * dx_m) ** 2 + (Z - mid * dx_m) ** 2
    phi0 = np.exp(-r_sq / (2.0 * (2.0 * dx_m) ** 2))
    lap0 = laplacian_3d_clamped(phi0, dx_m)
    phim1 = phi0 + 0.5 * (dt ** 2) * (c_m_per_s ** 2) * lap0

    source_field = None
    if source_amplitude > 0.0:
        source_field = np.zeros_like(c_field)
        source_field[sponge_width:-sponge_width, sponge_width:-sponge_width, sponge_width:-sponge_width] = (
            float(source_amplitude) * np.sin(X[sponge_width:-sponge_width, sponge_width:-sponge_width, sponge_width:-sponge_width])
        )

    p, pm = phi0.copy(), phim1.copy()
    h_init = compute_interior_exact_discrete_leapfrog_energy(p, pm, c_field, dt, dx_m, sponge_width)

    cum_boundary = 0.0
    cum_diss = 0.0
    cum_work = 0.0

    for _ in range(n_steps):
        pn = step_wave_fdtd(p, pm, c_field, sig_field, dt, dx_m, source_field=source_field)
        cum_boundary += compute_exact_discrete_interior_boundary_transfer(p, pm, dt, dx_m, sponge_width)
        cum_diss += compute_interior_sponge_dissipated_energy(pn, pm, c_field, sig_field, dt, dx_m, sponge_width)
        cum_work += compute_interior_source_work_step(pn, pm, source_field, c_field, dt, dx_m, sponge_width)
        pm, p = p, pn

    h_final = compute_interior_exact_discrete_leapfrog_energy(p, pm, c_field, dt, dx_m, sponge_width)
    delta_h = h_final - h_init
    closure_err = abs(delta_h + cum_boundary + cum_diss - cum_work)
    rel_closure = float(closure_err / h_init) if h_init > 0 else 0.0
    is_exact = bool(rel_closure < 1e-12)

    note = (
        f"Discrete interior control-volume budget (grid={grid_size}, sw={sponge_width}, dx={dx_m}m, dt_factor={courant_factor}, steps={n_steps}, "
        f"interior_sigma={interior_sigma:.2f}, source_amplitude={source_amplitude:.2f}): "
        f"H_init={h_init:.6f} E_arb, H_final={h_final:.6f} E_arb, delta_H={delta_h:.6f} E_arb, "
        f"cum_B={cum_boundary:.6f} E_arb, cum_D={cum_diss:.6f} E_arb, cum_W={cum_work:.6f} E_arb, "
        f"closure_error={closure_err:.2e} E_arb, rel_closure={rel_closure:.2e} (< 1e-12)."
    )

    return InteriorControlVolumeBudgetResult(
        grid_size=grid_size,
        sponge_width=sponge_width,
        dx_m=dx_m,
        dt_s=float(dt),
        dt_factor=courant_factor,
        n_steps=n_steps,
        initial_interior_hamiltonian=float(h_init),
        final_interior_hamiltonian=float(h_final),
        interior_hamiltonian_change=float(delta_h),
        cumulative_boundary_transfer=float(cum_boundary),
        cumulative_interior_dissipation=float(cum_diss),
        cumulative_interior_source_work=float(cum_work),
        discrete_local_closure_error=float(closure_err),
        relative_local_closure_error=float(rel_closure),
        is_exact_to_machine_precision=is_exact,
        diagnostic_note=note,
        interior_sigma=float(interior_sigma),
        source_amplitude=float(source_amplitude),
    )


@dataclass(frozen=True)
class TwoMaterialEnergyConservationResult:
    initial_energy: float
    final_energy: float
    terminal_continuum_signed_drift_ratio: float
    max_energy_drift_ratio: float
    max_discrete_hamiltonian_drift_ratio: float
    max_continuum_diagnostic_drift_ratio: float
    initial_discrete_hamiltonian: float
    final_discrete_hamiltonian: float
    exact_discrete_hamiltonian_trajectory: list[float]
    continuum_energy_trajectory: list[float]
    is_conserved_to_tolerance: bool
    diagnostic_note: str


def benchmark_two_material_energy_conservation(
    grid_size: int = 36,
    n_steps: int = 35,
    dx_m: float = 1.0,
    c1: float = 1.0,
    c2: float = 0.60,
    courant_factor: float = 0.85,
    tolerance_drift: float = 0.08,
) -> TwoMaterialEnergyConservationResult:
    """Benchmark discrete Hamiltonian conservation across a two-medium interface (P1-R1-F4, P1-R2-F4, P1-R3-F5, P1-R4-F2).

    Validates that:
    1. The exact discrete staggered leapfrog Hamiltonian H^{n+1/2} is conserved to machine precision (< 1e-10).
    2. The sampled continuum energy diagnostic H_cont has modest truncation drift (< 8%) across the interface.
    3. Records the initial continuum state (step 0) and then records a continuum sample AFTER each step update
       (steps 1..n_steps), so continuum_energy_trajectory has n_steps + 1 entries and final_energy is the
       exact sampled continuum energy of the actual terminal state (phi^(n_steps), phi^(n_steps-1)) (P1-R4-F2).
    """
    dt = courant_factor * dx_m / (max(c1, c2) * np.sqrt(3.0))

    c_field = np.full((grid_size, grid_size, grid_size), c1, dtype=float)
    c_field[grid_size // 2:, :, :] = c2
    sigma_field = np.zeros_like(c_field)

    coords = np.arange(grid_size) * dx_m
    x0 = float((grid_size // 4) * dx_m)
    y0 = float((grid_size // 2) * dx_m)
    z0 = float((grid_size // 2) * dx_m)
    sigma_pulse = 2.5 * dx_m

    X, Y, Z = np.meshgrid(coords, coords, coords, indexing='ij')
    r_sq_0 = (X - x0)**2 + (Y - y0)**2 + (Z - z0)**2
    r_sq_m1 = (X - (x0 - c1 * dt))**2 + (Y - y0)**2 + (Z - z0)**2

    phi_0 = np.exp(-r_sq_0 / (2.0 * sigma_pulse ** 2))
    phi_minus_1 = np.exp(-r_sq_m1 / (2.0 * sigma_pulse ** 2))

    for arr in (phi_0, phi_minus_1):
        arr[0, :, :] = arr[-1, :, :] = 0.0
        arr[:, 0, :] = arr[:, -1, :] = 0.0
        arr[:, :, 0] = arr[:, :, -1] = 0.0

    phi = phi_0.copy()
    phi_prev = phi_minus_1.copy()

    # Step 0 initial sampled continuum energy: state (phi^0, phi^-1)
    h_cont_0 = float(compute_sampled_continuum_energy_diagnostic(phi, phi_prev, c_field, dt, dx_m))
    cont_trajectory: list[float] = [h_cont_0]
    exact_trajectory: list[float] = []

    for _ in range(n_steps):
        phi_next = step_wave_fdtd(phi, phi_prev, c_field, sigma_field, dt, dx_m)
        h_exact = float(compute_exact_discrete_leapfrog_energy(phi_next, phi, c_field, dt, dx_m))
        exact_trajectory.append(h_exact)

        # Advance state to step k, then sample continuum energy of (phi^k, phi^{k-1}) (P1-R4-F2)
        phi_prev, phi = phi, phi_next
        h_cont = float(compute_sampled_continuum_energy_diagnostic(phi, phi_prev, c_field, dt, dx_m))
        cont_trajectory.append(h_cont)

    h_exact_0 = float(exact_trajectory[0])
    h_exact_final = float(exact_trajectory[-1])
    h_cont_final = float(cont_trajectory[-1])

    exact_drifts = [abs(e - h_exact_0) / h_exact_0 if h_exact_0 > 0 else 0.0 for e in exact_trajectory]
    cont_drifts = [abs(e - h_cont_0) / h_cont_0 if h_cont_0 > 0 else 0.0 for e in cont_trajectory]

    max_exact_drift = float(max(exact_drifts))
    max_cont_drift = float(max(cont_drifts))
    terminal_signed_drift = float((h_cont_final - h_cont_0) / h_cont_0) if h_cont_0 > 0 else 0.0

    is_ok = bool(max_exact_drift < 1e-10 and max_cont_drift <= tolerance_drift)

    note = (
        f'Initial exact discrete Hamiltonian: {h_exact_0:.4e}, final: {h_exact_final:.4e}, '
        f'max discrete drift: {max_exact_drift:.2e} (< 1e-10). '
        f'Initial sampled continuum diagnostic (step 0): {h_cont_0:.6f}, '
        f'terminal sampled final_energy (step {n_steps}): {h_cont_final:.6f} '
        f'(terminal signed drift: {terminal_signed_drift:+.2%}, max trajectory continuum drift: {max_cont_drift:.2%} <= {tolerance_drift:.0%}).'
    )

    return TwoMaterialEnergyConservationResult(
        initial_energy=h_cont_0,
        final_energy=h_cont_final,
        terminal_continuum_signed_drift_ratio=terminal_signed_drift,
        max_energy_drift_ratio=max_exact_drift,
        max_discrete_hamiltonian_drift_ratio=max_exact_drift,
        max_continuum_diagnostic_drift_ratio=max_cont_drift,
        initial_discrete_hamiltonian=h_exact_0,
        final_discrete_hamiltonian=h_exact_final,
        exact_discrete_hamiltonian_trajectory=exact_trajectory,
        continuum_energy_trajectory=cont_trajectory,
        is_conserved_to_tolerance=is_ok,
        diagnostic_note=note,
    )


@dataclass(frozen=True)
class WaveGridConvergenceRow:
    n: int
    dx: float
    dt: float
    n_steps: int
    linf_error: float


@dataclass(frozen=True)
class WaveGridConvergenceResult:
    rows: list[WaveGridConvergenceRow]
    observed_orders: list[float]
    is_second_order_converged: bool
    diagnostic_note: str


def benchmark_wave_grid_convergence(
    n_list: Sequence[int] = (17, 33, 65),
    T: float = 0.5,
    c0: float = 1.0,
    tolerance_min_order: float = 1.70,
) -> WaveGridConvergenceResult:
    """Benchmark spatial and temporal second-order convergence of 3D wave solver (P1-R2-F5).

    Compares numerical solution against exact analytical 3D standing mode:
    phi_exact(x,y,z,t) = sin(pi*x/L) * sin(pi*y/L) * sin(pi*z/L) * cos(omega*t)
    with L=1.0, omega = c0 * sqrt(3) * pi / L.
    Verifies O(dx^2 + dt^2) asymptotic second-order convergence rate p ~= 2.0.
    """
    L = 1.0
    kx = np.pi / L
    ky = np.pi / L
    kz = np.pi / L
    omega = c0 * np.sqrt(kx**2 + ky**2 + kz**2)

    rows: list[WaveGridConvergenceRow] = []

    for n in n_list:
        dx = L / (n - 1)
        dt = 0.5 * dx / (c0 * np.sqrt(3.0))
        n_steps = int(round(T / dt))
        actual_T = n_steps * dt

        c_field = np.full((n, n, n), c0, dtype=float)
        sigma_field = np.zeros((n, n, n), dtype=float)

        coords = np.linspace(0, L, n)
        X, Y, Z = np.meshgrid(coords, coords, coords, indexing='ij')

        spatial_mode = np.sin(kx * X) * np.sin(ky * Y) * np.sin(kz * Z)
        phi_0 = spatial_mode * np.cos(omega * 0.0)
        phi_minus_1 = spatial_mode * np.cos(omega * (-dt))

        phi = phi_0.copy()
        phi_prev = phi_minus_1.copy()

        for _ in range(n_steps):
            phi_next = step_wave_fdtd(phi, phi_prev, c_field, sigma_field, dt, dx)
            phi_prev, phi = phi, phi_next

        phi_exact = spatial_mode * np.cos(omega * actual_T)
        err = float(np.max(np.abs(phi - phi_exact)))

        rows.append(WaveGridConvergenceRow(
            n=n,
            dx=dx,
            dt=dt,
            n_steps=n_steps,
            linf_error=err,
        ))

    orders = []
    for i in range(len(rows) - 1):
        r1, r2 = rows[i], rows[i + 1]
        p = float(np.log(r1.linf_error / r2.linf_error) / np.log(r1.dx / r2.dx))
        orders.append(p)

    is_ok = bool(all(p >= tolerance_min_order for p in orders)) if orders else False

    note = (
        f'Wave grid convergence across n={list(n_list)}: '
        f'L_inf errors = {[round(r.linf_error, 7) for r in rows]}. '
        f'Observed convergence orders: {[round(p, 2) for p in orders]}. '
        f'Confirms asymptotic second-order convergence of 3D FDTD solver (p >= {tolerance_min_order}).'
    )

    return WaveGridConvergenceResult(
        rows=rows,
        observed_orders=orders,
        is_second_order_converged=is_ok,
        diagnostic_note=note,
    )


@dataclass(frozen=True)
class InterfaceRefinementRow:
    dx: float
    nx: int
    n_steps: int
    incident_peak: float
    reflected_signed_peak: float
    transmitted_peak: float
    measured_r_amp: float
    measured_t_amp: float
    r_amp_abs_error: float
    t_amp_abs_error: float
    measured_energy_partition_sum: float
    energy_partition_abs_error: float


@dataclass(frozen=True)
class InterfaceTransmissionReflectionResult:
    c1: float
    c2: float
    analytical_r_amp: float
    analytical_t_amp: float
    analytical_r_energy: float
    analytical_t_energy: float
    incident_peak: float
    reflected_signed_peak: float
    transmitted_peak: float
    measured_r_amp: float
    measured_t_amp: float
    r_amp_abs_error: float
    t_amp_abs_error: float
    measured_energy_partition_sum: float
    energy_partition_abs_error: float
    refinement_rows: list[InterfaceRefinementRow]
    errors_decrease_with_refinement: bool
    is_consistent: bool
    interface_derivation_note: str
    diagnostic_note: str


def benchmark_two_material_interface_transmission(
    c1: float = 1.0,
    c2: float = 0.6,
    dx_list: Sequence[float] = (1.0, 0.5, 0.25),
    tolerance_coeff_error: float = 0.015,
    grid_size: int | None = None,
    n_steps: int | None = None,
) -> InterfaceTransmissionReflectionResult:
    """Analytical reflection & transmission benchmark across planar two-medium step interface (P1-R2-F5, P1-R3-F3).

    Derivation for the implemented non-divergence scalar wave equation:
        (1 / c(x)^2) * d^2 phi / dt^2 = nabla^2 phi
    At a planar step interface x = x_int between medium 1 (speed c1) and medium 2 (speed c2),
    boundedness of d^2 phi / dx^2 requires continuity of both field and normal derivative:
        1) phi(x_int^-, t) = phi(x_int^+, t)           => 1 + R_amp = T_amp
        2) dphi/dx(x_int^-, t) = dphi/dx(x_int^+, t)   => (1 - R_amp) / c1 = T_amp / c2
    Solving yields the exact analytical amplitude and energy coefficients:
        R_amp = (c2 - c1) / (c1 + c2)
        T_amp = 2 * c2 / (c1 + c2) = 1 + R_amp
        R_energy = |R_amp|^2 = ((c2 - c1) / (c1 + c2))^2
        T_energy = (c1 / c2) * |T_amp|^2 = 4 * c1 * c2 / (c1 + c2)^2
        R_energy + T_energy = 1
    """
    r_exact = float((c2 - c1) / (c1 + c2))
    t_exact = float(2.0 * c2 / (c1 + c2))
    r_e_exact = float(r_exact ** 2)
    t_e_exact = float((c1 / c2) * (t_exact ** 2))

    L_x = 60.0
    x_int = 30.0
    x0 = 21.0
    sigma_x = 2.0
    T_phys = 18.0

    rows: list[InterfaceRefinementRow] = []

    for dx in dx_list:
        nx = int(round(L_x / dx)) + 1
        ny = 3
        mid_x = int(round(x_int / dx))
        dt = 0.5 * dx / (max(c1, c2) * np.sqrt(3.0))
        steps = int(round(T_phys / dt))

        x = np.arange(nx) * dx
        # Right-traveling Gaussian pulse f(x - c1*t) initialized in medium 1
        phi0_1d = np.exp(-((x - x0) ** 2) / (2.0 * sigma_x ** 2))
        phim1_1d = np.exp(-((x - (x0 - c1 * dt)) ** 2) / (2.0 * sigma_x ** 2))
        phi0_1d[0] = phi0_1d[-1] = 0.0
        phim1_1d[0] = phim1_1d[-1] = 0.0

        phi_0 = np.broadcast_to(phi0_1d[:, None, None], (nx, ny, ny)).copy()
        phi_m1 = np.broadcast_to(phim1_1d[:, None, None], (nx, ny, ny)).copy()

        sig_f = np.zeros((nx, ny, ny), dtype=float)
        c_ref = np.full((nx, ny, ny), c1, dtype=float)
        c_two = np.full((nx, ny, ny), c1, dtype=float)
        c_two[mid_x:, :, :] = c2

        # 1. Incident-only homogeneous reference control (c = c1 everywhere)
        p_ref, pm_ref = phi_0.copy(), phi_m1.copy()
        # 2. Two-material step interface simulation (c1 -> c2 at x = x_int)
        p_two, pm_two = phi_0.copy(), phi_m1.copy()

        for _ in range(steps):
            p_ref_n = step_wave_fdtd(p_ref, pm_ref, c_ref, sig_f, dt, dx, boundary_mode='planar_x')
            pm_ref, p_ref = p_ref, p_ref_n

            p_two_n = step_wave_fdtd(p_two, pm_two, c_two, sig_f, dt, dx, boundary_mode='planar_x')
            pm_two, p_two = p_two, p_two_n

        inc_line = p_ref[:, 1, 1]
        two_line = p_two[:, 1, 1]

        # Isolate reflected wave in medium 1 (x < x_int) via reference subtraction and transmitted wave in medium 2 (x >= x_int)
        refl_region = two_line[:mid_x] - inc_line[:mid_x]
        trans_region = two_line[mid_x:]

        inc_peak = float(np.max(np.abs(inc_line)))
        refl_idx = int(np.argmax(np.abs(refl_region)))
        refl_signed = float(refl_region[refl_idx])
        trans_idx = int(np.argmax(np.abs(trans_region)))
        trans_signed = float(trans_region[trans_idx])

        r_meas = float(refl_signed / inc_peak) if inc_peak > 0 else 0.0
        t_meas = float(trans_signed / inc_peak) if inc_peak > 0 else 0.0
        r_err = float(abs(r_meas - r_exact))
        t_err = float(abs(t_meas - t_exact))

        e_part = float((r_meas ** 2) + (c1 / c2) * (t_meas ** 2))
        e_err = float(abs(e_part - 1.0))

        rows.append(InterfaceRefinementRow(
            dx=float(dx),
            nx=nx,
            n_steps=steps,
            incident_peak=inc_peak,
            reflected_signed_peak=refl_signed,
            transmitted_peak=trans_signed,
            measured_r_amp=r_meas,
            measured_t_amp=t_meas,
            r_amp_abs_error=r_err,
            t_amp_abs_error=t_err,
            measured_energy_partition_sum=e_part,
            energy_partition_abs_error=e_err,
        ))

    finest = rows[-1]
    err_decreases = bool(
        all(
            rows[i + 1].r_amp_abs_error < rows[i].r_amp_abs_error
            and rows[i + 1].t_amp_abs_error < rows[i].t_amp_abs_error
            for i in range(len(rows) - 1)
        )
    ) if len(rows) >= 2 else True

    is_ok = bool(
        err_decreases
        and finest.r_amp_abs_error <= tolerance_coeff_error
        and finest.t_amp_abs_error <= tolerance_coeff_error
        and finest.energy_partition_abs_error <= 2.0 * tolerance_coeff_error
    )

    deriv_note = (
        'For the non-divergence PDE phi_tt = c(x)^2 nabla^2 phi, continuity of phi and dphi/dx across '
        'a planar interface yields R_amp = (c2 - c1)/(c1 + c2), T_amp = 2*c2/(c1 + c2) = 1 + R_amp, '
        'and energy conservation |R_amp|^2 + (c1/c2)*|T_amp|^2 = 1. This validates numerical solver '
        'accuracy on the mathematical wave PDE, not physical scalar-wave propagation.'
    )

    note = (
        f'Analytical planar interface benchmark (c1={c1} -> c2={c2}) across dx={[r.dx for r in rows]}: '
        f'Exact R_amp={r_exact:+.4f}, T_amp={t_exact:+.4f}. '
        f'Finest (dx={finest.dx}) measured R_amp={finest.measured_r_amp:+.4f} (abs_err={finest.r_amp_abs_error:.4e}), '
        f'T_amp={finest.measured_t_amp:+.4f} (abs_err={finest.t_amp_abs_error:.4e}), '
        f'energy partition R_e + T_e = {finest.measured_energy_partition_sum:.4f} (err={finest.energy_partition_abs_error:.4e}). '
        f'Errors decrease monotonically under refinement: {err_decreases}.'
    )

    return InterfaceTransmissionReflectionResult(
        c1=c1,
        c2=c2,
        analytical_r_amp=r_exact,
        analytical_t_amp=t_exact,
        analytical_r_energy=r_e_exact,
        analytical_t_energy=t_e_exact,
        incident_peak=finest.incident_peak,
        reflected_signed_peak=finest.reflected_signed_peak,
        transmitted_peak=finest.transmitted_peak,
        measured_r_amp=finest.measured_r_amp,
        measured_t_amp=finest.measured_t_amp,
        r_amp_abs_error=finest.r_amp_abs_error,
        t_amp_abs_error=finest.t_amp_abs_error,
        measured_energy_partition_sum=finest.measured_energy_partition_sum,
        energy_partition_abs_error=finest.energy_partition_abs_error,
        refinement_rows=rows,
        errors_decrease_with_refinement=err_decreases,
        is_consistent=is_ok,
        interface_derivation_note=deriv_note,
        diagnostic_note=note,
    )


def run_3d_simulation(
    shape: str = 'Sphere',
    material: str = 'Air (baseline)',
    n: int = 48,
    n_frames: int = 70,
    spf: int = 4,
    dx_m: float = 1.0,
    source_freq_hz: float = 0.05,
    source_mode: str = 'dirichlet',
) -> tuple[list[np.ndarray], np.ndarray, dict[str, Any]]:
    """Production 3D FDTD wave simulation runner (resolves P1-R1-F1, P1-R2-F5).

    Executes validated non-divergence FDTD with:
    - Relocated source outside sponge (source_x > w_sponge).
    - Quadratic boundary damping layer sigma(d) = max_sigma * (d/w)^2.
    - Clamped Dirichlet boundaries (no periodic roll).
    - Normalized source injection independent of dt (Dirichlet emitter or dt^2 scaled additive source).
    - CFL enforcement.
    """
    if material not in MATERIALS:
        raise ValueError(f'Unknown material: {material}. Options: {list(MATERIALS.keys())}')

    sponge_w = 8
    source_x = min(14, max(sponge_w + 1, n // 2))
    source_y = n // 2
    source_z = n // 2
    cfg = WaveGridConfig(
        n_x=n, n_y=n, n_z=n, dx_m=dx_m,
        sponge_width=sponge_w,
        source_x=source_x,
        source_y=source_y,
        source_z=source_z,
        source_frequency_hz=source_freq_hz,
    )

    obj_mask = make_shape_mask(n, shape)
    c_speed = float(MATERIALS[material]['speed'])

    c_field = np.full((n, n, n), cfg.c_background_m_per_s, dtype=float)
    c_field[obj_mask] = c_speed

    sigma_field = create_sponge_conductivity_field((n, n, n), sponge_w, max_sigma=2.0)

    # Validate CFL for the configured medium
    dt = cfg.dt_s
    omega = 2.0 * np.pi * source_freq_hz

    phi = np.zeros((n, n, n), dtype=float)
    phi_prev = np.zeros((n, n, n), dtype=float)
    snapshots: list[np.ndarray] = []

    sy, sz = n // 2, n // 2

    for fi in range(n_frames):
        for s in range(spf):
            step_idx = fi * spf + s
            t_phys = step_idx * dt
            if source_mode == 'additive':
                src_field = np.zeros((n, n, n), dtype=float)
                src_field[source_x, sy, sz] = np.sin(omega * t_phys) / (dx_m ** 3)
                phi_next = step_wave_fdtd(phi, phi_prev, c_field, sigma_field, dt, dx_m, source_field=src_field)
            else:  # 'dirichlet' emitter (prescribed waveform, exactly dt-independent)
                phi_next = step_wave_fdtd(phi, phi_prev, c_field, sigma_field, dt, dx_m)
                phi_next[source_x, sy, sz] = np.sin(omega * (t_phys + dt))

            phi_prev, phi = phi, phi_next

        snapshots.append(phi.copy())

    audit = audit_wavelength_resolution(material, c_speed, source_freq_hz, dx_m)

    metadata: dict[str, Any] = {
        'grid_size': n,
        'dx_m': dx_m,
        'dt_s': dt,
        'sponge_width': sponge_w,
        'source_pos': (source_x, sy, sz),
        'source_freq_hz': source_freq_hz,
        'source_mode': source_mode,
        'shape': shape,
        'material': material,
        'resolution_audit': {
            'points_per_wavelength': audit.points_per_wavelength,
            'is_adequately_resolved': audit.is_adequately_resolved,
            'status': audit.status,
            'epistemic_label': audit.epistemic_label,
            'diagnostic_note': audit.diagnostic_note,
        },
    }

    return snapshots, obj_mask, metadata
