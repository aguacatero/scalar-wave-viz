"""Conventional electrostatic benchmarks, not an anomalous propulsion model.

2D Dirichlet Laplace solution for vacuum with a grounded outer box.
The outer boundary is a physical external electrode, NOT free-space infinity.
The ideal parallel plate benchmark is a separate analytic reference.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

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
    """Ideal parallel plates, neglecting fringing; opposing attraction sums to zero.

    Coordinate convention:
      Positive plate at x = 0, negative plate at x = gap.
      Force on positive plate is along +x (attracted toward negative plate): +p * A.
      Force on negative plate is along -x (attracted toward positive plate): -p * A.
      Net pair force is the explicit sum: force_pos + force_neg == 0.0 (Newton's 3rd Law).
    """
    if not all(np.isfinite(v) for v in (voltage_v, gap_m, area_m2)):
        raise ValueError('Inputs must be finite')
    if gap_m <= 0 or area_m2 <= 0:
        raise ValueError('Gap and area must be positive')
    e_field = voltage_v / gap_m
    pressure = 0.5 * EPSILON_0_F_PER_M * e_field**2
    force_pos = pressure * area_m2
    force_neg = -pressure * area_m2
    net_force = force_pos + force_neg
    energy = 0.5 * EPSILON_0_F_PER_M * e_field**2 * area_m2 * gap_m
    return PlateBenchmark(
        voltage_v=voltage_v,
        gap_m=gap_m,
        area_m2=area_m2,
        electric_field_v_per_m=e_field,
        pressure_pa=pressure,
        force_on_positive_plate_n=force_pos,
        force_on_negative_plate_n=force_neg,
        net_pair_force_n=net_force,
        stored_energy_j=energy,
    )


def verify_plate_force_virtual_work(
    voltage_v: float, gap_m: float, area_m2: float, delta_gap_m: float = 1e-8
) -> dict[str, float]:
    """Independently cross-check parallel-plate attraction via virtual work and energy derivatives.

    Distinguishes two thermodynamic ensembles:
    1. Fixed Charge Q (isolated capacitor):
       U_Q(g) = Q^2 / (2 * C(g)) = Q^2 * g / (2 * epsilon_0 * A)
       Force along gap direction tending to increase gap:
         F_g = - dU_Q / dg = - 0.5 * epsilon_0 * (V/g)^2 * A (attractive, pulling inward)

    2. Fixed Voltage V (connected to external voltage source / battery):
       U_V(g) = 0.5 * C(g) * V^2
       When gap increases by dg:
         dW_source = V * dQ = V^2 * dC = 2 * dU_V
         dW_mech = F_g * dg = dW_source - dU_V = dU_V
       Force tending to increase gap:
         F_g = dU_V / dg = - 0.5 * epsilon_0 * (V/g)^2 * A (identical attractive magnitude)
    """
    if gap_m <= 0 or area_m2 <= 0 or delta_gap_m <= 0 or delta_gap_m >= gap_m:
        raise ValueError('Invalid geometry for virtual work test')

    def capacitance(g: float) -> float:
        return EPSILON_0_F_PER_M * area_m2 / g

    # Constant voltage energy and numerical derivative
    u_v_plus = 0.5 * capacitance(gap_m + delta_gap_m) * voltage_v**2
    u_v_minus = 0.5 * capacitance(gap_m - delta_gap_m) * voltage_v**2
    du_v_dg = (u_v_plus - u_v_minus) / (2 * delta_gap_m)
    f_gap_fixed_v = du_v_dg

    # Constant charge energy and numerical derivative
    q_fixed = capacitance(gap_m) * voltage_v
    u_q_plus = q_fixed**2 / (2 * capacitance(gap_m + delta_gap_m))
    u_q_minus = q_fixed**2 / (2 * capacitance(gap_m - delta_gap_m))
    du_q_dg = (u_q_plus - u_q_minus) / (2 * delta_gap_m)
    f_gap_fixed_q = -du_q_dg

    expected_magnitude = 0.5 * EPSILON_0_F_PER_M * (voltage_v / gap_m)**2 * area_m2

    return {
        'expected_magnitude_n': expected_magnitude,
        'virtual_work_fixed_v_n': abs(f_gap_fixed_v),
        'virtual_work_fixed_q_n': abs(f_gap_fixed_q),
        'signed_f_gap_fixed_v_n': f_gap_fixed_v,
        'signed_f_gap_fixed_q_n': f_gap_fixed_q,
    }


@dataclass(frozen=True)
class ElectrodeConfig:
    center_x_m: float
    center_y_m: float = 0.0
    radius_m: float = 0.003
    voltage_v: float = 0.0

    def __post_init__(self):
        for name, val in (('center_x_m', self.center_x_m),
                          ('center_y_m', self.center_y_m),
                          ('radius_m', self.radius_m),
                          ('voltage_v', self.voltage_v)):
            if not np.isfinite(val):
                raise ValueError(f'{name} must be finite')
        if self.radius_m <= 0:
            raise ValueError('radius_m must be positive')


@dataclass(frozen=True)
class GroundedBoxConfig:
    n: int = 101
    box_width_m: float = 0.04
    left_electrode: ElectrodeConfig = ElectrodeConfig(
        center_x_m=-0.008, center_y_m=0.0, radius_m=0.003, voltage_v=500.0
    )
    right_electrode: ElectrodeConfig = ElectrodeConfig(
        center_x_m=0.008, center_y_m=0.0, radius_m=0.003, voltage_v=-500.0
    )

    def __post_init__(self):
        if not isinstance(self.n, int) or self.n < 11 or self.n > 401:
            raise ValueError('n must be an integer between 11 and 401')
        if not np.isfinite(self.box_width_m) or self.box_width_m <= 0:
            raise ValueError('box_width_m must be positive and finite')

        half_w = self.box_width_m / 2.0
        for name, elec in (
            ('left_electrode', self.left_electrode),
            ('right_electrode', self.right_electrode),
        ):
            if abs(elec.center_x_m) + elec.radius_m >= half_w or abs(elec.center_y_m) + elec.radius_m >= half_w:
                raise ValueError(
                    f'{name} penetrates or touches grounded enclosure boundary: '
                    f'x_extent=[{elec.center_x_m - elec.radius_m:.4e}, {elec.center_x_m + elec.radius_m:.4e}], '
                    f'y_extent=[{elec.center_y_m - elec.radius_m:.4e}, {elec.center_y_m + elec.radius_m:.4e}], '
                    f'half_width={half_w:.4e}'
                )

        center_dist = float(np.hypot(
            self.right_electrode.center_x_m - self.left_electrode.center_x_m,
            self.right_electrode.center_y_m - self.left_electrode.center_y_m,
        ))
        if center_dist <= (self.left_electrode.radius_m + self.right_electrode.radius_m):
            raise ValueError(
                f'Electrodes intersect or touch in continuous space: '
                f'center distance {center_dist:.4e} m <= sum of radii '
                f'{self.left_electrode.radius_m + self.right_electrode.radius_m:.4e} m'
            )


@dataclass(frozen=True)
class FieldSolution:
    potential_v: np.ndarray
    ex_v_per_m: np.ndarray             # Physical vacuum field; NaN outside vacuum interior
    ey_v_per_m: np.ndarray             # Physical vacuum field; NaN outside vacuum interior
    vacuum_mask: np.ndarray            # True for vacuum nodes where Laplace eq holds
    conductor_mask: np.ndarray         # True for interior conductor electrodes
    boundary_mask: np.ndarray          # True for external boundary (e.g. grounded box)
    fixed_mask: np.ndarray             # conductor_mask | boundary_mask (backward compatible)
    grid_spacing_m: float
    max_discrete_residual_v: float
    raw_gradient_x_v_per_m: np.ndarray # Discrete gradient of potential grid across all nodes
    raw_gradient_y_v_per_m: np.ndarray # Discrete gradient of potential grid across all nodes
    config: GroundedBoxConfig | None = None

    @property
    def vacuum_e_magnitude_v_per_m(self) -> np.ndarray:
        """Physical vacuum electric field magnitude; NaN on non-vacuum nodes."""
        return np.hypot(self.ex_v_per_m, self.ey_v_per_m)


def solve_dirichlet(
    fixed_mask: np.ndarray,
    fixed_potential_v: np.ndarray,
    grid_spacing_m: float,
    conductor_mask: np.ndarray | None = None,
    boundary_mask: np.ndarray | None = None,
    config: GroundedBoxConfig | None = None,
) -> FieldSolution:
    """Solve Laplace's equation with a five-point finite-difference stencil.

    Fixed values are Dirichlet. No force or charge claim follows from
    a potential-field picture without an explicitly defined system boundary.

    Domain nodes are explicitly partitioned into:
      - vacuum_mask: interior vacuum cells where Laplace eq holds (nabla^2 V = 0)
      - conductor_mask: interior conducting electrodes
      - boundary_mask: external Dirichlet boundary (grounded outer enclosure)

    Validates that conductor_mask and boundary_mask are disjoint and form a complete
    partition of fixed_mask, and that boundary_mask covers all exterior boundaries.

    Physical vacuum electric fields (ex_v_per_m, ey_v_per_m) are NaN on non-vacuum cells
    to prevent fictitious interface-gradient samples from being mistaken for physical interior fields.
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

    if boundary_mask is not None:
        b_mask = np.asarray(boundary_mask, dtype=bool)
        if b_mask.shape != mask.shape:
            raise ValueError(f'boundary_mask shape {b_mask.shape} does not match fixed_mask shape {mask.shape}')
        if not (b_mask[0, :].all() and b_mask[-1, :].all() and
                b_mask[:, 0].all() and b_mask[:, -1].all()):
            raise ValueError('All outer boundary points must be included in boundary_mask')
    else:
        b_mask = np.zeros(mask.shape, dtype=bool)
        b_mask[0, :] = b_mask[-1, :] = True
        b_mask[:, 0] = b_mask[:, -1] = True

    if conductor_mask is not None:
        c_mask = np.asarray(conductor_mask, dtype=bool)
        if c_mask.shape != mask.shape:
            raise ValueError(f'conductor_mask shape {c_mask.shape} does not match fixed_mask shape {mask.shape}')
    else:
        c_mask = mask & ~b_mask

    # Disjointness check
    overlap = c_mask & b_mask
    if np.any(overlap):
        raise ValueError(f'conductor_mask and boundary_mask must be disjoint; found {np.sum(overlap)} overlapping cells')

    # Partition check: union must exactly equal fixed_mask
    if not np.array_equal(c_mask | b_mask, mask):
        raise ValueError('conductor_mask and boundary_mask must form a complete partition of fixed_mask')

    v_mask = ~mask

    unknown = np.argwhere(v_mask)
    indexes = np.full(mask.shape, -1, dtype=int)
    indexes[v_mask] = np.arange(len(unknown))
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
        potential[v_mask] = spsolve(matrix, rhs)
    neighbor_sum = (potential[:-2, 1:-1] + potential[2:, 1:-1] +
                    potential[1:-1, :-2] + potential[1:-1, 2:])
    residual = 4 * potential[1:-1, 1:-1] - neighbor_sum
    max_residual = float(np.max(np.abs(residual[v_mask[1:-1,1:-1]]), initial=0.0))

    # Raw discrete gradient across entire grid
    raw_ex = -np.gradient(potential, grid_spacing_m, axis=0, edge_order=2)
    raw_ey = -np.gradient(potential, grid_spacing_m, axis=1, edge_order=2)

    # Physical vacuum field: NaN outside vacuum interior
    vac_ex = np.full_like(raw_ex, np.nan)
    vac_ey = np.full_like(raw_ey, np.nan)
    vac_ex[v_mask] = raw_ex[v_mask]
    vac_ey[v_mask] = raw_ey[v_mask]

    return FieldSolution(
        potential_v=potential,
        ex_v_per_m=vac_ex,
        ey_v_per_m=vac_ey,
        vacuum_mask=v_mask,
        conductor_mask=c_mask,
        boundary_mask=b_mask,
        fixed_mask=mask.copy(),
        grid_spacing_m=grid_spacing_m,
        max_discrete_residual_v=max_residual,
        raw_gradient_x_v_per_m=raw_ex,
        raw_gradient_y_v_per_m=raw_ey,
        config=config,
    )


@dataclass(frozen=True)
class SurfaceInterfaceResult:
    face_count: int
    normal_fields_v_per_m: np.ndarray
    tractions_pa: np.ndarray
    face_normals: np.ndarray
    max_normal_field_v_per_m: float
    max_traction_pa: float
    mean_traction_pa: float
    integrated_force_per_depth_n_per_m: np.ndarray
    diagnostic_note: str


def evaluate_conductor_surface_interface(
    solution: FieldSolution,
) -> SurfaceInterfaceResult:
    """Evaluate one-sided surface-normal electric field and electrostatic traction across conductor-vacuum faces.

    In continuum electrostatics of ideal conductors:
      - Physical interior field is E = 0.
      - At the conductor surface, electric field is purely normal: E = E_n * n_hat.
      - Normal field is evaluated from the vacuum side: E_n = - dV/dn.
      - Local outward electrostatic traction: T_n = 0.5 * epsilon_0 * E_n^2.
      - Vector traction on face with outward normal n_hat: T_vec = T_n * n_hat.

    This function identifies discrete interface faces between conductor nodes and
    adjacent vacuum nodes, computing the one-sided normal derivative:
        E_n = - (V_vacuum - V_conductor) / h
    across each face oriented along the outward face normal n_hat.
    This strictly avoids node-centered central differences that conflate tangential fields
    with normal traction (e.g. eliminating the 2x traction error on harmonic V = x*y).

    NOTE: This is a diagnostic interface calculation for research inspection.
    It does NOT establish anomalous propulsion or a closed-system force violation.
    """
    pot = solution.potential_v
    h = solution.grid_spacing_m
    cond = solution.conductor_mask
    vac = solution.vacuum_mask

    normal_fields: list[float] = []
    tractions: list[float] = []
    normals: list[tuple[float, float]] = []

    # 1. East faces: conductor at (i, j) adjacent to vacuum at (i+1, j) -> normal = (+1, 0)
    east_cond = cond[:-1, :] & vac[1:, :]
    if np.any(east_cond):
        i_idxs, j_idxs = np.where(east_cond)
        for i, j in zip(i_idxs, j_idxs):
            e_n = -(pot[i + 1, j] - pot[i, j]) / h
            t_n = 0.5 * EPSILON_0_F_PER_M * e_n**2
            normal_fields.append(e_n)
            tractions.append(t_n)
            normals.append((1.0, 0.0))

    # 2. West faces: conductor at (i, j) adjacent to vacuum at (i-1, j) -> normal = (-1, 0)
    west_cond = cond[1:, :] & vac[:-1, :]
    if np.any(west_cond):
        i_idxs, j_idxs = np.where(west_cond)
        # i_idxs here are in sliced coords [1:], so actual conductor index is i + 1
        for i, j in zip(i_idxs + 1, j_idxs):
            e_n = -(pot[i - 1, j] - pot[i, j]) / h
            t_n = 0.5 * EPSILON_0_F_PER_M * e_n**2
            normal_fields.append(e_n)
            tractions.append(t_n)
            normals.append((-1.0, 0.0))

    # 3. North faces: conductor at (i, j) adjacent to vacuum at (i, j+1) -> normal = (0, +1)
    north_cond = cond[:, :-1] & vac[:, 1:]
    if np.any(north_cond):
        i_idxs, j_idxs = np.where(north_cond)
        for i, j in zip(i_idxs, j_idxs):
            e_n = -(pot[i, j + 1] - pot[i, j]) / h
            t_n = 0.5 * EPSILON_0_F_PER_M * e_n**2
            normal_fields.append(e_n)
            tractions.append(t_n)
            normals.append((0.0, 1.0))

    # 4. South faces: conductor at (i, j) adjacent to vacuum at (i, j-1) -> normal = (0, -1)
    south_cond = cond[:, 1:] & vac[:, :-1]
    if np.any(south_cond):
        i_idxs, j_idxs = np.where(south_cond)
        for i, j in zip(i_idxs, j_idxs + 1):
            e_n = -(pot[i, j - 1] - pot[i, j]) / h
            t_n = 0.5 * EPSILON_0_F_PER_M * e_n**2
            normal_fields.append(e_n)
            tractions.append(t_n)
            normals.append((0.0, -1.0))

    arr_fields = np.array(normal_fields, dtype=float)
    arr_tractions = np.array(tractions, dtype=float)
    arr_normals = np.array(normals, dtype=float)

    face_count = len(normal_fields)
    max_e = float(np.max(np.abs(arr_fields))) if face_count > 0 else 0.0
    max_t = float(np.max(arr_tractions)) if face_count > 0 else 0.0
    mean_t = float(np.mean(arr_tractions)) if face_count > 0 else 0.0

    # Integrated force per unit depth: sum(T_n * n_hat * h)
    if face_count > 0:
        fx = float(np.sum(arr_tractions * arr_normals[:, 0] * h))
        fy = float(np.sum(arr_tractions * arr_normals[:, 1] * h))
        integrated_f = np.array([fx, fy], dtype=float)
    else:
        integrated_f = np.array([0.0, 0.0], dtype=float)

    note = (
        'Diagnostic one-sided surface-normal interface traction. Evaluated on discrete face edges. '
        'Not a converged device force or anomalous propulsion claim.'
    )

    return SurfaceInterfaceResult(
        face_count=face_count,
        normal_fields_v_per_m=arr_fields,
        tractions_pa=arr_tractions,
        face_normals=arr_normals,
        max_normal_field_v_per_m=max_e,
        max_traction_pa=max_t,
        mean_traction_pa=mean_t,
        integrated_force_per_depth_n_per_m=integrated_f,
        diagnostic_note=note,
    )


def electrode_pair_in_grounded_box(
    n: int = 81, box_width_m: float = 0.04,
    left_center_x_m: float = -0.008, right_center_x_m: float = 0.008,
    left_center_y_m: float = 0.0, right_center_y_m: float = 0.0,
    left_radius_m: float = 0.003, right_radius_m: float = 0.003,
    left_voltage_v: float = 500.0, right_voltage_v: float = -500.0,
    config: GroundedBoxConfig | None = None,
) -> FieldSolution:
    """Two cylindrical-electrode cross-sections in a grounded square box.

    Vacuum, homogeneous permittivity, ideal conductors.
    NOT an Exodus patent geometry. A grounded box is an external object.
    """
    if config is not None:
        n = config.n
        box_width_m = config.box_width_m
        left_center_x_m = config.left_electrode.center_x_m
        left_center_y_m = config.left_electrode.center_y_m
        right_center_x_m = config.right_electrode.center_x_m
        right_center_y_m = config.right_electrode.center_y_m
        left_radius_m = config.left_electrode.radius_m
        right_radius_m = config.right_electrode.radius_m
        left_voltage_v = config.left_electrode.voltage_v
        right_voltage_v = config.right_electrode.voltage_v
    else:
        config = GroundedBoxConfig(
            n=n,
            box_width_m=box_width_m,
            left_electrode=ElectrodeConfig(left_center_x_m, left_center_y_m, left_radius_m, left_voltage_v),
            right_electrode=ElectrodeConfig(right_center_x_m, right_center_y_m, right_radius_m, right_voltage_v),
        )

    if not isinstance(n, int) or n < 11 or n > 401:
        raise ValueError('n must be an integer between 11 and 401')
    scalars = (box_width_m, left_center_x_m, left_center_y_m,
               right_center_x_m, right_center_y_m,
               left_radius_m, right_radius_m, left_voltage_v, right_voltage_v)
    if not all(np.isfinite(v) for v in scalars):
        raise ValueError('Geometry and voltages must be finite')
    if box_width_m <= 0 or left_radius_m <= 0 or right_radius_m <= 0:
        raise ValueError('Width and radii must be positive')

    # Continuous geometry validation before rasterization (R5-F3)
    half_w = box_width_m / 2.0
    for name, cx, cy, rad in (
        ('left electrode', left_center_x_m, left_center_y_m, left_radius_m),
        ('right electrode', right_center_x_m, right_center_y_m, right_radius_m),
    ):
        if abs(cx) + rad >= half_w or abs(cy) + rad >= half_w:
            raise ValueError(f'{name.capitalize()} penetrates or touches grounded enclosure boundary')

    center_dist = float(np.hypot(right_center_x_m - left_center_x_m, right_center_y_m - left_center_y_m))
    if center_dist <= (left_radius_m + right_radius_m):
        raise ValueError('Electrodes intersect or touch in continuous space')
    h = box_width_m / (n-1)
    coords = np.linspace(-box_width_m/2, box_width_m/2, n)
    x, y = np.meshgrid(coords, coords, indexing='ij')
    left = (x - left_center_x_m)**2 + (y - left_center_y_m)**2 <= left_radius_m**2
    right = (x - right_center_x_m)**2 + (y - right_center_y_m)**2 <= right_radius_m**2
    if np.any(left & right) or not np.any(left) or not np.any(right):
        raise ValueError('Electrodes overlap or are too small for the grid')
    for disk in (left, right):
        if (disk[0,:].any() or disk[-1,:].any() or
            disk[:,0].any() or disk[:,-1].any()):
            raise ValueError('Electrodes must not touch the grounded enclosure')

    boundary_mask = np.zeros((n, n), dtype=bool)
    boundary_mask[0, :] = boundary_mask[-1, :] = True
    boundary_mask[:, 0] = boundary_mask[:, -1] = True

    conductor_mask = left | right
    fixed_mask = boundary_mask | conductor_mask

    fixed_potential = np.zeros((n, n), dtype=float)
    fixed_potential[left] = left_voltage_v
    fixed_potential[right] = right_voltage_v

    return solve_dirichlet(
        fixed_mask, fixed_potential, h,
        conductor_mask=conductor_mask,
        boundary_mask=boundary_mask,
        config=config,
    )


def check_configuration_symmetries(
    config: GroundedBoxConfig,
    solution: FieldSolution | None = None,
) -> dict[str, bool]:
    """Check whether electrode configuration satisfies exact discrete Laplace symmetry preconditions.

    Exact criteria (no loose floating-point tolerances that mask boundary defects):
    1. x-reflection antisymmetry: V(-x, y) = -V(x, y)
       Preconditions:
         - r_left == r_right > 0
         - x_right == -x_left != 0
         - y_right == y_left
         - V_right == -V_left != 0

    2. Central-inversion antisymmetry: V(-x, -y) = -V(x, y)
       Preconditions:
         - r_left == r_right > 0
         - x_right == -x_left != 0
         - y_right == -y_left
         - V_right == -V_left != 0

    If solution is provided, also checks discrete transformed fixed masks and potentials exactly:
       - x-reflection: fixed_mask == fixed_mask[::-1, :] and
                       conductor_mask == conductor_mask[::-1, :] and
                       potential_v[fixed_mask] + potential_v[::-1, :][fixed_mask] == 0.0
       - central inversion: fixed_mask == fixed_mask[::-1, ::-1] and
                            conductor_mask == conductor_mask[::-1, ::-1] and
                            potential_v[fixed_mask] + potential_v[::-1, ::-1][fixed_mask] == 0.0
    """
    le = config.left_electrode
    re = config.right_electrode

    r_equal = (le.radius_m == re.radius_m) and (le.radius_m > 0.0)
    x_antisym = (re.center_x_m == -le.center_x_m) and (le.center_x_m != 0.0)
    v_antisym = (re.voltage_v == -le.voltage_v) and (le.voltage_v != 0.0)

    y_equal = (le.center_y_m == re.center_y_m)
    y_antisym = (re.center_y_m == -le.center_y_m)

    x_reflection = bool(r_equal and x_antisym and v_antisym and y_equal)
    central_inversion = bool(r_equal and x_antisym and v_antisym and y_antisym)

    if solution is not None:
        if x_reflection:
            mask_ok = (
                np.array_equal(solution.fixed_mask, solution.fixed_mask[::-1, :])
                and np.array_equal(solution.conductor_mask, solution.conductor_mask[::-1, :])
            )
            pot_ok = bool(mask_ok and np.all(
                solution.potential_v[solution.fixed_mask] + solution.potential_v[::-1, :][solution.fixed_mask] == 0.0
            ))
            x_reflection = bool(x_reflection and pot_ok)
        if central_inversion:
            mask_ok = (
                np.array_equal(solution.fixed_mask, solution.fixed_mask[::-1, ::-1])
                and np.array_equal(solution.conductor_mask, solution.conductor_mask[::-1, ::-1])
            )
            pot_ok = bool(mask_ok and np.all(
                solution.potential_v[solution.fixed_mask] + solution.potential_v[::-1, ::-1][solution.fixed_mask] == 0.0
            ))
            central_inversion = bool(central_inversion and pot_ok)

    return {
        'has_x_reflection_antisymmetry': x_reflection,
        'has_central_inversion_antisymmetry': central_inversion,
    }


def check_discrete_symmetries(
    solution: FieldSolution,
    config: GroundedBoxConfig | None = None,
) -> dict[str, bool]:
    """Check whether discrete solution and grid masks satisfy exact discrete Laplace symmetry."""
    cfg = config or solution.config or GroundedBoxConfig()
    return check_configuration_symmetries(cfg, solution=solution)


@dataclass(frozen=True)
class MeshRefinementResult:
    n: int
    grid_spacing_m: float
    probe_x_m: float
    probe_y_m: float
    probe_potential_v: float
    probe_ex_v_per_m: float | None
    probe_ey_v_per_m: float | None
    max_vacuum_e_v_per_m: float
    max_conductor_raw_gradient_v_per_m: float
    max_discrete_residual_v: float
    potential_antisymmetry_error_v: float | None
    potential_central_inversion_error_v: float | None = None
    probe_in_vacuum: bool = True
    probe_status: str = 'VALID_VACUUM'
    symmetry_status: str = 'N/A'
    requested_probe_x_m: float = 0.0
    requested_probe_y_m: float = 0.0


def electrode_pair_mesh_study(
    n_list: Sequence[int] = (41, 81, 101, 161),
    box_width_m: float = 0.04,
    probe_xy_m: tuple[float, float] = (0.0, 0.0),
    config: GroundedBoxConfig | None = None,
    require_vacuum_probe: bool = False,
) -> list[MeshRefinementResult]:
    """Perform mesh-refinement study for cylindrical electrode pair in grounded enclosure.

    Demonstrates that:
    1. Probe field at fixed physical point in vacuum converges smoothly when evaluated on-grid.
    2. Peak vacuum field on the staircase boundary varies significantly with n (grid sensitivity).
    3. Fictitious gradient inside conductors on raw grid is nonzero while physical vacuum E is masked.
    4. Evaluates potential antisymmetry (x-reflection or central inversion) only when exact mathematical
       and discrete symmetry preconditions are met; otherwise records N/A to prevent nonphysical error reporting.
    """
    results: list[MeshRefinementResult] = []
    base_config = config or GroundedBoxConfig(box_width_m=box_width_m)
    for n in n_list:
        run_config = GroundedBoxConfig(
            n=n,
            box_width_m=base_config.box_width_m,
            left_electrode=base_config.left_electrode,
            right_electrode=base_config.right_electrode,
        )
        sol = electrode_pair_in_grounded_box(config=run_config)
        coords = np.linspace(-run_config.box_width_m / 2, run_config.box_width_m / 2, n)

        ix = int(np.argmin(np.abs(coords - probe_xy_m[0])))
        iy = int(np.argmin(np.abs(coords - probe_xy_m[1])))

        probe_in_vac = bool(sol.vacuum_mask[ix, iy])
        if require_vacuum_probe and not probe_in_vac:
            raise ValueError(
                f"Probe at ({probe_xy_m[0]:.4f}, {probe_xy_m[1]:.4f}) is not in vacuum at n={n} "
                f"(located in conductor={sol.conductor_mask[ix, iy]} or boundary={sol.boundary_mask[ix, iy]})"
            )

        probe_v = float(sol.potential_v[ix, iy])
        if probe_in_vac:
            probe_ex: float | None = float(sol.ex_v_per_m[ix, iy])
            probe_ey: float | None = float(sol.ey_v_per_m[ix, iy])
            probe_status = 'VALID_VACUUM'
        else:
            probe_ex = None
            probe_ey = None
            probe_status = (
                f'NON_VACUUM (probe at [{coords[ix]:.4e}, {coords[iy]:.4e}] inside conductor or boundary; '
                'vacuum field undefined / masked to E=0)'
            )

        vac_e = sol.vacuum_e_magnitude_v_per_m
        max_vac_e = float(np.nanmax(vac_e)) if np.any(sol.vacuum_mask) else 0.0

        raw_mag = np.hypot(sol.raw_gradient_x_v_per_m, sol.raw_gradient_y_v_per_m)
        max_cond_raw = float(np.max(raw_mag[sol.conductor_mask])) if np.any(sol.conductor_mask) else 0.0

        sym_info = check_configuration_symmetries(run_config, solution=sol)
        if sym_info['has_x_reflection_antisymmetry']:
            antisym_err: float | None = float(np.max(np.abs(sol.potential_v + sol.potential_v[::-1, :])))
        else:
            antisym_err = None

        if sym_info['has_central_inversion_antisymmetry']:
            central_inv_err: float | None = float(np.max(np.abs(sol.potential_v + sol.potential_v[::-1, ::-1])))
        else:
            central_inv_err = None

        if sym_info['has_x_reflection_antisymmetry'] and sym_info['has_central_inversion_antisymmetry']:
            sym_status = 'X_REFLECTION_AND_CENTRAL_INVERSION_ANTISYMMETRIC'
        elif sym_info['has_x_reflection_antisymmetry']:
            sym_status = 'X_REFLECTION_ANTISYMMETRIC'
        elif sym_info['has_central_inversion_antisymmetry']:
            sym_status = 'CENTRAL_INVERSION_ANTISYMMETRIC'
        else:
            sym_status = 'N/A (asymmetric geometry or potentials)'

        results.append(MeshRefinementResult(
            n=n,
            grid_spacing_m=sol.grid_spacing_m,
            probe_x_m=float(coords[ix]),
            probe_y_m=float(coords[iy]),
            probe_potential_v=probe_v,
            probe_ex_v_per_m=probe_ex,
            probe_ey_v_per_m=probe_ey,
            max_vacuum_e_v_per_m=max_vac_e,
            max_conductor_raw_gradient_v_per_m=max_cond_raw,
            max_discrete_residual_v=sol.max_discrete_residual_v,
            potential_antisymmetry_error_v=antisym_err,
            potential_central_inversion_error_v=central_inv_err,
            probe_in_vacuum=probe_in_vac,
            probe_status=probe_status,
            symmetry_status=sym_status,
            requested_probe_x_m=float(probe_xy_m[0]),
            requested_probe_y_m=float(probe_xy_m[1]),
        ))
    return results


@dataclass(frozen=True)
class ProbeConvergenceAssessment:
    vacuum_status: str              # 'ALL_IN_VACUUM', 'NON_VACUUM', or 'UNKNOWN'
    convergence_status: str         # 'CONVERGED', 'INCONCLUSIVE', or 'NOT_ASSESSED'
    assessment_summary: str
    requested_probe_xy_m: tuple[float, float]
    sampled_probe_coords: list[tuple[float, float]]
    coords_stable: bool
    relative_field_drift: float | None = None
    is_converged: bool = False


def assess_probe_convergence(
    study_results: Sequence[MeshRefinementResult],
    requested_probe_xy_m: tuple[float, float] = (0.0, 0.0),
    max_relative_drift_tol: float = 0.05,
) -> ProbeConvergenceAssessment:
    """R5-F2: Rigorously assess probe convergence distinguishing vacuum validity from quantitative convergence.

    Conditions for positive 'CONVERGED' assessment:
    1. Vacuum validity: all probe samples must be in vacuum (no conductor/boundary samples).
    2. Sufficient mesh resolutions: at least 3 distinct resolutions (1-row or 2-row studies cannot verify convergence).
    3. Coordinate stability: sampled probe coordinates across all resolutions must be fixed and match requested target.
    4. Quantitative convergence: relative variation (max - min) / min of field magnitude across resolutions must be within tolerance.

    If any condition is not met, fails closed to 'NOT_ASSESSED' or 'INCONCLUSIVE'.
    """
    if not study_results:
        return ProbeConvergenceAssessment(
            vacuum_status='UNKNOWN',
            convergence_status='NOT_ASSESSED',
            assessment_summary='NOT_ASSESSED: No mesh refinement results provided.',
            requested_probe_xy_m=requested_probe_xy_m,
            sampled_probe_coords=[],
            coords_stable=False,
            relative_field_drift=None,
            is_converged=False,
        )

    sampled_coords = [(r.probe_x_m, r.probe_y_m) for r in study_results]
    all_vac = all(r.probe_in_vacuum for r in study_results)

    if not all_vac:
        return ProbeConvergenceAssessment(
            vacuum_status='NON_VACUUM',
            convergence_status='NOT_ASSESSED',
            assessment_summary=(
                'NON_VACUUM: Probe point is located inside conductor or boundary on one or more mesh resolutions. '
                'Physical vacuum electric field is masked (E=0 in ideal conductor; vacuum E undefined). '
                'Quantitative convergence NOT_ASSESSED.'
            ),
            requested_probe_xy_m=requested_probe_xy_m,
            sampled_probe_coords=sampled_coords,
            coords_stable=False,
            relative_field_drift=None,
            is_converged=False,
        )

    # All in vacuum: check number of resolutions
    if len(study_results) < 3:
        return ProbeConvergenceAssessment(
            vacuum_status='ALL_IN_VACUUM',
            convergence_status='NOT_ASSESSED',
            assessment_summary=(
                f'NOT_ASSESSED: Insufficient mesh resolutions ({len(study_results)} row(s) provided). '
                'At least 3 distinct mesh resolutions are required to evaluate quantitative convergence.'
            ),
            requested_probe_xy_m=requested_probe_xy_m,
            sampled_probe_coords=sampled_coords,
            coords_stable=False,
            relative_field_drift=None,
            is_converged=False,
        )

    # Check coordinate stability / alignment with requested target
    req_x, req_y = requested_probe_xy_m
    coord_drift = [
        float(np.hypot(x - req_x, y - req_y))
        for x, y in sampled_coords
    ]
    coords_stable = (
        all(d < 1e-12 for d in coord_drift)
        and all(c == sampled_coords[0] for c in sampled_coords)
    )

    if not coords_stable:
        return ProbeConvergenceAssessment(
            vacuum_status='ALL_IN_VACUUM',
            convergence_status='INCONCLUSIVE',
            assessment_summary=(
                f'INCONCLUSIVE: Sampled probe coordinates drift or deviate from requested point '
                f'({req_x:.4e}, {req_y:.4e}) due to nearest-grid sampling across mesh resolutions. '
                f'Sampled coordinates: {sampled_coords}. Fixed-point convergence cannot be verified.'
            ),
            requested_probe_xy_m=requested_probe_xy_m,
            sampled_probe_coords=sampled_coords,
            coords_stable=False,
            relative_field_drift=None,
            is_converged=False,
        )

    # Evaluate quantitative field values
    e_mags = []
    for r in study_results:
        if r.probe_ex_v_per_m is None or r.probe_ey_v_per_m is None:
            return ProbeConvergenceAssessment(
                vacuum_status='ALL_IN_VACUUM',
                convergence_status='NOT_ASSESSED',
                assessment_summary='NOT_ASSESSED: Missing electric field values in study results.',
                requested_probe_xy_m=requested_probe_xy_m,
                sampled_probe_coords=sampled_coords,
                coords_stable=True,
                relative_field_drift=None,
                is_converged=False,
            )
        e_mags.append(float(np.hypot(r.probe_ex_v_per_m, r.probe_ey_v_per_m)))

    min_e = min(e_mags)
    max_e = max(e_mags)
    denom = min_e if min_e > 1e-12 else (max_e if max_e > 1e-12 else 1.0)
    relative_drift = float((max_e - min_e) / denom)

    # Check for wild drift
    if relative_drift > max_relative_drift_tol:
        return ProbeConvergenceAssessment(
            vacuum_status='ALL_IN_VACUUM',
            convergence_status='INCONCLUSIVE',
            assessment_summary=(
                f'INCONCLUSIVE: Probe field at fixed point ({req_x:.4e}, {req_y:.4e}) exhibits significant '
                f'numerical drift across mesh resolutions (relative drift = {relative_drift:.2%}); '
                f'smooth convergence not verified.'
            ),
            requested_probe_xy_m=requested_probe_xy_m,
            sampled_probe_coords=sampled_coords,
            coords_stable=True,
            relative_field_drift=relative_drift,
            is_converged=False,
        )

    return ProbeConvergenceAssessment(
        vacuum_status='ALL_IN_VACUUM',
        convergence_status='CONVERGED',
        assessment_summary=(
            f'CONVERGED: Probe field at fixed point ({req_x:.4e}, {req_y:.4e}) is in vacuum across all '
            f'{len(study_results)} mesh resolutions and converges smoothly (relative drift = {relative_drift:.2%}).'
        ),
        requested_probe_xy_m=requested_probe_xy_m,
        sampled_probe_coords=sampled_coords,
        coords_stable=True,
        relative_field_drift=relative_drift,
        is_converged=True,
    )


def format_voltage_title(v_left_v: float, v_right_v: float) -> str:
    """Format voltage label for Panel A title using exact symmetry criteria.

    - Exactly symmetric: v_left == -v_right and v_left != 0.0 -> '±{V} V'
    - Asymmetric or near-symmetric: 'V_left={V_left} V, V_right={V_right} V'
    """
    if v_left_v == -v_right_v and v_left_v != 0.0:
        if float(v_left_v).is_integer():
            return f'±{abs(v_left_v):.0f} V'
        return f'±{abs(v_left_v):g} V'

    def _fmt(val: float) -> str:
        if float(val).is_integer():
            return f'{val:+.0f} V'
        return f'{val:+} V' if not f'{val:+}'.endswith('.0') else f'{val:+.0f} V'

    return f'V_left={_fmt(v_left_v)}, V_right={_fmt(v_right_v)}'


def format_panel_a_title(cfg: GroundedBoxConfig) -> str:
    """Return the complete Panel A figure title string."""
    v_label = format_voltage_title(cfg.left_electrode.voltage_v, cfg.right_electrode.voltage_v)
    return f'A · Case 1: Grounded Box ({v_label})\nDirichlet Potential (V)'



@dataclass(frozen=True)
class CoaxialBenchmarkResult:
    n: int
    grid_spacing_m: float
    probe_r_m: float
    analytic_potential_v: float
    numerical_potential_v: float
    potential_error_v: float
    analytic_field_er_v_per_m: float
    numerical_field_ex_v_per_m: float
    field_error_v_per_m: float


def coaxial_cylinder_benchmark(
    n_list: Sequence[int] = (41, 81, 161),
    box_width_m: float = 0.04,
    r_inner_m: float = 0.005,
    r_outer_m: float = 0.015,
    v_inner_v: float = 100.0,
    v_outer_v: float = 0.0,
    probe_r_m: float = 0.010,
) -> list[CoaxialBenchmarkResult]:
    """Source-backed analytic benchmark: coaxial cylinders in 2D Laplace solver.

    Analytic potential in vacuum (r_inner <= r <= r_outer):
      V(r) = V_inner + (V_outer - V_inner) * ln(r / r_inner) / ln(r_outer / r_inner)
      E_r(r) = (V_inner - V_outer) / (ln(r_outer / r_inner) * r)

    Verifies that potential and field errors at fixed physical probe point r_probe
    decrease monotonically with grid refinement h.
    """
    benchmarks: list[CoaxialBenchmarkResult] = []

    for n in n_list:
        h = box_width_m / (n - 1)
        coords = np.linspace(-box_width_m / 2, box_width_m / 2, n)
        x, y = np.meshgrid(coords, coords, indexing='ij')
        r = np.hypot(x, y)

        inner = (r <= r_inner_m)
        outer = (r >= r_outer_m)
        outer[0, :] = outer[-1, :] = outer[:, 0] = outer[:, -1] = True

        mask = inner | outer
        fixed = np.zeros((n, n), dtype=float)
        fixed[inner] = v_inner_v
        fixed[outer] = v_outer_v

        sol = solve_dirichlet(mask, fixed, h, conductor_mask=inner, boundary_mask=outer)

        ix = int(np.argmin(np.abs(coords - probe_r_m)))
        iy = (n - 1) // 2
        actual_x = float(coords[ix])

        analytic_v = v_inner_v + (v_outer_v - v_inner_v) * np.log(actual_x / r_inner_m) / np.log(r_outer_m / r_inner_m)
        analytic_er = (v_inner_v - v_outer_v) / (np.log(r_outer_m / r_inner_m) * actual_x)

        num_v = float(sol.potential_v[ix, iy])
        num_ex = float(sol.ex_v_per_m[ix, iy])

        err_v = abs(num_v - analytic_v)
        err_ex = abs(num_ex - analytic_er)

        benchmarks.append(CoaxialBenchmarkResult(
            n=n,
            grid_spacing_m=h,
            probe_r_m=actual_x,
            analytic_potential_v=analytic_v,
            numerical_potential_v=num_v,
            potential_error_v=err_v,
            analytic_field_er_v_per_m=analytic_er,
            numerical_field_ex_v_per_m=num_ex,
            field_error_v_per_m=err_ex,
        ))
    return benchmarks
