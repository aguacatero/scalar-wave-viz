"""Conventional electrostatic benchmarks, not an anomalous propulsion model.

2D Dirichlet Laplace solution for vacuum with a grounded outer box.
The outer boundary is a physical external electrode, NOT free-space infinity.
The ideal parallel plate benchmark is a separate analytic reference.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve

EPSILON_0_F_PER_M = 8.8541878188e-12


@dataclass(frozen=True)
class PlateBenchmark:
    voltage_v: float
    gap_m: float
    area_m2: float
    electric_field_v_per_m: float
    pressure_pa: float
    force_on_positive_plate_n: float
    force_on_negative_plate_n: float
    net_pair_force_n: float
    stored_energy_j: float


def parallel_plate_benchmark(voltage_v: float, gap_m: float, area_m2: float) -> PlateBenchmark:
    """Ideal parallel plates, neglecting fringing; opposing attraction sums to zero."""
    if not all(np.isfinite(v) for v in (voltage_v, gap_m, area_m2)):
        raise ValueError('Inputs must be finite')
    if gap_m <= 0 or area_m2 <= 0:
        raise ValueError('Gap and area must be positive')
    e_field = voltage_v / gap_m
    pressure = 0.5 * EPSILON_0_F_PER_M * e_field**2
    force = pressure * area_m2
    energy = 0.5 * EPSILON_0_F_PER_M * e_field**2 * area_m2 * gap_m
    return PlateBenchmark(voltage_v, gap_m, area_m2, e_field, pressure,
                          force, -force, 0.0, energy)


@dataclass(frozen=True)
class FieldSolution:
    potential_v: np.ndarray
    ex_v_per_m: np.ndarray
    ey_v_per_m: np.ndarray
    fixed_mask: np.ndarray
    grid_spacing_m: float
    max_discrete_residual_v: float


def solve_dirichlet(fixed_mask: np.ndarray, fixed_potential_v: np.ndarray,
                    grid_spacing_m: float) -> FieldSolution:
    """Solve Laplace's equation with a five-point finite-difference stencil.

    Fixed values are Dirichlet. No force or charge claim follows from
    a potential-field picture without an explicitly defined system boundary.
    """
    mask = np.asarray(fixed_mask, dtype=bool)
    values = np.asarray(fixed_potential_v, dtype=float)
    if mask.ndim != 2 or min(mask.shape) < 3 or mask.shape != values.shape:
        raise ValueError('Mask and values must be matching 2D grids, at least 3x3')
    if not (np.isfinite(grid_spacing_m) and grid_spacing_m > 0):
        raise ValueError('Grid spacing must be positive and finite')
    if not np.all(np.isfinite(values)):
        raise ValueError('Potential values must be finite')
    if not (mask[0, :].all() and mask[-1, :].all() and
            mask[:, 0].all() and mask[:, -1].all()):
        raise ValueError('All outer boundary points must have fixed potentials')

    unknown = np.argwhere(~mask)
    indexes = np.full(mask.shape, -1, dtype=int)
    indexes[~mask] = np.arange(len(unknown))
    rows, cols, coefficients = [], [], []
    rhs = np.zeros(len(unknown))
    for k, (i, j) in enumerate(unknown):
        rows.append(k); cols.append(k); coefficients.append(4.0)
        for ni, nj in ((i-1,j),(i+1,j),(i,j-1),(i,j+1)):
            if mask[ni,nj]:
                rhs[k] += values[ni,nj]
            else:
                rows.append(k); cols.append(int(indexes[ni,nj])); coefficients.append(-1.0)

    potential = values.copy()
    if len(unknown):
        matrix = coo_matrix((coefficients, (rows, cols)),
                            shape=(len(unknown), len(unknown))).tocsr()
        potential[~mask] = spsolve(matrix, rhs)
    neighbor_sum = (potential[:-2, 1:-1] + potential[2:, 1:-1] +
                    potential[1:-1, :-2] + potential[1:-1, 2:])
    residual = 4 * potential[1:-1, 1:-1] - neighbor_sum
    max_residual = float(np.max(np.abs(residual[~mask[1:-1,1:-1]]), initial=0.0))
    ex = -np.gradient(potential, grid_spacing_m, axis=0, edge_order=2)
    ey = -np.gradient(potential, grid_spacing_m, axis=1, edge_order=2)
    return FieldSolution(potential, ex, ey, mask.copy(), grid_spacing_m, max_residual)


def electrode_pair_in_grounded_box(
    n: int = 81, box_width_m: float = 0.04,
    left_center_x_m: float = -0.008, right_center_x_m: float = 0.008,
    left_radius_m: float = 0.003, right_radius_m: float = 0.003,
    left_voltage_v: float = 500.0, right_voltage_v: float = -500.0,
) -> FieldSolution:
    """Two cylindrical-electrode cross-sections in a grounded square box.

    Vacuum, homogeneous permittivity, ideal conductors.
    NOT an Exodus patent geometry. A grounded box is an external object.
    """
    if not isinstance(n, int) or n < 11 or n > 401:
        raise ValueError('n must be an integer between 11 and 401')
    scalars = (box_width_m, left_center_x_m, right_center_x_m,
               left_radius_m, right_radius_m, left_voltage_v, right_voltage_v)
    if not all(np.isfinite(v) for v in scalars):
        raise ValueError('Geometry and voltages must be finite')
    if box_width_m <= 0 or left_radius_m <= 0 or right_radius_m <= 0:
        raise ValueError('Width and radii must be positive')
    h = box_width_m / (n-1)
    coords = np.linspace(-box_width_m/2, box_width_m/2, n)
    x, y = np.meshgrid(coords, coords, indexing='ij')
    left = (x-left_center_x_m)**2 + y**2 <= left_radius_m**2
    right = (x-right_center_x_m)**2 + y**2 <= right_radius_m**2
    if np.any(left & right) or not np.any(left) or not np.any(right):
        raise ValueError('Electrodes overlap or are too small for the grid')
    for disk in (left, right):
        if (disk[0,:].any() or disk[-1,:].any() or
            disk[:,0].any() or disk[:,-1].any()):
            raise ValueError('Electrodes must not touch the grounded enclosure')
    mask = np.zeros((n,n), dtype=bool)
    mask[0,:] = mask[-1,:] = True
    mask[:,0] = mask[:,-1] = True
    mask |= left | right
    fixed = np.zeros((n,n))
    fixed[left] = left_voltage_v
    fixed[right] = right_voltage_v
    return solve_dirichlet(mask, fixed, h)
