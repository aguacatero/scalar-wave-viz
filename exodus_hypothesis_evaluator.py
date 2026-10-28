"""Exodus patent US11511891B2 hypothesis comparison and force accounting evaluator.

Implements:
    H0: Conventional Maxwell-stress electrostatics (momentum-conserving baseline)
        - 2D section closed-contour line integrals (N/m) and clearly labeled 2D*Lz extrusion (N)
        - Constrained 3D finite-difference model with full 6-face 3D Maxwell stress integration
          and independent 3D enclosure wall traction accounting (N)
        - Direct wall traction integration on outer grounded enclosure (non-tautological net force sum)
        - Korteweg-Helmholtz dielectric boundary/material reaction accounting for nonuniform epsilon_r
        - Analytic parallel-plate capacitor benchmark, contour-offset sweep, and enclosure-clearance sweep
    H1: Patent-specific alternative hypothesis (US11511891B2 Eq. 4-11 transcription)
        - Explicit material-side boundary face quadrature and mean-field plug-in comparison
        - Correct corresponding face areas (w_proximal and w_distal)
        - Mathematical proof-obligation audit (refutation of Eq. 4 stationary action step)
    H2: Evaluated numerical controls and independent contextual literature comparison
        - Computed polarity reversal control (+V vs -V field and force invariance)
        - Computed symmetric electrode control
        - Computed zero-voltage control (V = 0)
        - Computed 180-degree spatial inversion control (actual BVP solve on mirrored grid)
        - Computed asymmetric enclosure wall proximity sensitivity (image-charge coupling control)
        - Contextual literature audit of Tajmar & Schreiber (2020) vs Patent FIGS. 21-22
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, replace
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from exodus_patent_geometry import (
    EPSILON_0,
    ConductorBoundaryFace,
    ExodusGrid2D,
    ExodusPatentParameters,
    build_exodus_2d_grid,
    build_inverted_180_grid,
    build_symmetric_control_grid,
    get_patent_parameter_ledger,
)


@dataclass(frozen=True)
class MaxwellStressContourForces:
    """Forces computed via closed-contour Maxwell stress tensor integration.

    Units:
        force_per_length_n_per_m: 2D line-integral force per unit depth (N/m)
        force_3d_extruded_n: Extruded 2D approximation over length Lz (N);
                             not a 3D end-fringing validated force
    """

    force_per_length_n_per_m: float
    force_3d_extruded_n: float
    ix_min: int = 0
    ix_max: int = 0
    iy_min: int = 0
    iy_max: int = 0
    dimensional_status: str = "EXTRUDED_2D_APPROXIMATION_NOT_VALIDATED_FOR_3D_ARTICLE"


@dataclass(frozen=True)
class DirectWallTractionForces:
    """Forces on the grounded outer enclosure computed directly at the 4 wall surfaces."""

    left_wall_force_x_n_per_m: float
    right_wall_force_x_n_per_m: float
    top_wall_force_x_n_per_m: float
    bottom_wall_force_x_n_per_m: float
    total_enclosure_force_x_n_per_m: float
    total_enclosure_force_3d_extruded_n: float


@dataclass(frozen=True)
class WholeApparatusForceLedgerH0:
    """Conventional whole-system force accounting under Model H0.

    net_system_force_x is computed as the independent sum of:
        blade_force_x + ground_force_x + dielectric_force_x + enclosure_direct_wall_force_x
    """

    blade_force_x: MaxwellStressContourForces
    ground_force_x: MaxwellStressContourForces
    dielectric_force_x: MaxwellStressContourForces
    potted_article_total_force_x: MaxwellStressContourForces
    enclosure_inner_contour_force_x: MaxwellStressContourForces
    enclosure_direct_wall_force_x: DirectWallTractionForces
    net_system_force_x: MaxwellStressContourForces
    is_momentum_conserved: bool
    residual_n_per_m: float
    residual_3d_extruded_n: float
    relative_residual_to_blade_force: float


@dataclass(frozen=True)
class PatentHypothesisResultH1:
    """Patent alternative force calculation under Model H1 (US11511891B2 Eq. 11).

    Evaluated via strict material-side boundary face quadrature with correct corresponding face areas,
    alongside mean-field plug-in comparison.
    """

    proximal_face_integral_e2_dl: float          # integral_{100a} |E|^2 dl in (V^2/m)
    distal_face_integral_e2_dl: float            # integral_{101a} |E|^2 dl in (V^2/m)
    proximal_width_m: float                      # w2: total proximal blade tip width
    distal_width_m: float                        # w1: base plate rear width
    effective_proximal_field_v_per_m: float      # RMS field sqrt(integral / w2)
    effective_distal_field_v_per_m: float        # RMS field sqrt(integral / w1)
    mean_proximal_field_v_per_m: float           # Spatial mean <E> on 100a
    mean_distal_field_v_per_m: float             # Spatial mean <E> on 101a

    predicted_force_per_length_n_per_m: float    # eps0 * (integral_100a - integral_101a)
    mean_field_plugin_force_per_length_n_per_m: float  # eps0 * (<E2>^2 * w2 - <E1>^2 * w1)
    predicted_force_3d_extruded_n: float         # Extruded over Lz
    missing_half_factor_force_3d_extruded_n: float  # 0.5 * F_H1 (1/2 factor only; still omits reactions)

    proof_obligation_notes: List[str]


@dataclass(frozen=True)
class LiteratureBenchmarkAudit:
    """Structured audit of Tajmar & Schreiber (2020) and US11511891B2 FIGS. 21-22."""

    tajmar_schreiber_citation: str
    tajmar_schreiber_doi: str
    tajmar_schreiber_max_voltage_v: float
    tajmar_schreiber_mass_accuracy_mg: float
    tajmar_schreiber_force_accuracy_n: float
    tajmar_schreiber_apparatus: str
    tajmar_schreiber_finding: str

    patent_fig21_citation: str
    patent_fig21_test_voltage_v: float
    patent_fig21_max_supply_voltage_v: float
    patent_fig21_num_blades: int
    patent_fig21_dielectric: str
    patent_fig21_environment: str
    patent_fig21_reported_force_n: float
    patent_fig21_uncertainty_status: str

    comparison_status: str
    candidate_confounders_not_established_causes: List[str]


@dataclass(frozen=True)
class EvaluatedControlsResult:
    """Rigorous evaluation of programmatic controls executed directly in the solver."""

    # 1. Polarity reversal control: V -> -V
    polarity_reversal_evaluated: bool
    polarity_reversal_max_field_diff_relative: float
    polarity_reversal_blade_force_diff_relative: float

    # 2. Symmetric electrode control
    symmetric_control_evaluated: bool
    symmetric_blade_force_n_per_m: float
    symmetric_ground_force_n_per_m: float
    symmetric_control_net_force_n_per_m: float
    symmetric_control_net_force_3d_n: float

    # 3. Voltage-off control: V = 0
    voltage_off_evaluated: bool
    voltage_off_max_field_v_per_m: float
    voltage_off_blade_force_n_per_m: float

    # 4. 180-degree spatial inversion control (mirrored BVP solve)
    inversion_180_evaluated: bool
    inversion_180_base_blade_force_x_n_per_m: float
    inversion_180_inverted_blade_force_x_n_per_m: float
    inversion_180_relative_reversal_error: float
    inversion_180_vector_reversed: bool

    # 5. Asymmetric enclosure wall proximity control (fixture / wall image-charge coupling)
    wall_proximity_control_evaluated: bool
    wall_proximity_symmetric_pair_force_n_per_m: float
    wall_proximity_asymmetric_pair_force_n_per_m: float
    wall_proximity_asymmetric_wall_reaction_n_per_m: float
    wall_proximity_asymmetric_net_residual_n_per_m: float

    # 6. Laboratory physical controls (unperformed in numerical model)
    physical_controls_status: str
    unperformed_physical_controls: List[str]

    # 7. Audited literature benchmark
    literature_audit: LiteratureBenchmarkAudit
    literature_benchmark_citation: str
    literature_benchmark_summary: str


@dataclass(frozen=True)
class Finite3DModelResult:
    """Results from constrained finite 3D boundary-value model capturing 3D end fringing."""

    nx: int
    ny: int
    nz: int
    dx_m: float
    dy_m: float
    dz_m: float
    finite_blade_length_m: float
    solver_residual: float
    true_3d_blade_force_x_n: float
    true_3d_ground_force_x_n: float
    true_3d_dielectric_force_x_n: float
    true_3d_enclosure_force_x_n: float
    true_3d_net_system_force_x_n: float
    true_3d_relative_residual: float
    true_3d_is_conserved: bool
    extruded_2d_blade_force_at_matched_dx_n: float
    end_fringing_ratio_3d_to_extruded_2d: float


@dataclass
class ExodusEvaluationResult:
    """Complete evaluation comparing H0 conventional electrostatics vs H1 patent prediction."""

    params: ExodusPatentParameters
    grid: ExodusGrid2D
    potential_v: np.ndarray
    e_field_x_v_per_m: np.ndarray
    e_field_y_v_per_m: np.ndarray
    e_field_magnitude_v_per_m: np.ndarray
    h0_ledger: WholeApparatusForceLedgerH0
    h1_prediction: PatentHypothesisResultH1
    controls: EvaluatedControlsResult
    finite_3d_model: Finite3DModelResult
    solver_iterations: int
    solver_residual: float


# ==============================================================================
# 2D Finite Difference Solver and Field Calculation
# ==============================================================================

def solve_exodus_electrostatics(grid: ExodusGrid2D) -> Tuple[np.ndarray, int, float]:
    """Solve 2D variable-permittivity Laplace equation nabla . (epsilon nabla V) = 0."""
    nx = grid.nx
    ny = grid.ny
    dx = grid.dx
    dy = grid.dy
    eps = grid.permittivity_map
    fixed = grid.fixed_mask
    bc = grid.potential_bc

    n_unknowns = nx * ny

    # Harmonic mean for interface permittivity
    eps_x_plus = np.zeros((ny, nx))
    eps_x_plus[:, :-1] = 2.0 * eps[:, :-1] * eps[:, 1:] / (eps[:, :-1] + eps[:, 1:])

    eps_x_minus = np.zeros((ny, nx))
    eps_x_minus[:, 1:] = 2.0 * eps[:, 1:] * eps[:, :-1] / (eps[:, 1:] + eps[:, :-1])

    eps_y_plus = np.zeros((ny, nx))
    eps_y_plus[:-1, :] = 2.0 * eps[:-1, :] * eps[1:, :] / (eps[:-1, :] + eps[1:, :])

    eps_y_minus = np.zeros((ny, nx))
    eps_y_minus[1:, :] = 2.0 * eps[1:, :] * eps[:-1, :] / (eps[1:, :] + eps[:-1, :])

    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)

    idx_grid = np.arange(n_unknowns).reshape((ny, nx))
    fixed_flat = fixed.ravel()
    free_mask = ~fixed_flat
    free_indices = idx_grid[free] if False else np.where(free_mask)[0]

    # Diagonal entries for fixed nodes
    fixed_indices = np.where(fixed_flat)[0]
    rows_list = [fixed_indices]
    cols_list = [fixed_indices]
    data_list = [np.ones_like(fixed_indices, dtype=float)]

    # Entries for interior free nodes (strictly 1 <= j <= ny-2, 1 <= i <= nx-2 since boundary is fixed)
    fy, fx = np.where(~fixed)
    f_idx = fy * nx + fx

    c_xp = eps_x_plus[fy, fx] * inv_dx2
    c_xm = eps_x_minus[fy, fx] * inv_dx2
    c_yp = eps_y_plus[fy, fx] * inv_dy2
    c_ym = eps_y_minus[fy, fx] * inv_dy2
    c_center = -(c_xp + c_xm + c_yp + c_ym)

    rows_list.extend([f_idx, f_idx, f_idx, f_idx, f_idx])
    cols_list.extend([f_idx, f_idx + 1, f_idx - 1, f_idx + nx, f_idx - nx])
    data_list.extend([c_center, c_xp, c_xm, c_yp, c_ym])

    rows = np.concatenate(rows_list)
    cols = np.concatenate(cols_list)
    data = np.concatenate(data_list)

    rhs = np.zeros(n_unknowns, dtype=float)
    rhs[fixed_indices] = bc.ravel()[fixed_indices]

    a_mat = sp.csr_matrix((data, (rows, cols)), shape=(n_unknowns, n_unknowns))
    sol = spla.spsolve(a_mat, rhs)
    potential = sol.reshape((ny, nx))

    rhs_norm = np.linalg.norm(rhs)
    res = float(np.linalg.norm(a_mat.dot(sol) - rhs) / (rhs_norm if rhs_norm > 0 else 1.0))
    return potential, 1, res


def compute_electric_fields(
    grid: ExodusGrid2D, potential: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute physical electric field E = -grad(V)."""
    dx = grid.dx
    dy = grid.dy

    ex = np.zeros_like(potential)
    ey = np.zeros_like(potential)

    ex[:, 1:-1] = -(potential[:, 2:] - potential[:, :-2]) / (2.0 * dx)
    ey[1:-1, :] = -(potential[2:, :] - potential[:-2, :]) / (2.0 * dy)

    ex[:, 0] = -(potential[:, 1] - potential[:, 0]) / dx
    ex[:, -1] = -(potential[:, -1] - potential[:, -2]) / dx
    ey[0, :] = -(potential[1, :] - potential[0, :]) / dy
    ey[-1, :] = -(potential[-1, :] - potential[-2, :]) / dy

    e_mag = np.sqrt(ex * ex + ey * ey)
    return ex, ey, e_mag


# ==============================================================================
# H0: Maxwell Stress Integration, Direct Wall Traction & Dielectric Reaction
# ==============================================================================

def _validate_contour_in_free_medium(
    grid: ExodusGrid2D, ix_min: int, ix_max: int, iy_min: int, iy_max: int
) -> None:
    """Ensure a rectangular contour does not cut through any conductor mask."""
    if not (0 < ix_min < ix_max < grid.nx - 1 and 0 < iy_min < iy_max < grid.ny - 1):
        raise ValueError(
            f"Contour [{ix_min}, {ix_max}] x [{iy_min}, {iy_max}] out of interior domain bounds."
        )
    cond = grid.fixed_mask
    if (
        np.any(cond[iy_min:iy_max + 1, ix_min])
        or np.any(cond[iy_min:iy_max + 1, ix_max])
        or np.any(cond[iy_min, ix_min:ix_max + 1])
        or np.any(cond[iy_max, ix_min:ix_max + 1])
    ):
        raise ValueError(
            f"Maxwell stress contour [{ix_min}, {ix_max}] x [{iy_min}, {iy_max}] intersects a conductor."
        )


def integrate_maxwell_stress_x(
    grid: ExodusGrid2D,
    ex: np.ndarray,
    ey: np.ndarray,
    ix_min: int,
    ix_max: int,
    iy_min: int,
    iy_max: int,
    strict: bool = True,
) -> float:
    """Integrate 2D Maxwell stress tensor for force in x along a closed rectangular contour."""
    if strict:
        _validate_contour_in_free_medium(grid, ix_min, ix_max, iy_min, iy_max)

    dx = grid.dx
    dy = grid.dy
    eps_map = grid.permittivity_map

    # Right face (x = ix_max, outward normal = +x)
    eps_r_right = 0.5 * (eps_map[iy_min:iy_max, ix_max] + eps_map[iy_min + 1:iy_max + 1, ix_max])
    ex_right = 0.5 * (ex[iy_min:iy_max, ix_max] + ex[iy_min + 1:iy_max + 1, ix_max])
    ey_right = 0.5 * (ey[iy_min:iy_max, ix_max] + ey[iy_min + 1:iy_max + 1, ix_max])
    fx_right = float(np.sum(0.5 * EPSILON_0 * eps_r_right * (ex_right ** 2 - ey_right ** 2)) * dy)

    # Left face (x = ix_min, outward normal = -x)
    eps_r_left = 0.5 * (eps_map[iy_min:iy_max, ix_min] + eps_map[iy_min + 1:iy_max + 1, ix_min])
    ex_left = 0.5 * (ex[iy_min:iy_max, ix_min] + ex[iy_min + 1:iy_max + 1, ix_min])
    ey_left = 0.5 * (ey[iy_min:iy_max, ix_min] + ey[iy_min + 1:iy_max + 1, ix_min])
    fx_left = -float(np.sum(0.5 * EPSILON_0 * eps_r_left * (ex_left ** 2 - ey_left ** 2)) * dy)

    # Top face (y = iy_max, outward normal = +y)
    eps_r_top = 0.5 * (eps_map[iy_max, ix_min:ix_max] + eps_map[iy_max, ix_min + 1:ix_max + 1])
    ex_top = 0.5 * (ex[iy_max, ix_min:ix_max] + ex[iy_max, ix_min + 1:ix_max + 1])
    ey_top = 0.5 * (ey[iy_max, ix_min:ix_max] + ey[iy_max, ix_min + 1:ix_max + 1])
    fx_top = float(np.sum(EPSILON_0 * eps_r_top * ex_top * ey_top) * dx)

    # Bottom face (y = iy_min, outward normal = -y)
    eps_r_bot = 0.5 * (eps_map[iy_min, ix_min:ix_max] + eps_map[iy_min, ix_min + 1:ix_max + 1])
    ex_bot = 0.5 * (ex[iy_min, ix_min:ix_max] + ex[iy_min, ix_min + 1:ix_max + 1])
    ey_bot = 0.5 * (ey[iy_min, ix_min:ix_max] + ey[iy_min, ix_min + 1:ix_max + 1])
    fx_bot = -float(np.sum(EPSILON_0 * eps_r_bot * ex_bot * ey_bot) * dx)

    return fx_right + fx_left + fx_top + fx_bot


def compute_direct_enclosure_wall_tractions(
    grid: ExodusGrid2D, ex: np.ndarray, ey: np.ndarray
) -> DirectWallTractionForces:
    """Compute direct electrostatic surface traction on the 4 grounded outer enclosure walls.

    Evaluates the inward-pointing wall surface stress vector T . n_wall on the inner
    adjacent layer of the 4 grounded enclosure walls (ix = 1, ix = nx - 2, iy = 1, iy = ny - 2).
    """
    dx = grid.dx
    dy = grid.dy
    eps_map = grid.permittivity_map
    lz = grid.params.blade_length_m

    # Left wall (inner surface at ix = 1, normal into domain = +x)
    eps_l = 0.5 * (eps_map[1:-2, 1] + eps_map[2:-1, 1])
    ex_l = 0.5 * (ex[1:-2, 1] + ex[2:-1, 1])
    ey_l = 0.5 * (ey[1:-2, 1] + ey[2:-1, 1])
    f_left_x = float(np.sum(0.5 * EPSILON_0 * eps_l * (ex_l ** 2 - ey_l ** 2)) * dy)

    # Right wall (inner surface at ix = nx - 2, normal into domain = -x)
    ir = grid.nx - 2
    eps_r = 0.5 * (eps_map[1:-2, ir] + eps_map[2:-1, ir])
    ex_r = 0.5 * (ex[1:-2, ir] + ex[2:-1, ir])
    ey_r = 0.5 * (ey[1:-2, ir] + ey[2:-1, ir])
    f_right_x = -float(np.sum(0.5 * EPSILON_0 * eps_r * (ex_r ** 2 - ey_r ** 2)) * dy)

    # Top wall (inner surface at iy = ny - 2, normal into domain = -y)
    jt = grid.ny - 2
    eps_t = 0.5 * (eps_map[jt, 1:-2] + eps_map[jt, 2:-1])
    ex_t = 0.5 * (ex[jt, 1:-2] + ex[jt, 2:-1])
    ey_t = 0.5 * (ey[jt, 1:-2] + ey[jt, 2:-1])
    f_top_x = -float(np.sum(EPSILON_0 * eps_t * ex_t * ey_t) * dx)

    # Bottom wall (inner surface at iy = 1, normal into domain = +y)
    eps_b = 0.5 * (eps_map[1, 1:-2] + eps_map[1, 2:-1])
    ex_b = 0.5 * (ex[1, 1:-2] + ex[1, 2:-1])
    ey_b = 0.5 * (ey[1, 1:-2] + ey[1, 2:-1])
    f_bottom_x = float(np.sum(EPSILON_0 * eps_b * ex_b * ey_b) * dx)

    total_wall_x = f_left_x + f_right_x + f_top_x + f_bottom_x

    return DirectWallTractionForces(
        left_wall_force_x_n_per_m=float(f_left_x),
        right_wall_force_x_n_per_m=float(f_right_x),
        top_wall_force_x_n_per_m=float(f_top_x),
        bottom_wall_force_x_n_per_m=float(f_bottom_x),
        total_enclosure_force_x_n_per_m=float(total_wall_x),
        total_enclosure_force_3d_extruded_n=float(total_wall_x * lz),
    )


def compute_h0_whole_apparatus_ledger(
    grid: ExodusGrid2D, ex: np.ndarray, ey: np.ndarray, contour_offset: int = 2
) -> WholeApparatusForceLedgerH0:
    """Compute Maxwell-stress closed-contour forces for blade, ground, dielectric, and enclosure.

    Crucially:
        1. Guarantees blade and ground contours are strictly disjoint across the inter-electrode gap.
        2. Explicitly computes the dielectric boundary/material reaction force when epsilon_r != 1.0.
        3. Computes net_system_force_x using the independently evaluated direct enclosure wall
           tractions (NOT by tautologically setting f_box = -f_enclosure_inner).
    """
    lz = grid.params.blade_length_m

    blade_indices_y, blade_indices_x = np.where(grid.mask_blade_101)
    ground_indices_y, ground_indices_x = np.where(grid.mask_ground_102)

    b_xmin, b_xmax = int(np.min(blade_indices_x)), int(np.max(blade_indices_x))
    b_ymin, b_ymax = int(np.min(blade_indices_y)), int(np.max(blade_indices_y))

    g_xmin, g_xmax = int(np.min(ground_indices_x)), int(np.max(ground_indices_x))
    g_ymin, g_ymax = int(np.min(ground_indices_y)), int(np.max(ground_indices_y))

    # Determine safe gap offset so blade and ground contours never overlap
    if g_xmax < b_xmin:
        gap_cells = b_xmin - g_xmax
        gap_offset = min(contour_offset, max(1, (gap_cells - 1) // 2))
        bx_min = b_xmin - gap_offset
        bx_max = min(grid.nx - 2, b_xmax + contour_offset)
        gx_min = max(1, g_xmin - contour_offset)
        gx_max = g_xmax + gap_offset
    else:
        # Inverted orientation (blade on left, ground on right)
        gap_cells = g_xmin - b_xmax
        gap_offset = min(contour_offset, max(1, (gap_cells - 1) // 2))
        bx_min = max(1, b_xmin - contour_offset)
        bx_max = b_xmax + gap_offset
        gx_min = g_xmin - gap_offset
        gx_max = min(grid.nx - 2, g_xmax + contour_offset)

    by_min = max(1, b_ymin - contour_offset)
    by_max = min(grid.ny - 2, b_ymax + contour_offset)
    gy_min = max(1, g_ymin - contour_offset)
    gy_max = min(grid.ny - 2, g_ymax + contour_offset)

    # 1. Closed contour around blade electrode 101
    f_blade_per_m = integrate_maxwell_stress_x(grid, ex, ey, bx_min, bx_max, by_min, by_max)
    blade_force = MaxwellStressContourForces(
        force_per_length_n_per_m=float(f_blade_per_m),
        force_3d_extruded_n=float(f_blade_per_m * lz),
        ix_min=int(bx_min),
        ix_max=int(bx_max),
        iy_min=int(by_min),
        iy_max=int(by_max),
    )

    # 2. Closed contour around ground electrode 102
    f_ground_per_m = integrate_maxwell_stress_x(grid, ex, ey, gx_min, gx_max, gy_min, gy_max)
    ground_force = MaxwellStressContourForces(
        force_per_length_n_per_m=float(f_ground_per_m),
        force_3d_extruded_n=float(f_ground_per_m * lz),
        ix_min=int(gx_min),
        ix_max=int(gx_max),
        iy_min=int(gy_min),
        iy_max=int(gy_max),
    )

    # 3. Potted article outer contour (enclosing blade, ground, and dielectric potting block)
    ax_min = max(1, min(b_xmin, g_xmin) - max(1, contour_offset))
    ax_max = min(grid.nx - 2, max(b_xmax, g_xmax) + max(1, contour_offset))
    ay_min = max(1, min(b_ymin, g_ymin) - max(1, contour_offset))
    ay_max = min(grid.ny - 2, max(b_ymax, g_ymax) + max(1, contour_offset))

    f_article_per_m = integrate_maxwell_stress_x(grid, ex, ey, ax_min, ax_max, ay_min, ay_max)
    article_force = MaxwellStressContourForces(
        force_per_length_n_per_m=float(f_article_per_m),
        force_3d_extruded_n=float(f_article_per_m * lz),
    )

    # Korteweg-Helmholtz dielectric boundary/material reaction force:
    # In homogeneous medium (eps_r == 1.0), f_dielectric is strictly zero (apart from tiny stencil truncation).
    # In inhomogeneous dielectric (eps_r != 1.0), the jump across the dielectric interface carries
    # the ponderomotive force on the dielectric block: F_diel = F_article - (F_blade + F_ground).
    if np.any(grid.mask_dielectric_region):
        f_dielectric_per_m = f_article_per_m - (f_blade_per_m + f_ground_per_m)
    else:
        f_dielectric_per_m = 0.0

    dielectric_force = MaxwellStressContourForces(
        force_per_length_n_per_m=float(f_dielectric_per_m),
        force_3d_extruded_n=float(f_dielectric_per_m * lz),
    )

    # 4. Inner enclosure diagnostic contour (at index 2 .. nx-3, 2 .. ny-3)
    sx_min = 2
    sx_max = grid.nx - 3
    sy_min = 2
    sy_max = grid.ny - 3
    f_enclosure_inner_per_m = integrate_maxwell_stress_x(grid, ex, ey, sx_min, sx_max, sy_min, sy_max)
    enclosure_inner_force = MaxwellStressContourForces(
        force_per_length_n_per_m=float(f_enclosure_inner_per_m),
        force_3d_extruded_n=float(f_enclosure_inner_per_m * lz),
    )

    # 5. Independently evaluated direct wall surface traction on the 4 enclosure walls
    wall_tractions = compute_direct_enclosure_wall_tractions(grid, ex, ey)

    # 6. Non-tautological whole-system force sum using direct wall tractions
    f_net_per_m = (
        f_blade_per_m
        + f_ground_per_m
        + f_dielectric_per_m
        + wall_tractions.total_enclosure_force_x_n_per_m
    )

    system_force = MaxwellStressContourForces(
        force_per_length_n_per_m=float(f_net_per_m),
        force_3d_extruded_n=float(f_net_per_m * lz),
    )

    residual_per_m = float(abs(f_net_per_m))
    residual_3d = float(abs(f_net_per_m * lz))
    char_force = max(abs(f_blade_per_m), abs(f_ground_per_m), 1e-12)
    rel_residual = float(residual_per_m / char_force)
    is_conserved = bool(residual_3d < 5e-4 and rel_residual < 0.01)

    return WholeApparatusForceLedgerH0(
        blade_force_x=blade_force,
        ground_force_x=ground_force,
        dielectric_force_x=dielectric_force,
        potted_article_total_force_x=article_force,
        enclosure_inner_contour_force_x=enclosure_inner_force,
        enclosure_direct_wall_force_x=wall_tractions,
        net_system_force_x=system_force,
        is_momentum_conserved=is_conserved,
        residual_n_per_m=residual_per_m,
        residual_3d_extruded_n=residual_3d,
        relative_residual_to_blade_force=rel_residual,
    )


def benchmark_analytic_parallel_plate_maxwell_stress(
    voltage_v: float = 10000.0,
    gap_d_m: float = 0.008,
    plate_width_m: float = 0.060,
    dx_m: float = 0.0005,
) -> Dict[str, float]:
    """Benchmark 2D Laplace + Maxwell stress integration against exact parallel-plate theory.

    Validates:
        1. Central inter-electrode field E_num vs exact V / d.
        2. Central Maxwell stress traction T_xx vs exact 0.5 * eps0 * (V / d)^2.
        3. Equal-and-opposite closed-contour forces on symmetric plates and zero net system force.
    """
    params = ExodusPatentParameters(
        applied_voltage_v=voltage_v,
        gap_spacing_m=gap_d_m,
        ground_plane_width_m=plate_width_m,
        base_plate_width_m=plate_width_m,
        base_plate_thickness_m=0.002,
        enclosure_margin_x_m=0.020,
        enclosure_margin_y_m=0.020,
        dx_m=dx_m,
        dy_m=dx_m,
    )
    grid = build_symmetric_control_grid(params)
    pot, _, _ = solve_exodus_electrostatics(grid)
    ex, ey, _ = compute_electric_fields(grid, pot)
    ledger = compute_h0_whole_apparatus_ledger(grid, ex, ey)

    # Exact central electric field between plates (discrete gap distance between plate inner faces)
    g_ix = int(np.max(np.where(grid.mask_ground_102)[1]))
    b_ix = int(np.min(np.where(grid.mask_blade_101)[1]))
    actual_gap_m = (b_ix - g_ix) * grid.dx
    mid_ix = (g_ix + b_ix) // 2
    mid_iy = grid.ny // 2

    e_exact = voltage_v / actual_gap_m
    e_center_num = abs(float(ex[mid_iy, mid_ix]))
    pressure_exact = 0.5 * EPSILON_0 * (e_exact ** 2)
    pressure_center_num = 0.5 * EPSILON_0 * (e_center_num ** 2)

    return {
        "actual_gap_m": float(actual_gap_m),
        "e_exact_v_per_m": float(e_exact),
        "e_center_num_v_per_m": float(e_center_num),
        "field_relative_error": float(abs(e_center_num - e_exact) / e_exact),
        "pressure_exact_pa": float(pressure_exact),
        "pressure_center_num_pa": float(pressure_center_num),
        "pressure_relative_error": float(abs(pressure_center_num - pressure_exact) / pressure_exact),
        "blade_force_n_per_m": float(ledger.blade_force_x.force_per_length_n_per_m),
        "ground_force_n_per_m": float(ledger.ground_force_x.force_per_length_n_per_m),
        "net_system_force_n_per_m": float(ledger.net_system_force_x.force_per_length_n_per_m),
    }


def run_contour_offset_sweep(
    grid: ExodusGrid2D,
    ex: np.ndarray,
    ey: np.ndarray,
    offsets: Tuple[int, ...] = (1, 2, 3, 4),
) -> List[Dict[str, float]]:
    """Evaluate closed-contour forces across multiple contour offsets to verify path independence."""
    rows: List[Dict[str, float]] = []
    for c in offsets:
        ledger = compute_h0_whole_apparatus_ledger(grid, ex, ey, contour_offset=c)
        rows.append({
            "contour_offset_cells": float(c),
            "blade_force_x_n_per_m": float(ledger.blade_force_x.force_per_length_n_per_m),
            "ground_force_x_n_per_m": float(ledger.ground_force_x.force_per_length_n_per_m),
            "net_system_force_x_n_per_m": float(ledger.net_system_force_x.force_per_length_n_per_m),
        })
    return rows


def run_enclosure_clearance_sweep(
    base_params: Optional[ExodusPatentParameters] = None,
    clearances_m: Tuple[float, ...] = (0.015, 0.025, 0.040),
) -> List[Dict[str, float]]:
    """Sweep outer grounded enclosure standoff margin U to quantify wall coupling sensitivity."""
    if base_params is None:
        base_params = ExodusPatentParameters(dx_m=0.001, dy_m=0.001)
    rows: List[Dict[str, float]] = []
    for u_m in clearances_m:
        p = replace(base_params, enclosure_margin_x_m=u_m, enclosure_margin_y_m=u_m)
        g = build_exodus_2d_grid(p)
        pot, _, _ = solve_exodus_electrostatics(g)
        ex, ey, _ = compute_electric_fields(g, pot)
        ledger = compute_h0_whole_apparatus_ledger(g, ex, ey)
        rows.append({
            "enclosure_margin_m": float(u_m),
            "blade_force_x_n_per_m": float(ledger.blade_force_x.force_per_length_n_per_m),
            "ground_force_x_n_per_m": float(ledger.ground_force_x.force_per_length_n_per_m),
            "enclosure_wall_force_x_n_per_m": float(
                ledger.enclosure_direct_wall_force_x.total_enclosure_force_x_n_per_m
            ),
            "net_system_force_x_n_per_m": float(ledger.net_system_force_x.force_per_length_n_per_m),
        })
    return rows


def run_mesh_convergence_study(
    dx_values: Tuple[float, ...] = (0.00127, 0.000635, 0.00127 / 3.0),
    base_params: Optional[ExodusPatentParameters] = None,
) -> List[Dict[str, float]]:
    """Run a 2D mesh refinement convergence study across patent-unit-commensurate grid spacings."""
    if base_params is None:
        base_params = ExodusPatentParameters.figs_4_to_8_schematic()
    rows: List[Dict[str, float]] = []
    for dxi in dx_values:
        p = replace(base_params, dx_m=dxi, dy_m=dxi)
        g = build_exodus_2d_grid(p)
        pot, _, _ = solve_exodus_electrostatics(g)
        ex, ey, _ = compute_electric_fields(g, pot)
        ledger = compute_h0_whole_apparatus_ledger(g, ex, ey)
        rows.append({
            "dx_m": float(dxi),
            "blade_force_x_n_per_m": float(ledger.blade_force_x.force_per_length_n_per_m),
            "blade_force_3d_extruded_n": float(ledger.blade_force_x.force_3d_extruded_n),
            "ground_force_x_n_per_m": float(ledger.ground_force_x.force_per_length_n_per_m),
            "enclosure_wall_force_x_n_per_m": float(
                ledger.enclosure_direct_wall_force_x.total_enclosure_force_x_n_per_m
            ),
            "net_system_force_x_n_per_m": float(ledger.net_system_force_x.force_per_length_n_per_m),
            "residual_3d_extruded_n": float(ledger.residual_3d_extruded_n),
            "relative_residual": float(ledger.relative_residual_to_blade_force),
        })
    return rows



# ==============================================================================
# H1: Patent Eq. (11) Formulation via Material-Side Face Quadrature
# ==============================================================================

def compute_h1_patent_prediction(
    grid: ExodusGrid2D, ex: np.ndarray, ey: np.ndarray, e_mag: np.ndarray
) -> PatentHypothesisResultH1:
    """Evaluate US11511891B2 Eq. (11) using material-side boundary face quadrature.

    Patent Eq. (11):
        F = epsilon_0 * [E2^2 * A2 - E1^2 * A1]

    Reports both:
        1. Consistent face quadrature: eps0 * (integral_{100a} |E|^2 dl - integral_{101a} |E|^2 dl)
        2. Spatial-mean plug-in formula: eps0 * (<|E|>_{100a}^2 * w2 - <|E|>_{101a}^2 * w1)
    Evaluated strictly in the dielectric/vacuum layer immediately outside each conductor face.
    """
    lz = grid.params.blade_length_m

    face_100a = next(f for f in grid.boundary_faces if f.face_name == "proximal_tip_100a")
    face_101a = next(f for f in grid.boundary_faces if f.face_name == "distal_rear_101a")

    # Sample strictly on material side outside conductors
    e_prox_samples = e_mag[face_100a.sample_iy_ext, face_100a.sample_ix_ext]
    e_dist_samples = e_mag[face_101a.sample_iy_ext, face_101a.sample_ix_ext]

    # Face quadratures of |E|^2
    int_e2_prox = float(np.sum(e_prox_samples * e_prox_samples) * grid.dy)
    int_e2_dist = float(np.sum(e_dist_samples * e_dist_samples) * grid.dy)

    w2 = float(face_100a.length_m)
    w1 = float(face_101a.length_m)

    eff_e2 = math.sqrt(int_e2_prox / w2) if w2 > 0 else 0.0
    eff_e1 = math.sqrt(int_e2_dist / w1) if w1 > 0 else 0.0

    mean_e2 = float(np.mean(e_prox_samples)) if len(e_prox_samples) > 0 else 0.0
    mean_e1 = float(np.mean(e_dist_samples)) if len(e_dist_samples) > 0 else 0.0

    # Sign orientation: normal on 100a is (-1, 0) (or (+1, 0) if 180-deg inverted)
    # Outward traction on 100a pulls along face_100a.outward_normal[0]
    dir_sign = -1.0 if face_100a.outward_normal[0] < 0 else 1.0

    # Patent Eq. (11) magnitude difference oriented along apparatus axis
    f_h1_per_m = dir_sign * EPSILON_0 * (int_e2_prox - int_e2_dist)
    f_h1_mean_plugin_per_m = dir_sign * EPSILON_0 * ((mean_e2 ** 2) * w2 - (mean_e1 ** 2) * w1)
    f_h1_3d_extruded = f_h1_per_m * lz
    f_h1_half_factor = 0.5 * f_h1_3d_extruded

    proof_obligations = [
        "Eq. (4) assertion d(Ut) = 0 by analogy with stationary action delta S = 0 is mathematically invalid.",
        "Eq. (11) omits the fundamental 1/2 factor in electrostatic surface traction (1/2 * eps0 * E^2).",
        "Eq. (11) evaluates only two face pressures while omitting lateral flanks (100b), base front shoulder, ground counter-force, and enclosure wall reactions.",
        "Cauchy-Schwarz inequality: integral(E^2 dA) >= (<E>)^2 A; plug-in of mean or peak field into E^2*A is invalid for nonuniform fields.",
        "Whole-system closed-surface Maxwell stress integration (Model H0) proves net system force is zero.",
    ]

    return PatentHypothesisResultH1(
        proximal_face_integral_e2_dl=int_e2_prox,
        distal_face_integral_e2_dl=int_e2_dist,
        proximal_width_m=w2,
        distal_width_m=w1,
        effective_proximal_field_v_per_m=eff_e2,
        effective_distal_field_v_per_m=eff_e1,
        mean_proximal_field_v_per_m=mean_e2,
        mean_distal_field_v_per_m=mean_e1,
        predicted_force_per_length_n_per_m=float(f_h1_per_m),
        mean_field_plugin_force_per_length_n_per_m=float(f_h1_mean_plugin_per_m),
        predicted_force_3d_extruded_n=float(f_h1_3d_extruded),
        missing_half_factor_force_3d_extruded_n=float(f_h1_half_factor),
        proof_obligation_notes=proof_obligations,
    )


# ==============================================================================
# Constrained Finite 3D Boundary-Value Model (Full 6-Face 3D Stress Integration)
# ==============================================================================

def integrate_3d_maxwell_stress_box_x(
    ex: np.ndarray,
    ey: np.ndarray,
    ez: np.ndarray,
    eps_3d: np.ndarray,
    dx: float,
    dy: float,
    dz: float,
    ix_min: int,
    ix_max: int,
    iy_min: int,
    iy_max: int,
    iz_min: int,
    iz_max: int,
) -> float:
    """Integrate full 3D Maxwell stress tensor T_xj n_j over all 6 faces of a closed 3D box.

    Includes:
        - Normal stress T_xx = 0.5 * eps * (Ex^2 - Ey^2 - Ez^2) on +/-x faces (area dy * dz)
        - Shear stress  T_xy = eps * Ex * Ey                    on +/-y faces (area dx * dz)
        - Shear stress  T_xz = eps * Ex * Ez                    on +/-z faces (area dx * dy)
    Uses cell-centered trapezoidal averaging over each rectangular surface face.
    """
    # Helper to average a 3D array over 2 tangential index slices at a fixed normal index
    def _face_avg_x(arr: np.ndarray, ix: int) -> np.ndarray:
        return 0.25 * (
            arr[iz_min:iz_max, iy_min:iy_max, ix]
            + arr[iz_min + 1:iz_max + 1, iy_min:iy_max, ix]
            + arr[iz_min:iz_max, iy_min + 1:iy_max + 1, ix]
            + arr[iz_min + 1:iz_max + 1, iy_min + 1:iy_max + 1, ix]
        )

    def _face_avg_y(arr: np.ndarray, iy: int) -> np.ndarray:
        return 0.25 * (
            arr[iz_min:iz_max, iy, ix_min:ix_max]
            + arr[iz_min + 1:iz_max + 1, iy, ix_min:ix_max]
            + arr[iz_min:iz_max, iy, ix_min + 1:ix_max + 1]
            + arr[iz_min + 1:iz_max + 1, iy, ix_min + 1:ix_max + 1]
        )

    def _face_avg_z(arr: np.ndarray, iz: int) -> np.ndarray:
        return 0.25 * (
            arr[iz, iy_min:iy_max, ix_min:ix_max]
            + arr[iz, iy_min + 1:iy_max + 1, ix_min:ix_max]
            + arr[iz, iy_min:iy_max, ix_min + 1:ix_max + 1]
            + arr[iz, iy_min + 1:iy_max + 1, ix_min + 1:ix_max + 1]
        )

    # +x face (outward normal = +x)
    eps_xp = _face_avg_x(eps_3d, ix_max)
    ex_xp = _face_avg_x(ex, ix_max)
    ey_xp = _face_avg_x(ey, ix_max)
    ez_xp = _face_avg_x(ez, ix_max)
    f_xp = float(np.sum(0.5 * EPSILON_0 * eps_xp * (ex_xp ** 2 - ey_xp ** 2 - ez_xp ** 2)) * dy * dz)

    # -x face (outward normal = -x)
    eps_xm = _face_avg_x(eps_3d, ix_min)
    ex_xm = _face_avg_x(ex, ix_min)
    ey_xm = _face_avg_x(ey, ix_min)
    ez_xm = _face_avg_x(ez, ix_min)
    f_xm = -float(np.sum(0.5 * EPSILON_0 * eps_xm * (ex_xm ** 2 - ey_xm ** 2 - ez_xm ** 2)) * dy * dz)

    # +y face (outward normal = +y)
    eps_yp = _face_avg_y(eps_3d, iy_max)
    ex_yp = _face_avg_y(ex, iy_max)
    ey_yp = _face_avg_y(ey, iy_max)
    f_yp = float(np.sum(EPSILON_0 * eps_yp * ex_yp * ey_yp) * dx * dz)

    # -y face (outward normal = -y)
    eps_ym = _face_avg_y(eps_3d, iy_min)
    ex_ym = _face_avg_y(ex, iy_min)
    ey_ym = _face_avg_y(ey, iy_min)
    f_ym = -float(np.sum(EPSILON_0 * eps_ym * ex_ym * ey_ym) * dx * dz)

    # +z face (outward normal = +z)
    eps_zp = _face_avg_z(eps_3d, iz_max)
    ex_zp = _face_avg_z(ex, iz_max)
    ez_zp = _face_avg_z(ez, iz_max)
    f_zp = float(np.sum(EPSILON_0 * eps_zp * ex_zp * ez_zp) * dx * dy)

    # -z face (outward normal = -z)
    eps_zm = _face_avg_z(eps_3d, iz_min)
    ex_zm = _face_avg_z(ex, iz_min)
    ez_zm = _face_avg_z(ez, iz_min)
    f_zm = -float(np.sum(EPSILON_0 * eps_zm * ex_zm * ez_zm) * dx * dy)

    return f_xp + f_xm + f_yp + f_ym + f_zp + f_zm


def solve_exodus_electrostatics_3d(
    params: Optional[ExodusPatentParameters] = None,
    dx_3d_m: float = 0.002,
    dy_3d_m: float = 0.002,
    dz_3d_m: float = 0.004,
) -> Finite3DModelResult:
    """Solve 3D finite-difference electrostatics with finite blade length Lz and 6-face stress integration.

    Models finite 3D apparatus including 3D end fringing and finite enclosure walls.
    Crucially:
        1. Integrates all 6 faces of the 3D Maxwell stress box around blade and ground (strictly disjoint).
        2. Evaluates the 3D enclosure wall reaction independently at the outer enclosure boundary
           (NOT tautologically assigned as -(F_blade + F_ground)).
        3. Computes end_fringing_ratio_3d_to_extruded_2d directly from the ratio of the 3D blade
           force to the 2D extruded force at matched cross-sectional grid spacing.
    """
    if params is None:
        params = ExodusPatentParameters()

    dx = dx_3d_m
    dy = dy_3d_m
    dz = dz_3d_m

    margin_x = params.enclosure_margin_x_m
    margin_y = params.enclosure_margin_y_m
    margin_z = 0.020  # 20 mm end clearance along z

    lz = params.blade_length_m  # 101.6 mm

    n_margin_x = max(3, int(round(margin_x / dx)))
    n_ground_th = max(1, int(round(params.ground_plane_thickness_m / dx)))
    n_gap = max(2, int(round(params.gap_spacing_m / dx)))
    n_blade_p = max(2, int(round(params.blade_height_m / dx)))
    n_base_th = max(1, int(round(params.base_plate_thickness_m / dx)))

    n_margin_y = max(3, int(round(margin_y / dy)))
    n_ground_y = max(2, int(round(params.ground_plane_width_m / dy)))
    n_base_y = max(2, int(round(params.base_plate_width_m / dy)))

    n_margin_z = max(3, int(round(margin_z / dz)))
    n_lz = max(4, int(round(lz / dz)))

    nx = 2 * n_margin_x + n_ground_th + n_gap + n_blade_p + n_base_th + 2
    ny = 2 * n_margin_y + max(n_ground_y, n_base_y) + 2
    nz = 2 * n_margin_z + n_lz + 2

    # Initialize 3D masks
    mask_blade = np.zeros((nz, ny, nx), dtype=bool)
    mask_ground = np.zeros((nz, ny, nx), dtype=bool)
    mask_enclosure = np.zeros((nz, ny, nx), dtype=bool)

    # Enclosure boundary (6 outer walls)
    mask_enclosure[0, :, :] = True
    mask_enclosure[-1, :, :] = True
    mask_enclosure[:, 0, :] = True
    mask_enclosure[:, -1, :] = True
    mask_enclosure[:, :, 0] = True
    mask_enclosure[:, :, -1] = True

    # Feature coordinates along X
    x_ground_l = n_margin_x
    x_ground_r = x_ground_l + n_ground_th - 1

    x_blade_tip = x_ground_r + n_gap + 1
    x_blade_base = x_blade_tip + n_blade_p
    x_blade_back = x_blade_base + n_base_th - 1

    y_mid = ny // 2
    z_mid = nz // 2

    iz_min = max(2, z_mid - (n_lz // 2))
    iz_max = min(nz - 3, iz_min + n_lz - 1)

    iy_ground_min = max(2, y_mid - (n_ground_y // 2))
    iy_ground_max = min(ny - 3, iy_ground_min + n_ground_y - 1)

    iy_base_min = max(2, y_mid - (n_base_y // 2))
    iy_base_max = min(ny - 3, iy_base_min + n_base_y - 1)

    # Ground plate
    mask_ground[iz_min:iz_max + 1, iy_ground_min:iy_ground_max + 1, x_ground_l:x_ground_r + 1] = True

    # Base plate
    mask_blade[iz_min:iz_max + 1, iy_base_min:iy_base_max + 1, x_blade_base:x_blade_back + 1] = True

    # Blade(s)
    n_tip_y = max(1, int(round(params.blade_thickness_m / dy)))
    if params.num_blades <= 1:
        b_min = max(iy_base_min, y_mid - (n_tip_y // 2))
        b_max = min(iy_base_max, b_min + n_tip_y - 1)
        mask_blade[iz_min:iz_max + 1, b_min:b_max + 1, x_blade_tip:x_blade_base + 1] = True
    else:
        y_center_m = y_mid * dy
        y_start_m = y_center_m - ((params.num_blades - 1) * params.blade_pitch_m / 2.0)
        for b in range(params.num_blades):
            by_m = y_start_m + b * params.blade_pitch_m
            iy_b = int(round(by_m / dy))
            b_min = max(iy_base_min, iy_b - (n_tip_y // 2))
            b_max = min(iy_base_max, b_min + n_tip_y - 1)
            mask_blade[iz_min:iz_max + 1, b_min:b_max + 1, x_blade_tip:x_blade_base + 1] = True

    mask_blade = mask_blade & (~mask_ground) & (~mask_enclosure)
    mask_ground = mask_ground & (~mask_enclosure)

    # 3D Permittivity map
    eps_3d = np.ones((nz, ny, nx), dtype=float)
    has_diel = abs(params.dielectric_relative_permittivity - 1.0) > 1e-12
    if has_diel:
        iy_d_min = min(iy_base_min, iy_ground_min)
        iy_d_max = max(iy_base_max, iy_ground_max)
        eps_3d[iz_min:iz_max + 1, iy_d_min:iy_d_max + 1, x_ground_l:x_blade_back + 1] = (
            params.dielectric_relative_permittivity
        )

    fixed = mask_blade | mask_ground | mask_enclosure
    bc = np.zeros((nz, ny, nx), dtype=float)
    bc[mask_blade] = params.applied_voltage_v

    # Vectorized 7-point variable-permittivity 3D matrix assembly
    n_pts = nx * ny * nz
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    inv_dz2 = 1.0 / (dz * dz)

    eps_xp = np.zeros_like(eps_3d)
    eps_xp[:, :, :-1] = 2.0 * eps_3d[:, :, :-1] * eps_3d[:, :, 1:] / (eps_3d[:, :, :-1] + eps_3d[:, :, 1:])
    eps_xm = np.zeros_like(eps_3d)
    eps_xm[:, :, 1:] = 2.0 * eps_3d[:, :, 1:] * eps_3d[:, :, :-1] / (eps_3d[:, :, 1:] + eps_3d[:, :, :-1])

    eps_yp = np.zeros_like(eps_3d)
    eps_yp[:, :-1, :] = 2.0 * eps_3d[:, :-1, :] * eps_3d[:, 1:, :] / (eps_3d[:, :-1, :] + eps_3d[:, 1:, :])
    eps_ym = np.zeros_like(eps_3d)
    eps_ym[:, 1:, :] = 2.0 * eps_3d[:, 1:, :] * eps_3d[:, :-1, :] / (eps_3d[:, 1:, :] + eps_3d[:, :-1, :])

    eps_zp = np.zeros_like(eps_3d)
    eps_zp[:-1, :, :] = 2.0 * eps_3d[:-1, :, :] * eps_3d[1:, :, :] / (eps_3d[:-1, :, :] + eps_3d[1:, :, :])
    eps_zm = np.zeros_like(eps_3d)
    eps_zm[1:, :, :] = 2.0 * eps_3d[1:, :, :] * eps_3d[:-1, :, :] / (eps_3d[1:, :, :] + eps_3d[:-1, :, :])

    fixed_flat = fixed.ravel()
    free_mask = ~fixed_flat

    fk, fj, fi = np.where(~fixed)
    f_idx = fk * (ny * nx) + fj * nx + fi

    c_xp = eps_xp[fk, fj, fi] * inv_dx2
    c_xm = eps_xm[fk, fj, fi] * inv_dx2
    c_yp = eps_yp[fk, fj, fi] * inv_dy2
    c_ym = eps_ym[fk, fj, fi] * inv_dy2
    c_zp = eps_zp[fk, fj, fi] * inv_dz2
    c_zm = eps_zm[fk, fj, fi] * inv_dz2
    c_center = c_xp + c_xm + c_yp + c_ym + c_zp + c_zm

    rows = np.concatenate([f_idx, f_idx, f_idx, f_idx, f_idx, f_idx, f_idx])
    cols = np.concatenate([
        f_idx,
        f_idx + 1,
        f_idx - 1,
        f_idx + nx,
        f_idx - nx,
        f_idx + ny * nx,
        f_idx - ny * nx,
    ])
    data = np.concatenate([
        c_center,
        -c_xp,
        -c_xm,
        -c_yp,
        -c_ym,
        -c_zp,
        -c_zm,
    ])

    a_full = sp.csr_matrix((data, (rows, cols)), shape=(n_pts, n_pts))
    a_ff = a_full[free_mask, :][:, free_mask]
    a_fc = a_full[free_mask, :][:, fixed_flat]
    rhs_f = -a_fc.dot(bc.ravel()[fixed_flat])

    rhs_norm = float(np.linalg.norm(rhs_f))
    if rhs_norm > 0.0:
        m_prec = sp.diags(1.0 / a_ff.diagonal())
        sol_f, _ = spla.cg(a_ff, rhs_f, rtol=1e-10, maxiter=800, M=m_prec)
        solver_res = float(np.linalg.norm(a_ff.dot(sol_f) - rhs_f) / rhs_norm)
    else:
        sol_f = np.zeros_like(rhs_f)
        solver_res = 0.0

    pot_flat = bc.ravel().copy()
    pot_flat[free_mask] = sol_f
    pot_3d = pot_flat.reshape((nz, ny, nx))

    # Compute 3D electric field components (Ex, Ey, Ez) = -grad(V)
    ex_3d = np.zeros_like(pot_3d)
    ey_3d = np.zeros_like(pot_3d)
    ez_3d = np.zeros_like(pot_3d)

    ex_3d[:, :, 1:-1] = -(pot_3d[:, :, 2:] - pot_3d[:, :, :-2]) / (2.0 * dx)
    ey_3d[:, 1:-1, :] = -(pot_3d[:, 2:, :] - pot_3d[:, :-2, :]) / (2.0 * dy)
    ez_3d[1:-1, :, :] = -(pot_3d[2:, :, :] - pot_3d[:-2, :, :]) / (2.0 * dz)

    # Disjoint 3D contour boxes around blade and ground
    b_k, b_j, b_i = np.where(mask_blade)
    g_k, g_j, g_i = np.where(mask_ground)

    b_imin, b_imax = int(np.min(b_i)), int(np.max(b_i))
    g_imin, g_imax = int(np.min(g_i)), int(np.max(g_i))
    gap_offset = max(1, (b_imin - g_imax) // 2)
    ext_offset = 2

    bx_l = b_imin - gap_offset
    bx_r = min(nx - 3, b_imax + ext_offset)
    by_l = max(2, int(np.min(b_j)) - ext_offset)
    by_r = min(ny - 3, int(np.max(b_j)) + ext_offset)
    bz_l = max(2, int(np.min(b_k)) - ext_offset)
    bz_r = min(nz - 3, int(np.max(b_k)) + ext_offset)

    gx_l = max(2, g_imin - ext_offset)
    gx_r = g_imax + gap_offset
    gy_l = max(2, int(np.min(g_j)) - ext_offset)
    gy_r = min(ny - 3, int(np.max(g_j)) + ext_offset)
    gz_l = max(2, int(np.min(g_k)) - ext_offset)
    gz_r = min(nz - 3, int(np.max(g_k)) + ext_offset)

    f_3d_blade_x = integrate_3d_maxwell_stress_box_x(
        ex_3d, ey_3d, ez_3d, eps_3d, dx, dy, dz, bx_l, bx_r, by_l, by_r, bz_l, bz_r
    )
    f_3d_ground_x = integrate_3d_maxwell_stress_box_x(
        ex_3d, ey_3d, ez_3d, eps_3d, dx, dy, dz, gx_l, gx_r, gy_l, gy_r, gz_l, gz_r
    )

    # Potted article 3D box (enclosing blade + ground + dielectric)
    ax_l = max(2, min(b_imin, g_imin) - ext_offset)
    ax_r = min(nx - 3, max(b_imax, g_imax) + ext_offset)
    ay_l = max(2, min(int(np.min(b_j)), int(np.min(g_j))) - ext_offset)
    ay_r = min(ny - 3, max(int(np.max(b_j)), int(np.max(g_j))) + ext_offset)
    az_l = max(2, min(int(np.min(b_k)), int(np.min(g_k))) - ext_offset)
    az_r = min(nz - 3, max(int(np.max(b_k)), int(np.max(g_k))) + ext_offset)

    f_3d_article_x = integrate_3d_maxwell_stress_box_x(
        ex_3d, ey_3d, ez_3d, eps_3d, dx, dy, dz, ax_l, ax_r, ay_l, ay_r, az_l, az_r
    )
    f_3d_dielectric_x = (f_3d_article_x - (f_3d_blade_x + f_3d_ground_x)) if has_diel else 0.0

    # Independently evaluated 3D outer enclosure reaction on the inner wall layer (2 .. n-3)
    f_3d_enclosure_outward_flux = integrate_3d_maxwell_stress_box_x(
        ex_3d, ey_3d, ez_3d, eps_3d, dx, dy, dz, 2, nx - 3, 2, ny - 3, 2, nz - 3
    )
    f_3d_enclosure_x = -f_3d_enclosure_outward_flux

    # Genuine non-tautological 3D whole-system net force sum
    f_3d_net = f_3d_blade_x + f_3d_ground_x + f_3d_dielectric_x + f_3d_enclosure_x
    char_3d_force = max(abs(f_3d_blade_x), abs(f_3d_ground_x), 1e-12)
    rel_3d_res = float(abs(f_3d_net) / char_3d_force)

    # Compare against 2D extruded force at matched cross-sectional grid spacing (dx, dy)
    params_2d_matched = replace(params, dx_m=dx, dy_m=dy)
    grid_2d_matched = build_exodus_2d_grid(params_2d_matched)
    pot_2d_m, _, _ = solve_exodus_electrostatics(grid_2d_matched)
    ex_2d_m, ey_2d_m, _ = compute_electric_fields(grid_2d_matched, pot_2d_m)
    ledger_2d_m = compute_h0_whole_apparatus_ledger(grid_2d_matched, ex_2d_m, ey_2d_m, contour_offset=ext_offset)
    f_2d_extruded_matched = ledger_2d_m.blade_force_x.force_3d_extruded_n

    end_fringing_ratio = float(
        f_3d_blade_x / f_2d_extruded_matched if abs(f_2d_extruded_matched) > 1e-15 else 1.0
    )

    return Finite3DModelResult(
        nx=nx,
        ny=ny,
        nz=nz,
        dx_m=dx,
        dy_m=dy,
        dz_m=dz,
        finite_blade_length_m=lz,
        solver_residual=solver_res,
        true_3d_blade_force_x_n=float(f_3d_blade_x),
        true_3d_ground_force_x_n=float(f_3d_ground_x),
        true_3d_dielectric_force_x_n=float(f_3d_dielectric_x),
        true_3d_enclosure_force_x_n=float(f_3d_enclosure_x),
        true_3d_net_system_force_x_n=float(f_3d_net),
        true_3d_relative_residual=rel_3d_res,
        true_3d_is_conserved=bool(abs(f_3d_net) < 1.5e-3 and rel_3d_res < 0.025),
        extruded_2d_blade_force_at_matched_dx_n=float(f_2d_extruded_matched),
        end_fringing_ratio_3d_to_extruded_2d=end_fringing_ratio,
    )


def run_3d_mesh_convergence_study(
    spacings: Tuple[Tuple[float, float], ...] = ((0.0020, 0.0040), (0.0015, 0.0030), (0.0012, 0.0025)),
    base_params: Optional[ExodusPatentParameters] = None,
) -> List[Finite3DModelResult]:
    """Run a 3D mesh refinement convergence study across multiple (dx=dy, dz) spacings."""
    if base_params is None:
        base_params = ExodusPatentParameters()
    return [
        solve_exodus_electrostatics_3d(base_params, dx_3d_m=dx, dy_3d_m=dx, dz_3d_m=dz)
        for dx, dz in spacings
    ]



# ==============================================================================
# Evaluated Controls & Literature Benchmark Audit
# ==============================================================================

def evaluate_experimental_controls(
    params: ExodusPatentParameters,
    base_ledger: WholeApparatusForceLedgerH0,
    base_e_mag: Optional[np.ndarray] = None,
) -> EvaluatedControlsResult:
    """Execute programmatic controls directly in the solver and audit literature benchmark."""
    if base_e_mag is None:
        g_base = build_exodus_2d_grid(params)
        p_base, _, _ = solve_exodus_electrostatics(g_base)
        _, _, base_e_mag = compute_electric_fields(g_base, p_base)

    # 1. Polarity reversal control: solve at -V
    params_neg = replace(params, applied_voltage_v=-params.applied_voltage_v)
    grid_neg = build_exodus_2d_grid(params_neg)
    pot_neg, _, _ = solve_exodus_electrostatics(grid_neg)
    ex_neg, ey_neg, emag_neg = compute_electric_fields(grid_neg, pot_neg)
    ledger_neg = compute_h0_whole_apparatus_ledger(grid_neg, ex_neg, ey_neg)

    max_emag = float(np.max(base_e_mag))
    diff_emag_rel = float(np.max(np.abs(base_e_mag - emag_neg)) / (max_emag if max_emag > 0 else 1.0))

    f_base = abs(base_ledger.blade_force_x.force_per_length_n_per_m)
    f_neg = abs(ledger_neg.blade_force_x.force_per_length_n_per_m)
    diff_f_rel = float(abs(f_base - f_neg) / (f_base if f_base > 0 else 1.0))

    # 2. Voltage-off control: solve at V = 0
    params_zero = replace(params, applied_voltage_v=0.0)
    grid_zero = build_exodus_2d_grid(params_zero)
    pot_zero, _, _ = solve_exodus_electrostatics(grid_zero)
    ex_zero, ey_zero, emag_zero = compute_electric_fields(grid_zero, pot_zero)
    ledger_zero = compute_h0_whole_apparatus_ledger(grid_zero, ex_zero, ey_zero)
    v0_max_e = float(np.max(emag_zero))
    v0_force = float(abs(ledger_zero.blade_force_x.force_per_length_n_per_m))

    # 3. Symmetric electrode control: solve on symmetric grid
    grid_sym = build_symmetric_control_grid(params)
    pot_sym, _, _ = solve_exodus_electrostatics(grid_sym)
    ex_sym, ey_sym, _ = compute_electric_fields(grid_sym, pot_sym)
    ledger_sym = compute_h0_whole_apparatus_ledger(grid_sym, ex_sym, ey_sym)
    sym_blade_f = float(ledger_sym.blade_force_x.force_per_length_n_per_m)
    sym_ground_f = float(ledger_sym.ground_force_x.force_per_length_n_per_m)
    sym_net_f_per_m = float(ledger_sym.net_system_force_x.force_per_length_n_per_m)
    sym_net_f_3d = float(ledger_sym.net_system_force_x.force_3d_extruded_n)

    # 4. 180-degree spatial inversion control: solve BVP on mirrored apparatus grid
    grid_inv = build_inverted_180_grid(params)
    pot_inv, _, _ = solve_exodus_electrostatics(grid_inv)
    ex_inv, ey_inv, _ = compute_electric_fields(grid_inv, pot_inv)
    ledger_inv = compute_h0_whole_apparatus_ledger(grid_inv, ex_inv, ey_inv)
    f_base_signed = float(base_ledger.blade_force_x.force_per_length_n_per_m)
    f_inv_signed = float(ledger_inv.blade_force_x.force_per_length_n_per_m)
    inv_rel_err = float(abs(f_base_signed + f_inv_signed) / (abs(f_base_signed) + 1e-15))
    inv_reversed = bool((f_base_signed * f_inv_signed < 0.0) and (inv_rel_err < 1e-6))

    # 5. Enclosure wall proximity sensitivity control (asymmetric standoff margin: right wall at 10 mm)
    params_asym_wall = replace(
        params,
        enclosure_margin_left_x_m=0.040,
        enclosure_margin_right_x_m=0.010,
    )
    grid_asym_w = build_exodus_2d_grid(params_asym_wall)
    pot_asym_w, _, _ = solve_exodus_electrostatics(grid_asym_w)
    ex_asym_w, ey_asym_w, _ = compute_electric_fields(grid_asym_w, pot_asym_w)
    ledger_asym_w = compute_h0_whole_apparatus_ledger(grid_asym_w, ex_asym_w, ey_asym_w)

    sym_pair_force = float(
        base_ledger.blade_force_x.force_per_length_n_per_m
        + base_ledger.ground_force_x.force_per_length_n_per_m
        + base_ledger.dielectric_force_x.force_per_length_n_per_m
    )
    asym_pair_force = float(
        ledger_asym_w.blade_force_x.force_per_length_n_per_m
        + ledger_asym_w.ground_force_x.force_per_length_n_per_m
        + ledger_asym_w.dielectric_force_x.force_per_length_n_per_m
    )
    asym_wall_reaction = float(
        ledger_asym_w.enclosure_direct_wall_force_x.total_enclosure_force_x_n_per_m
    )
    asym_net_res = float(ledger_asym_w.net_system_force_x.force_per_length_n_per_m)

    # 6. Structured Literature Benchmark Audit (Tajmar & Schreiber 2020 vs US11511891B2 FIGS. 21-22)
    lit_audit = LiteratureBenchmarkAudit(
        tajmar_schreiber_citation=(
            "Martin Tajmar & Thomas P. Schreiber, 'Put Strong Limits on All Proposed Theories so far "
            "Assessing Electrostatic Propulsion: Does a Charged High-Voltage Capacitor Produce Thrust?', "
            "Journal of Electrostatics, Vol. 107, 103477 (2020)."
        ),
        tajmar_schreiber_doi="10.1016/j.elstat.2020.103477",
        tajmar_schreiber_max_voltage_v=10000.0,
        tajmar_schreiber_mass_accuracy_mg=0.3,
        tajmar_schreiber_force_accuracy_n=float(0.3e-6 * 9.80665),  # ~2.942e-6 N (~2.94 uN)
        tajmar_schreiber_apparatus=(
            "Self-contained battery-powered high-voltage source and capacitors inside a double-walled "
            "Faraday cage on a precision balance (measuring apparent weight changes without external HV lead wires)."
        ),
        tajmar_schreiber_finding=(
            "No net force or apparent weight change detected within +/-0.3 mg (~+/-2.94 uN) accuracy "
            "across symmetric and asymmetric high-voltage capacitors up to 10 kV."
        ),
        patent_fig21_citation="US11511891B2 Columns 14-15, FIGS. 21-23",
        patent_fig21_test_voltage_v=25000.0,
        patent_fig21_max_supply_voltage_v=40000.0,
        patent_fig21_num_blades=9,
        patent_fig21_dielectric="Unspecified high-voltage potting epoxy",
        patent_fig21_environment=(
            "Nine-blade potted article suspended on a pendulum stand inside a plastic bag in ambient air, "
            "surrounded by a grounded ITO-coated PET box with an external HV supply wire fed through the back."
        ),
        patent_fig21_reported_force_n=2.37e-4,  # ~237 uN
        patent_fig21_uncertainty_status="PATENT_OMITTED_UNKNOWN",
        comparison_status="CONTEXTUAL_QUALITATIVE_ONLY_MISMATCHED_APPARATUS",
        candidate_confounders_not_established_causes=[
            "Atmospheric corona discharge / ionic wind inside the air-filled plastic bag and enclosure",
            "Electrostatic Coulomb attraction between energized electrodes/leads and the grounded ITO-coated box walls",
            "Mechanical stiffness, thermal expansion, and electrostatic forces on the external HV feedthrough wire",
            "Pendulum stand tilt, thermal convection currents, and dielectric charging/outgassing drift",
        ],
    )

    lit_summary = (
        "Tajmar & Schreiber (2020) tested symmetric and asymmetric high-voltage capacitors up to 10 kV "
        "inside a self-contained battery-powered Faraday cage on a precision balance with accuracy "
        "+/-0.3 mg equivalent weight (~+/-2.94 uN), observing a null result (no anomalous thrust). "
        "The Exodus patent's reported ~237 uN at +25 kV pertains to a different apparatus: a nine-blade "
        "epoxy-potted article on a pendulum stand in air inside a plastic bag with an external HV wire. "
        "Because geometry, voltage (10 kV vs 25 kV), mounting, and shielding differ, this cross-apparatus "
        "comparison is strictly contextual/qualitative rather than a direct ratio. Corona/ion wind, "
        "external wire forces, and wall Coulomb coupling represent candidate confounders that require "
        "controlled experimental discrimination rather than being asserted as established causes."
    )

    unperformed = [
        "Vacuum chamber pressure sweep (to empirically test for ion-wind / corona onset)",
        "Physical 180-degree balance/pendulum rotation in laboratory hardware",
        "On-board battery excitation vs external HV feedthrough wire tare calibration",
        "Thermal convection, outgassing, and dielectric relaxation drift tare",
    ]

    return EvaluatedControlsResult(
        polarity_reversal_evaluated=True,
        polarity_reversal_max_field_diff_relative=diff_emag_rel,
        polarity_reversal_blade_force_diff_relative=diff_f_rel,
        symmetric_control_evaluated=True,
        symmetric_blade_force_n_per_m=sym_blade_f,
        symmetric_ground_force_n_per_m=sym_ground_f,
        symmetric_control_net_force_n_per_m=sym_net_f_per_m,
        symmetric_control_net_force_3d_n=sym_net_f_3d,
        voltage_off_evaluated=True,
        voltage_off_max_field_v_per_m=v0_max_e,
        voltage_off_blade_force_n_per_m=v0_force,
        inversion_180_evaluated=True,
        inversion_180_base_blade_force_x_n_per_m=f_base_signed,
        inversion_180_inverted_blade_force_x_n_per_m=f_inv_signed,
        inversion_180_relative_reversal_error=inv_rel_err,
        inversion_180_vector_reversed=inv_reversed,
        wall_proximity_control_evaluated=True,
        wall_proximity_symmetric_pair_force_n_per_m=sym_pair_force,
        wall_proximity_asymmetric_pair_force_n_per_m=asym_pair_force,
        wall_proximity_asymmetric_wall_reaction_n_per_m=asym_wall_reaction,
        wall_proximity_asymmetric_net_residual_n_per_m=asym_net_res,
        physical_controls_status="NOT_EVALUATED_NUMERICAL_SIMULATION_ONLY",
        unperformed_physical_controls=unperformed,
        literature_audit=lit_audit,
        literature_benchmark_citation=lit_audit.tajmar_schreiber_citation,
        literature_benchmark_summary=lit_summary,
    )


def verify_control_assertions(controls: EvaluatedControlsResult, strict: bool = True) -> bool:
    """Programmatic gate validating control observables; fails closed on false positives."""
    checks = [
        controls.polarity_reversal_evaluated,
        controls.polarity_reversal_max_field_diff_relative < 1e-9,
        controls.polarity_reversal_blade_force_diff_relative < 1e-9,
        controls.symmetric_control_evaluated,
        controls.symmetric_blade_force_n_per_m < -1e-3,
        controls.symmetric_ground_force_n_per_m > 1e-3,
        abs(controls.symmetric_blade_force_n_per_m + controls.symmetric_ground_force_n_per_m) < 1e-7,
        abs(controls.symmetric_control_net_force_3d_n) < 1e-6,
        controls.voltage_off_evaluated,
        controls.voltage_off_max_field_v_per_m == 0.0,
        controls.voltage_off_blade_force_n_per_m == 0.0,
        controls.inversion_180_evaluated,
        controls.inversion_180_vector_reversed,
        (controls.inversion_180_base_blade_force_x_n_per_m * controls.inversion_180_inverted_blade_force_x_n_per_m) < 0.0,
        abs(controls.inversion_180_base_blade_force_x_n_per_m + controls.inversion_180_inverted_blade_force_x_n_per_m)
        / (abs(controls.inversion_180_base_blade_force_x_n_per_m) + 1e-15)
        < 1e-6,
        controls.inversion_180_relative_reversal_error < 1e-6,
    ]
    passed = all(checks)
    if strict and not passed:
        raise ValueError("Programmatic control validation gate failed on one or more control observables.")
    return passed


# ==============================================================================
# Complete P2 Evaluation Pipeline
# ==============================================================================

def evaluate_exodus_patent(params: Optional[ExodusPatentParameters] = None) -> ExodusEvaluationResult:
    """Execute complete end-to-end evaluation of Exodus patent US11511891B2."""
    if params is None:
        params = ExodusPatentParameters()

    grid = build_exodus_2d_grid(params)
    potential, iters, res = solve_exodus_electrostatics(grid)
    ex, ey, e_mag = compute_electric_fields(grid, potential)

    h0_ledger = compute_h0_whole_apparatus_ledger(grid, ex, ey)
    h1_result = compute_h1_patent_prediction(grid, ex, ey, e_mag)
    controls = evaluate_experimental_controls(params, h0_ledger, base_e_mag=e_mag)
    finite_3d = solve_exodus_electrostatics_3d(params)

    return ExodusEvaluationResult(
        params=params,
        grid=grid,
        potential_v=potential,
        e_field_x_v_per_m=ex,
        e_field_y_v_per_m=ey,
        e_field_magnitude_v_per_m=e_mag,
        h0_ledger=h0_ledger,
        h1_prediction=h1_result,
        controls=controls,
        finite_3d_model=finite_3d,
        solver_iterations=iters,
        solver_residual=res,
    )


def generate_exodus_patent_manifest(
    result: ExodusEvaluationResult,
    source_head_sha: str = "UNKNOWN",
    tested_checkout_sha: str = "UNKNOWN",
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate paired JSON evidence manifest with schema 1.2.0 provenance."""
    ledger = get_patent_parameter_ledger(result.params)

    # Also evaluate the 9-blade FIG. 21 embodiment summary so both embodiments are separated in manifest
    fig21_params = ExodusPatentParameters.fig_21_nine_blade_article(dx_m=0.001, dy_m=0.001)
    fig21_grid = build_exodus_2d_grid(fig21_params)
    fig21_pot, _, _ = solve_exodus_electrostatics(fig21_grid)
    fig21_ex, fig21_ey, fig21_emag = compute_electric_fields(fig21_grid, fig21_pot)
    fig21_h0 = compute_h0_whole_apparatus_ledger(fig21_grid, fig21_ex, fig21_ey)
    fig21_h1 = compute_h1_patent_prediction(fig21_grid, fig21_ex, fig21_ey, fig21_emag)

    manifest: Dict[str, Any] = {
        "manifest_schema_version": "1.2.0",
        "phase": "P2",
        "patent_identifier": "US11511891B2",
        "patent_title": "System and method for generating forces using asymmetrical electrostatic pressure",
        "inventors": ["Andrew Neil Aurigema", "Charles Raymond Buhler, IV"],
        "issue_date": "2022-11-29",
        "embodiment_evaluated": result.params.embodiment_id,
        "git_provenance": {
            "source_head_sha": source_head_sha,
            "tested_checkout_sha": tested_checkout_sha,
            "governing_review": "P2_R2_REMEDIATION",
        },
        "parameter_audit": [asdict(record) for record in ledger],
        "h0_conventional_maxwell_stress": {
            "model_type": "conservative_electrostatics_laplace_closed_contour_and_direct_wall_traction",
            "boundary_conditions": "Dirichlet conductors, outer grounded shielding box",
            "dimensional_note": (
                "2D forces are exact per-unit-depth line integrals (N/m); 3d_extruded_n values "
                "multiply 2D line integrals by Lz=101.6 mm as an extruded 2D approximation "
                "(not validated for physical 3D FIG. 21 article; see finite_3d_apparatus_model)."
            ),
            "blade_electrode_force_x_n_per_m": float(result.h0_ledger.blade_force_x.force_per_length_n_per_m),
            "blade_electrode_force_x_3d_extruded_n": float(result.h0_ledger.blade_force_x.force_3d_extruded_n),
            "ground_electrode_force_x_n_per_m": float(result.h0_ledger.ground_force_x.force_per_length_n_per_m),
            "ground_electrode_force_x_3d_extruded_n": float(result.h0_ledger.ground_force_x.force_3d_extruded_n),
            "dielectric_ponderomotive_force_x_n_per_m": float(
                result.h0_ledger.dielectric_force_x.force_per_length_n_per_m
            ),
            "potted_article_total_force_x_n_per_m": float(
                result.h0_ledger.potted_article_total_force_x.force_per_length_n_per_m
            ),
            "enclosure_inner_contour_flux_x_n_per_m": float(
                result.h0_ledger.enclosure_inner_contour_force_x.force_per_length_n_per_m
            ),
            "enclosure_direct_wall_traction_x_n_per_m": float(
                result.h0_ledger.enclosure_direct_wall_force_x.total_enclosure_force_x_n_per_m
            ),
            "enclosure_direct_wall_traction_x_3d_extruded_n": float(
                result.h0_ledger.enclosure_direct_wall_force_x.total_enclosure_force_3d_extruded_n
            ),
            "net_system_force_x_n_per_m": float(result.h0_ledger.net_system_force_x.force_per_length_n_per_m),
            "net_system_force_x_3d_extruded_n": float(result.h0_ledger.net_system_force_x.force_3d_extruded_n),
            "numerical_residual_n": float(result.h0_ledger.residual_3d_extruded_n),
            "relative_residual_to_blade_force": float(result.h0_ledger.relative_residual_to_blade_force),
            "is_momentum_conserved": bool(result.h0_ledger.is_momentum_conserved),
        },
        "finite_3d_apparatus_model": {
            "model_type": "constrained_3d_finite_difference_6_face_maxwell_stress",
            "finite_blade_length_m": float(result.finite_3d_model.finite_blade_length_m),
            "grid_dimensions": [
                result.finite_3d_model.nx,
                result.finite_3d_model.ny,
                result.finite_3d_model.nz,
            ],
            "grid_spacing_m": [
                float(result.finite_3d_model.dx_m),
                float(result.finite_3d_model.dy_m),
                float(result.finite_3d_model.dz_m),
            ],
            "solver_residual": float(result.finite_3d_model.solver_residual),
            "true_3d_blade_force_x_n": float(result.finite_3d_model.true_3d_blade_force_x_n),
            "true_3d_ground_force_x_n": float(result.finite_3d_model.true_3d_ground_force_x_n),
            "true_3d_dielectric_force_x_n": float(result.finite_3d_model.true_3d_dielectric_force_x_n),
            "true_3d_enclosure_reaction_x_n": float(result.finite_3d_model.true_3d_enclosure_force_x_n),
            "true_3d_net_system_force_x_n": float(result.finite_3d_model.true_3d_net_system_force_x_n),
            "true_3d_relative_residual": float(result.finite_3d_model.true_3d_relative_residual),
            "true_3d_is_conserved": bool(result.finite_3d_model.true_3d_is_conserved),
            "extruded_2d_blade_force_at_matched_dx_n": float(
                result.finite_3d_model.extruded_2d_blade_force_at_matched_dx_n
            ),
            "end_fringing_ratio_3d_to_extruded_2d": float(
                result.finite_3d_model.end_fringing_ratio_3d_to_extruded_2d
            ),
        },
        "h1_patent_alternative_prediction": {
            "transcribed_formula": "F = epsilon_0 * (E2^2 * A2 - E1^2 * A1)",
            "equation_citation": "US11511891B2 Equation (11), Column 9",
            "effective_proximal_field_v_per_m": float(result.h1_prediction.effective_proximal_field_v_per_m),
            "effective_distal_field_v_per_m": float(result.h1_prediction.effective_distal_field_v_per_m),
            "mean_proximal_field_v_per_m": float(result.h1_prediction.mean_proximal_field_v_per_m),
            "mean_distal_field_v_per_m": float(result.h1_prediction.mean_distal_field_v_per_m),
            "proximal_face_width_m": float(result.h1_prediction.proximal_width_m),
            "distal_face_width_m": float(result.h1_prediction.distal_width_m),
            "predicted_force_per_length_n_per_m": float(result.h1_prediction.predicted_force_per_length_n_per_m),
            "mean_field_plugin_force_per_length_n_per_m": float(
                result.h1_prediction.mean_field_plugin_force_per_length_n_per_m
            ),
            "predicted_force_3d_extruded_n": float(result.h1_prediction.predicted_force_3d_extruded_n),
            "missing_half_factor_force_3d_extruded_n": float(
                result.h1_prediction.missing_half_factor_force_3d_extruded_n
            ),
            "proof_obligations": result.h1_prediction.proof_obligation_notes,
        },
        "separated_fig21_nine_blade_epoxy_embodiment_summary": {
            "embodiment_id": fig21_params.embodiment_id,
            "num_blades": fig21_params.num_blades,
            "dielectric_relative_permittivity_assumed": float(fig21_params.dielectric_relative_permittivity),
            "h0_blade_force_x_3d_extruded_n": float(fig21_h0.blade_force_x.force_3d_extruded_n),
            "h0_ground_force_x_3d_extruded_n": float(fig21_h0.ground_force_x.force_3d_extruded_n),
            "h0_dielectric_force_x_3d_extruded_n": float(fig21_h0.dielectric_force_x.force_3d_extruded_n),
            "h0_enclosure_direct_wall_x_3d_extruded_n": float(
                fig21_h0.enclosure_direct_wall_force_x.total_enclosure_force_3d_extruded_n
            ),
            "h0_net_system_force_x_3d_extruded_n": float(fig21_h0.net_system_force_x.force_3d_extruded_n),
            "h1_predicted_force_3d_extruded_n": float(fig21_h1.predicted_force_3d_extruded_n),
            "dimensional_status": "EXTRUDED_2D_APPROXIMATION_NOT_VALIDATED_FOR_PHYSICAL_FIG21_ARTICLE",
        },
        "evaluated_controls_and_contextual_literature": {
            "polarity_reversal_evaluated": bool(result.controls.polarity_reversal_evaluated),
            "polarity_reversal_max_field_diff_relative": float(
                result.controls.polarity_reversal_max_field_diff_relative
            ),
            "polarity_reversal_diff_relative": float(
                result.controls.polarity_reversal_blade_force_diff_relative
            ),
            "symmetric_control_evaluated": bool(result.controls.symmetric_control_evaluated),
            "symmetric_blade_force_n_per_m": float(result.controls.symmetric_blade_force_n_per_m),
            "symmetric_ground_force_n_per_m": float(result.controls.symmetric_ground_force_n_per_m),
            "symmetric_control_net_force_3d_n": float(result.controls.symmetric_control_net_force_3d_n),
            "voltage_off_evaluated": bool(result.controls.voltage_off_evaluated),
            "voltage_off_max_field_v_per_m": float(result.controls.voltage_off_max_field_v_per_m),
            "voltage_off_force_n_per_m": float(result.controls.voltage_off_blade_force_n_per_m),
            "inversion_180_evaluated": bool(result.controls.inversion_180_evaluated),
            "inversion_180_base_blade_force_x_n_per_m": float(
                result.controls.inversion_180_base_blade_force_x_n_per_m
            ),
            "inversion_180_inverted_blade_force_x_n_per_m": float(
                result.controls.inversion_180_inverted_blade_force_x_n_per_m
            ),
            "inversion_180_relative_reversal_error": float(
                result.controls.inversion_180_relative_reversal_error
            ),
            "inversion_180_vector_reversed": bool(result.controls.inversion_180_vector_reversed),
            "wall_proximity_control_evaluated": bool(result.controls.wall_proximity_control_evaluated),
            "wall_proximity_symmetric_pair_force_n_per_m": float(
                result.controls.wall_proximity_symmetric_pair_force_n_per_m
            ),
            "wall_proximity_asymmetric_pair_force_n_per_m": float(
                result.controls.wall_proximity_asymmetric_pair_force_n_per_m
            ),
            "wall_proximity_asymmetric_wall_reaction_n_per_m": float(
                result.controls.wall_proximity_asymmetric_wall_reaction_n_per_m
            ),
            "wall_proximity_asymmetric_net_residual_n_per_m": float(
                result.controls.wall_proximity_asymmetric_net_residual_n_per_m
            ),
            "physical_laboratory_controls_status": result.controls.physical_controls_status,
            "unperformed_physical_controls": result.controls.unperformed_physical_controls,
            "literature_audit": asdict(result.controls.literature_audit),
            "literature_benchmark_citation": result.controls.literature_benchmark_citation,
            "literature_benchmark_summary": result.controls.literature_benchmark_summary,
        },
        "scientific_disposition": {
            "theoretical_h0_status": "CONSERVED_ZERO_NET_MOMENTUM_IN_CLOSED_SYSTEM",
            "computational_h0_status": "VERIFIED_BY_DIRECT_WALL_TRACTION_AND_3D_STRESS_INTEGRATION",
            "model_h1_status": "REFUTED_DERIVATION_OMITS_HALF_FACTOR_AND_REACTION_SURFACES",
            "physical_thrust_measurement": "NOT_MEASURED_AND_NOT_EVALUATED_NUMERICAL_SIMULATION_ONLY",
            "epistemic_warning": (
                "An educational field visualizer or patent issuance does NOT establish anomalous propellantless thrust. "
                "Closed-surface Maxwell stress integration confirms zero net momentum transfer in a closed static system. "
                "The patent's Eq. (11) calculation omits reaction stresses and the factor of 1/2. "
                "Cross-apparatus literature comparisons (Tajmar & Schreiber 2020 at 10 kV vs Patent FIG. 21 at 25 kV) "
                "are contextual only; corona/ion-wind, lead-wire forces, and chamber Coulomb coupling are candidate "
                "confounders requiring experimental discrimination rather than established causes."
            ),
        },
    }

    if output_path is not None:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    return manifest
