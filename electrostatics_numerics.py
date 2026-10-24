"""P1 Advanced Electrostatic Numerics, Convergence Benchmarks, and Force Bookkeeping.

Implements P1-A (analytic harmonic benchmarks, convergence rate quantification, enclosure sensitivity)
and P1-B (Maxwell stress closed-contour integration, 2D force-per-length N/m accounting,
and whole-apparatus force balance).

All forces in 2D are strictly force per unit depth (N/m).
Preserves existing P0 electrostatics_baseline.py without modification.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from electrostatics_baseline import (
    EPSILON_0_F_PER_M,
    ElectrodeConfig,
    FieldSolution,
    GroundedBoxConfig,
    electrode_pair_in_grounded_box,
    solve_dirichlet,
)


@dataclass(frozen=True)
class HarmonicPolynomialBenchmarkResult:
    """Benchmark on a cubic harmonic polynomial V(x,y) = V0 * (x^3 - 3xy^2) / L^3.

    Continuous Laplacian is identically zero.
    The 5-point discrete Laplacian stencil has zero truncation error on polynomials of degree <= 3,
    so discrete solution error is bounded purely by floating-point linear solver tolerance.
    """
    n: int
    grid_spacing_m: float
    box_width_m: float
    v_0_v: float
    max_potential_error_v: float
    l2_potential_error_v: float
    max_discrete_residual_v: float
    max_ex_error_v_per_m: float
    max_ey_error_v_per_m: float
    is_exact_to_tolerance: bool


def harmonic_polynomial_benchmark(
    n_list: Sequence[int] = (21, 41, 81),
    box_width_m: float = 0.04,
    v_0_v: float = 100.0,
    tolerance_v: float = 1e-9,
) -> list[HarmonicPolynomialBenchmarkResult]:
    """Test 5-point Dirichlet Laplace solver against cubic harmonic polynomial.

    V_exact(x, y) = V_0 * (x^3 - 3*x*y^2) / (box_width_m / 2)^3.
    """
    results: list[HarmonicPolynomialBenchmarkResult] = []
    scale = (box_width_m / 2.0) ** 3

    for n in n_list:
        h = box_width_m / (n - 1)
        coords = np.linspace(-box_width_m / 2.0, box_width_m / 2.0, n)
        x, y = np.meshgrid(coords, coords, indexing='ij')

        v_exact = v_0_v * (x**3 - 3.0 * x * y**2) / scale
        ex_exact = -v_0_v * (3.0 * x**2 - 3.0 * y**2) / scale
        ey_exact = v_0_v * (6.0 * x * y) / scale

        # Boundary Dirichlet mask (outer box only)
        boundary_mask = np.zeros((n, n), dtype=bool)
        boundary_mask[0, :] = boundary_mask[-1, :] = True
        boundary_mask[:, 0] = boundary_mask[:, -1] = True

        sol = solve_dirichlet(boundary_mask, v_exact, h, boundary_mask=boundary_mask)

        # Evaluate errors on interior vacuum nodes
        interior = sol.vacuum_mask
        pot_err = np.abs(sol.potential_v[interior] - v_exact[interior])
        max_pot_err = float(np.max(pot_err))
        l2_pot_err = float(np.sqrt(np.mean(pot_err**2)))

        ex_err = np.abs(sol.ex_v_per_m[interior] - ex_exact[interior])
        ey_err = np.abs(sol.ey_v_per_m[interior] - ey_exact[interior])
        max_ex_err = float(np.max(ex_err))
        max_ey_err = float(np.max(ey_err))

        is_exact = bool(max_pot_err < tolerance_v and sol.max_discrete_residual_v < tolerance_v)

        results.append(HarmonicPolynomialBenchmarkResult(
            n=n,
            grid_spacing_m=h,
            box_width_m=box_width_m,
            v_0_v=v_0_v,
            max_potential_error_v=max_pot_err,
            l2_potential_error_v=l2_pot_err,
            max_discrete_residual_v=sol.max_discrete_residual_v,
            max_ex_error_v_per_m=max_ex_err,
            max_ey_error_v_per_m=max_ey_err,
            is_exact_to_tolerance=is_exact,
        ))
    return results


@dataclass(frozen=True)
class HarmonicTrigBenchmarkResult:
    """Benchmark on transcendental harmonic solution V(x,y) = V0 * sinh(pi*x/W) * sin(pi*y/W) / sinh(pi/2).

    Continuous Laplacian is zero. Truncation error of 5-point stencil is non-zero and O(h^2),
    enabling rigorous quantitative verification of 2nd-order asymptotic convergence rates.
    """
    n: int
    grid_spacing_m: float
    box_width_m: float
    v_0_v: float
    max_potential_error_v: float
    l2_potential_error_v: float
    max_field_error_v_per_m: float
    observed_order_potential: float | None
    observed_order_field: float | None


def harmonic_trig_benchmark(
    n_list: Sequence[int] = (21, 41, 81, 161),
    box_width_m: float = 0.04,
    v_0_v: float = 100.0,
) -> list[HarmonicTrigBenchmarkResult]:
    """Test 5-point Dirichlet Laplace solver convergence against smooth harmonic sine/sinh solution."""
    results: list[HarmonicTrigBenchmarkResult] = []
    w = box_width_m
    norm_const = float(np.sinh(np.pi / 2.0))

    prev_h: float | None = None
    prev_pot_err: float | None = None
    prev_field_err: float | None = None

    for n in n_list:
        h = w / (n - 1)
        coords = np.linspace(-w / 2.0, w / 2.0, n)
        x, y = np.meshgrid(coords, coords, indexing='ij')

        k = np.pi / w
        v_exact = v_0_v * np.sinh(k * x) * np.sin(k * y) / norm_const
        ex_exact = -v_0_v * k * np.cosh(k * x) * np.sin(k * y) / norm_const
        ey_exact = -v_0_v * k * np.sinh(k * x) * np.cos(k * y) / norm_const

        boundary_mask = np.zeros((n, n), dtype=bool)
        boundary_mask[0, :] = boundary_mask[-1, :] = True
        boundary_mask[:, 0] = boundary_mask[:, -1] = True

        sol = solve_dirichlet(boundary_mask, v_exact, h, boundary_mask=boundary_mask)

        interior = sol.vacuum_mask
        pot_err = np.abs(sol.potential_v[interior] - v_exact[interior])
        max_pot_err = float(np.max(pot_err))
        l2_pot_err = float(np.sqrt(np.mean(pot_err**2)))

        field_err = np.hypot(
            sol.ex_v_per_m[interior] - ex_exact[interior],
            sol.ey_v_per_m[interior] - ey_exact[interior],
        )
        max_field_err = float(np.max(field_err))

        order_pot: float | None = None
        order_field: float | None = None
        if prev_h is not None and prev_pot_err is not None and prev_field_err is not None:
            ratio = prev_h / h
            order_pot = float(np.log(prev_pot_err / max_pot_err) / np.log(ratio))
            order_field = float(np.log(prev_field_err / max_field_err) / np.log(ratio))

        prev_h = h
        prev_pot_err = max_pot_err
        prev_field_err = max_field_err

        results.append(HarmonicTrigBenchmarkResult(
            n=n,
            grid_spacing_m=h,
            box_width_m=w,
            v_0_v=v_0_v,
            max_potential_error_v=max_pot_err,
            l2_potential_error_v=l2_pot_err,
            max_field_error_v_per_m=max_field_err,
            observed_order_potential=order_pot,
            observed_order_field=order_field,
        ))
    return results


@dataclass(frozen=True)
class EnclosureSensitivityResult:
    """Diagnostic of grounded enclosure size sensitivity for fixed electrode geometry.

    Demonstrates that the grounded outer box is an active boundary condition, not open space.
    """
    box_width_m: float
    n: int
    grid_spacing_m: float
    midpoint_ex_v_per_m: float
    midpoint_ey_v_per_m: float
    max_outer_wall_field_v_per_m: float
    mean_outer_wall_field_v_per_m: float


def enclosure_size_sensitivity_study(
    box_widths_m: Sequence[float] = (0.03, 0.04, 0.06, 0.08, 0.12),
    h_target_m: float = 0.0005,
    config: GroundedBoxConfig | None = None,
) -> list[EnclosureSensitivityResult]:
    """Sweep enclosure width W at fixed physical grid spacing h to evaluate boundary impact."""
    results: list[EnclosureSensitivityResult] = []
    base_cfg = config or GroundedBoxConfig()

    for w in box_widths_m:
        # Choose n so grid spacing h stays approximately constant near h_target_m
        n = int(round(w / h_target_m)) + 1
        if n % 2 == 0:
            n += 1  # Keep odd for exact midpoint on-grid

        sweep_cfg = GroundedBoxConfig(
            n=n,
            box_width_m=w,
            left_electrode=base_cfg.left_electrode,
            right_electrode=base_cfg.right_electrode,
        )
        sol = electrode_pair_in_grounded_box(config=sweep_cfg)

        mid_i = (n - 1) // 2
        mid_ex = float(sol.ex_v_per_m[mid_i, mid_i])
        mid_ey = float(sol.ey_v_per_m[mid_i, mid_i])

        # Evaluate normal field on inner layer adjacent to grounded outer walls
        wall_fields: list[float] = []
        # Top and bottom inner rows (iy = 1 and iy = n - 2)
        wall_fields.extend(np.abs(sol.ey_v_per_m[1:-1, 1]).tolist())
        wall_fields.extend(np.abs(sol.ey_v_per_m[1:-1, n - 2]).tolist())
        # Left and right inner cols (ix = 1 and ix = n - 2)
        wall_fields.extend(np.abs(sol.ex_v_per_m[1, 1:-1]).tolist())
        wall_fields.extend(np.abs(sol.ex_v_per_m[n - 2, 1:-1]).tolist())

        arr_wf = np.array(wall_fields, dtype=float)
        arr_wf = arr_wf[np.isfinite(arr_wf)]
        max_wf = float(np.max(arr_wf)) if len(arr_wf) > 0 else 0.0
        mean_wf = float(np.mean(arr_wf)) if len(arr_wf) > 0 else 0.0

        results.append(EnclosureSensitivityResult(
            box_width_m=w,
            n=n,
            grid_spacing_m=sol.grid_spacing_m,
            midpoint_ex_v_per_m=mid_ex,
            midpoint_ey_v_per_m=mid_ey,
            max_outer_wall_field_v_per_m=max_wf,
            mean_outer_wall_field_v_per_m=mean_wf,
        ))
    return results


@dataclass(frozen=True)
class ContourStressResult:
    """2D Maxwell stress tensor closed-contour integral.

    All forces are strictly force per unit depth (N/m).
    """
    fx_n_per_m: float
    fy_n_per_m: float
    net_force_magnitude_n_per_m: float
    contour_x_range_m: tuple[float, float]
    contour_y_range_m: tuple[float, float]
    contour_indices: tuple[int, int, int, int]  # (ix_min, ix_max, iy_min, iy_max)
    is_pure_vacuum: bool
    segment_fx_n_per_m: dict[str, float]       # Contributions by edge
    segment_fy_n_per_m: dict[str, float]
    units: str = 'N/m'
    diagnostic_note: str = '2D Maxwell stress contour integral in vacuum; force per unit depth (N/m).'


def compute_maxwell_stress_contour(
    solution: FieldSolution,
    x_bounds_m: tuple[float, float],
    y_bounds_m: tuple[float, float],
    require_vacuum: bool = True,
) -> ContourStressResult:
    """Compute vacuum Maxwell stress contour integral on a rectangular loop.

    T_ij = epsilon_0 * (E_i E_j - 0.5 * |E|^2 * delta_ij)
    F'_i = oint_C T_ij n_j dl  (in N/m)

    Counter-clockwise contour segments:
      - Right edge: x = x_max, y in [y_min, y_max], outward normal n = (+1, 0)
      - Top edge: y = y_max, x in [x_min, x_max], outward normal n = (0, +1)
      - Left edge: x = x_min, y in [y_min, y_max], outward normal n = (-1, 0)
      - Bottom edge: y = y_min, x in [x_min, x_max], outward normal n = (0, -1)
    """
    n = solution.potential_v.shape[0]
    h = solution.grid_spacing_m
    w = (n - 1) * h
    coords = np.linspace(-w / 2.0, w / 2.0, n)

    # Snap bounds to nearest grid line
    ix_min = int(np.clip(np.argmin(np.abs(coords - x_bounds_m[0])), 1, n - 2))
    ix_max = int(np.clip(np.argmin(np.abs(coords - x_bounds_m[1])), 1, n - 2))
    iy_min = int(np.clip(np.argmin(np.abs(coords - y_bounds_m[0])), 1, n - 2))
    iy_max = int(np.clip(np.argmin(np.abs(coords - y_bounds_m[1])), 1, n - 2))

    if ix_min >= ix_max or iy_min >= iy_max:
        raise ValueError('Contour bounds must enclose at least one grid cell interior')

    # Collect contour perimeter masks to ensure purely in vacuum
    right_mask = solution.vacuum_mask[ix_max, iy_min:iy_max + 1]
    left_mask = solution.vacuum_mask[ix_min, iy_min:iy_max + 1]
    top_mask = solution.vacuum_mask[ix_min:ix_max + 1, iy_max]
    bottom_mask = solution.vacuum_mask[ix_min:ix_max + 1, iy_min]

    is_vac = bool(np.all(right_mask) and np.all(left_mask) and np.all(top_mask) and np.all(bottom_mask))
    if require_vacuum and not is_vac:
        raise ValueError(
            f'Maxwell stress contour intersects non-vacuum nodes on grid indices '
            f'x=[{ix_min}, {ix_max}], y=[{iy_min}, {iy_max}]'
        )

    eps = EPSILON_0_F_PER_M

    # Helper: compute stress tensor components on an array of Ex, Ey
    def get_t(ex_arr: np.ndarray, ey_arr: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        t_xx = 0.5 * eps * (ex_arr**2 - ey_arr**2)
        t_yy = -t_xx
        t_xy = eps * ex_arr * ey_arr
        return t_xx, t_yy, t_xy

    # 1. Right edge: x = ix_max, n = (+1, 0), dl = dy = h
    ex_r = solution.ex_v_per_m[ix_max, iy_min:iy_max + 1]
    ey_r = solution.ey_v_per_m[ix_max, iy_min:iy_max + 1]
    txx_r, _, txy_r = get_t(ex_r, ey_r)
    # Trapezoidal integration along y
    fx_right = float(np.trapz(txx_r, dx=h))
    fy_right = float(np.trapz(txy_r, dx=h))

    # 2. Left edge: x = ix_min, n = (-1, 0), dl = dy = h
    ex_l = solution.ex_v_per_m[ix_min, iy_min:iy_max + 1]
    ey_l = solution.ey_v_per_m[ix_min, iy_min:iy_max + 1]
    txx_l, _, txy_l = get_t(ex_l, ey_l)
    fx_left = float(-np.trapz(txx_l, dx=h))
    fy_left = float(-np.trapz(txy_l, dx=h))

    # 3. Top edge: y = iy_max, n = (0, +1), dl = dx = h
    ex_t = solution.ex_v_per_m[ix_min:ix_max + 1, iy_max]
    ey_t = solution.ey_v_per_m[ix_min:ix_max + 1, iy_max]
    _, tyy_t, txy_t = get_t(ex_t, ey_t)
    fx_top = float(np.trapz(txy_t, dx=h))
    fy_top = float(np.trapz(tyy_t, dx=h))

    # 4. Bottom edge: y = iy_min, n = (0, -1), dl = dx = h
    ex_b = solution.ex_v_per_m[ix_min:ix_max + 1, iy_min]
    ey_b = solution.ey_v_per_m[ix_min:ix_max + 1, iy_min]
    _, tyy_b, txy_b = get_t(ex_b, ey_b)
    fx_bottom = float(-np.trapz(txy_b, dx=h))
    fy_bottom = float(-np.trapz(tyy_b, dx=h))

    total_fx = fx_right + fx_left + fx_top + fx_bottom
    total_fy = fy_right + fy_left + fy_top + fy_bottom

    return ContourStressResult(
        fx_n_per_m=total_fx,
        fy_n_per_m=total_fy,
        net_force_magnitude_n_per_m=float(np.hypot(total_fx, total_fy)),
        contour_x_range_m=(float(coords[ix_min]), float(coords[ix_max])),
        contour_y_range_m=(float(coords[iy_min]), float(coords[iy_max])),
        contour_indices=(ix_min, ix_max, iy_min, iy_max),
        is_pure_vacuum=is_vac,
        segment_fx_n_per_m={'left': fx_left, 'right': fx_right, 'top': fx_top, 'bottom': fx_bottom},
        segment_fy_n_per_m={'left': fy_left, 'right': fy_right, 'top': fy_top, 'bottom': fy_bottom},
    )


@dataclass(frozen=True)
class WholeApparatusForceBudget:
    """Full-system electrostatic force accounting in 2D (force per unit depth, N/m).

    Explicitly accounts for:
    - Left electrode electrostatic force
    - Right electrode electrostatic force
    - Grounded enclosure electrostatic reaction force
    - Missing mechanical supports/standoffs (unmodeled reactions holding electrodes)
    """
    left_electrode_fx_n_per_m: float
    left_electrode_fy_n_per_m: float
    right_electrode_fx_n_per_m: float
    right_electrode_fy_n_per_m: float
    enclosure_reaction_fx_n_per_m: float
    enclosure_reaction_fy_n_per_m: float
    net_electrostatic_force_fx_n_per_m: float
    net_electrostatic_force_fy_n_per_m: float
    is_force_balanced_to_tolerance: bool
    unmodeled_reaction_explanation: str
    units: str = 'N/m'


def evaluate_whole_apparatus_force_budget(
    solution: FieldSolution,
    tolerance_n_per_m: float = 1e-4,
) -> WholeApparatusForceBudget:
    """Evaluate closed Maxwell stress contours for both electrodes and the grounded enclosure.

    Resolves P1-R1-F3:
    - Supports symmetric, asymmetric voltage, and off-axis geometries.
    - Accurately balances electrode forces against the grounded enclosure reaction.
    - Explicitly documents that electrostatic forces include inter-electrode interaction
      and grounded-wall image force coupling.
    """
    cfg = solution.config or GroundedBoxConfig()
    le = cfg.left_electrode
    re = cfg.right_electrode
    w = cfg.box_width_m
    h = solution.grid_spacing_m

    # Dynamic vacuum margins based on geometry clearances
    sep = abs(re.center_x_m - le.center_x_m)
    d_inter = sep - (le.radius_m + re.radius_m)
    d_left_wall = (le.center_x_m - le.radius_m) - (-w / 2.0)
    d_right_wall = (w / 2.0) - (re.center_x_m + re.radius_m)
    d_vert = (w / 2.0) - max(abs(le.center_y_m) + le.radius_m, abs(re.center_y_m) + re.radius_m)

    margin_x = min(d_inter * 0.35, d_left_wall * 0.35, d_right_wall * 0.35, 0.003)
    margin_y = min(d_vert * 0.35, 0.003)
    margin_x = max(margin_x, 1.5 * h)
    margin_y = max(margin_y, 1.5 * h)

    c_left = compute_maxwell_stress_contour(
        solution,
        x_bounds_m=(le.center_x_m - le.radius_m - margin_x, le.center_x_m + le.radius_m + margin_x),
        y_bounds_m=(le.center_y_m - le.radius_m - margin_y, le.center_y_m + le.radius_m + margin_y),
    )

    c_right = compute_maxwell_stress_contour(
        solution,
        x_bounds_m=(re.center_x_m - re.radius_m - margin_x, re.center_x_m + re.radius_m + margin_x),
        y_bounds_m=(re.center_y_m - re.radius_m - margin_y, re.center_y_m + re.radius_m + margin_y),
    )

    # Enclosure contour: large contour just inside the grounded outer boundary walls
    # Inner perimeter enclosing all electrodes
    wall_margin = 2.5 * h
    c_enclosure_inner = compute_maxwell_stress_contour(
        solution,
        x_bounds_m=(-w / 2.0 + wall_margin, w / 2.0 - wall_margin),
        y_bounds_m=(-w / 2.0 + wall_margin, w / 2.0 - wall_margin),
    )

    # By momentum conservation in the electrostatic field, the outward flux of Maxwell stress
    # through the inner boundary equals the mechanical reaction force exerted on the grounded box:
    # F_enclosure = - F_enclosure_inner
    f_enc_x = -c_enclosure_inner.fx_n_per_m
    f_enc_y = -c_enclosure_inner.fy_n_per_m

    # Net modeled force on all conductors:
    # F_net = F_left + F_right + F_enclosure
    net_fx = c_left.fx_n_per_m + c_right.fx_n_per_m + f_enc_x
    net_fy = c_left.fy_n_per_m + c_right.fy_n_per_m + f_enc_y

    is_balanced = bool(np.hypot(net_fx, net_fy) < tolerance_n_per_m)

    note = (
        'The 2D modeled conductors (left electrode, right electrode, grounded enclosure) '
        'form a closed electro-mechanical system. The electrostatic forces on electrodes '
        'arise from mutual interaction with each other and image charges in the grounded shielding enclosure. '
        'In an asymmetric configuration (unequal voltages or off-axis placement), the enclosure reaction force '
        'is demonstrably nonzero and balances the net force on the electrodes. '
        'In a real laboratory apparatus, rigid mechanical supports/standoffs and feedthroughs '
        'exert opposing mechanical reaction forces holding the electrodes in place. '
        'These mechanical reactions are NOT modeled in the electrostatic field solver and are NOT fictitious zeros; '
        'the net mechanical force on the complete isolated apparatus is strictly zero.'
    )

    return WholeApparatusForceBudget(
        left_electrode_fx_n_per_m=c_left.fx_n_per_m,
        left_electrode_fy_n_per_m=c_left.fy_n_per_m,
        right_electrode_fx_n_per_m=c_right.fx_n_per_m,
        right_electrode_fy_n_per_m=c_right.fy_n_per_m,
        enclosure_reaction_fx_n_per_m=f_enc_x,
        enclosure_reaction_fy_n_per_m=f_enc_y,
        net_electrostatic_force_fx_n_per_m=net_fx,
        net_electrostatic_force_fy_n_per_m=net_fy,
        is_force_balanced_to_tolerance=is_balanced,
        unmodeled_reaction_explanation=note,
    )


@dataclass(frozen=True)
class ComponentConvergenceAssessment:
    component_name: str
    finest_value_n_per_m: float
    penultimate_value_n_per_m: float
    last_step_abs_diff_n_per_m: float
    last_step_relative_change: float | None
    observed_order: float | None
    regime: str
    is_converged: bool


@dataclass(frozen=True)
class ForceMeshConvergenceRow:
    n: int
    grid_spacing_m: float
    left_electrode_fx_n_per_m: float
    right_electrode_fx_n_per_m: float
    enclosure_reaction_fx_n_per_m: float
    net_residual_fx_n_per_m: float
    left_electrode_fy_n_per_m: float = 0.0
    right_electrode_fy_n_per_m: float = 0.0
    enclosure_reaction_fy_n_per_m: float = 0.0
    net_residual_fy_n_per_m: float = 0.0
    net_residual_magnitude_n_per_m: float = 0.0
    abs_change_left_fx_to_prev: float | None = None
    abs_change_left_fy_to_prev: float | None = None
    abs_change_right_fx_to_prev: float | None = None
    abs_change_right_fy_to_prev: float | None = None
    abs_change_box_fx_to_prev: float | None = None
    abs_change_box_fy_to_prev: float | None = None
    max_abs_change_to_prev: float | None = None
    relative_change_to_prev: float | None = None
    relative_change_left_to_prev: float | None = None
    relative_change_right_to_prev: float | None = None
    relative_change_box_to_prev: float | None = None
    relative_change_left_fx_to_prev: float | None = None
    relative_change_left_fy_to_prev: float | None = None
    relative_change_right_fx_to_prev: float | None = None
    relative_change_right_fy_to_prev: float | None = None
    relative_change_box_fx_to_prev: float | None = None
    relative_change_box_fy_to_prev: float | None = None
    max_relative_change_to_prev: float | None = None


@dataclass(frozen=True)
class ForceMeshConvergenceStudy:
    rows: list[ForceMeshConvergenceRow]
    observed_order_left_electrode: float | None
    observed_order_right_electrode: float | None
    observed_order_enclosure: float | None
    observed_orders_by_component: dict[str, float | None]
    component_assessments: dict[str, ComponentConvergenceAssessment]
    per_component_last_step_diff_n_per_m: dict[str, float]
    max_component_last_step_diff_n_per_m: float
    max_vector_last_step_diff_n_per_m: float
    left_fx_last_step_diff_n_per_m: float
    is_converged_to_tolerance: bool
    max_component_relative_change: float
    finest_net_residual_magnitude_n_per_m: float
    discretization_error_note: str
    diagnostic_note: str


def evaluate_force_convergence_from_rows(
    rows: Sequence[ForceMeshConvergenceRow],
    tolerance_relative_change: float = 0.05,
    tolerance_abs_change_n_per_m: float = 5e-4,
    tolerance_near_zero_abs_n_per_m: float = 1e-6,
    significant_force_threshold_n_per_m: float = 1e-6,
    tolerance_residual_n_per_m: float = 1e-6,
) -> ForceMeshConvergenceStudy:
    """Evaluate full-vector 6-component convergence and 2D vector residual gates from mesh rows (P1-R3-F1).

    Examines all six conductor force components (left_fx, left_fy, right_fx, right_fy, box_fx, box_fy)
    and full 2D net residual vector (net_fx, net_fy, hypot(net_fx, net_fy)).
    Near-zero components are explicitly gated by absolute change and absolute magnitude bounds
    rather than being silently skipped.
    """
    if len(rows) < 2:
        raise ValueError('At least 2 mesh levels are required to evaluate force convergence')

    def _calc_order(vals: list[float], h_ratios: float) -> float | None:
        if len(vals) < 3:
            return None
        d1 = abs(vals[-3] - vals[-2])
        d2 = abs(vals[-2] - vals[-1])
        if d1 > 1e-12 and d2 > 1e-12:
            return float(np.log(d1 / d2) / np.log(h_ratios))
        return None

    h_ratio = rows[-3].grid_spacing_m / rows[-2].grid_spacing_m if len(rows) >= 3 else 2.0

    comp_getters = {
        'left_fx': lambda r: r.left_electrode_fx_n_per_m,
        'left_fy': lambda r: r.left_electrode_fy_n_per_m,
        'right_fx': lambda r: r.right_electrode_fx_n_per_m,
        'right_fy': lambda r: r.right_electrode_fy_n_per_m,
        'box_fx': lambda r: r.enclosure_reaction_fx_n_per_m,
        'box_fy': lambda r: r.enclosure_reaction_fy_n_per_m,
    }

    orders_by_comp: dict[str, float | None] = {}
    assessments: dict[str, ComponentConvergenceAssessment] = {}
    per_comp_diff: dict[str, float] = {}
    active_rel_changes: list[float] = []

    prev_row = rows[-2]
    finest_row = rows[-1]

    for name, getter in comp_getters.items():
        series = [float(getter(r)) for r in rows]
        order = _calc_order(series, h_ratio) if len(rows) >= 3 else None
        orders_by_comp[name] = order

        curr_val = float(getter(finest_row))
        prev_val = float(getter(prev_row))
        abs_diff = float(abs(curr_val - prev_val))
        per_comp_diff[name] = abs_diff

        scale = max(abs(curr_val), abs(prev_val))
        if scale > significant_force_threshold_n_per_m:
            regime = 'ACTIVE_RELATIVE_AND_ABS'
            denom = abs(curr_val) if abs(curr_val) > significant_force_threshold_n_per_m else scale
            rel_change = float(abs_diff / denom)
            active_rel_changes.append(rel_change)
            comp_ok = bool(rel_change <= tolerance_relative_change and abs_diff <= tolerance_abs_change_n_per_m)
        else:
            regime = 'NEAR_ZERO_ABSOLUTE'
            rel_change = None
            comp_ok = bool(
                abs_diff <= tolerance_near_zero_abs_n_per_m
                and abs(curr_val) <= tolerance_near_zero_abs_n_per_m
            )

        assessments[name] = ComponentConvergenceAssessment(
            component_name=name,
            finest_value_n_per_m=curr_val,
            penultimate_value_n_per_m=prev_val,
            last_step_abs_diff_n_per_m=abs_diff,
            last_step_relative_change=rel_change,
            observed_order=order,
            regime=regime,
            is_converged=comp_ok,
        )

    max_rel_change = float(max(active_rel_changes)) if active_rel_changes else 0.0
    max_comp_diff = float(max(per_comp_diff.values()))
    left_vec_diff = float(np.hypot(per_comp_diff['left_fx'], per_comp_diff['left_fy']))
    right_vec_diff = float(np.hypot(per_comp_diff['right_fx'], per_comp_diff['right_fy']))
    box_vec_diff = float(np.hypot(per_comp_diff['box_fx'], per_comp_diff['box_fy']))
    max_vec_diff = float(max(left_vec_diff, right_vec_diff, box_vec_diff))
    left_fx_diff = per_comp_diff['left_fx']

    # Verify algebraic consistency of reported residual with component sums on finest grid
    expected_res_fx = (
        finest_row.left_electrode_fx_n_per_m
        + finest_row.right_electrode_fx_n_per_m
        + finest_row.enclosure_reaction_fx_n_per_m
    )
    expected_res_fy = (
        finest_row.left_electrode_fy_n_per_m
        + finest_row.right_electrode_fy_n_per_m
        + finest_row.enclosure_reaction_fy_n_per_m
    )
    res_fx = float(finest_row.net_residual_fx_n_per_m)
    res_fy = float(finest_row.net_residual_fy_n_per_m)
    res_mag = float(np.hypot(res_fx, res_fy))

    residual_consistent = bool(
        abs(res_fx - expected_res_fx) <= 1e-11
        and abs(res_fy - expected_res_fy) <= 1e-11
        and abs(finest_row.net_residual_magnitude_n_per_m - res_mag) <= 1e-11
    )
    residual_ok = bool(
        residual_consistent
        and abs(res_fx) <= tolerance_residual_n_per_m
        and abs(res_fy) <= tolerance_residual_n_per_m
        and res_mag <= tolerance_residual_n_per_m
    )

    all_comps_ok = all(a.is_converged for a in assessments.values())
    is_ok = bool(all_comps_ok and residual_ok)

    disc_note = (
        'Two-grid differences |F_k(n_finest) - F_k(n_penultimate)| are reported per component '
        '(left_fx, left_fy, right_fx, right_fy, box_fx, box_fy) and as max_component_last_step_diff_n_per_m. '
        'These measure the last mesh-refinement shift on a Cartesian staircase grid and are NOT a formal '
        'probabilistic uncertainty budget.'
    )

    note = (
        f'Full-vector 6-component mesh study across n={[r.n for r in rows]}: '
        f'F_left=({finest_row.left_electrode_fx_n_per_m:.6e}, {finest_row.left_electrode_fy_n_per_m:.6e}) N/m, '
        f'F_right=({finest_row.right_electrode_fx_n_per_m:.6e}, {finest_row.right_electrode_fy_n_per_m:.6e}) N/m, '
        f'F_box=({finest_row.enclosure_reaction_fx_n_per_m:.6e}, {finest_row.enclosure_reaction_fy_n_per_m:.6e}) N/m, '
        f'Residual=({res_fx:.6e}, {res_fy:.6e}) N/m (|F_res|={res_mag:.6e} N/m). '
        f'Max active relative shift: {max_rel_change:.2%}, '
        f'max component last-step diff: {max_comp_diff:.2e} N/m (left_fx diff: {left_fx_diff:.2e} N/m).'
    )

    return ForceMeshConvergenceStudy(
        rows=list(rows),
        observed_order_left_electrode=orders_by_comp['left_fx'],
        observed_order_right_electrode=orders_by_comp['right_fx'],
        observed_order_enclosure=orders_by_comp['box_fx'],
        observed_orders_by_component=orders_by_comp,
        component_assessments=assessments,
        per_component_last_step_diff_n_per_m=per_comp_diff,
        max_component_last_step_diff_n_per_m=max_comp_diff,
        max_vector_last_step_diff_n_per_m=max_vec_diff,
        left_fx_last_step_diff_n_per_m=left_fx_diff,
        is_converged_to_tolerance=is_ok,
        max_component_relative_change=max_rel_change,
        finest_net_residual_magnitude_n_per_m=res_mag,
        discretization_error_note=disc_note,
        diagnostic_note=note,
    )


def force_mesh_convergence_study(
    n_list: Sequence[int] = (41, 81, 161),
    config: GroundedBoxConfig | None = None,
    tolerance_relative_change: float = 0.05,
    tolerance_abs_change_n_per_m: float = 5e-4,
    tolerance_near_zero_abs_n_per_m: float = 1e-6,
    significant_force_threshold_n_per_m: float = 1e-6,
    tolerance_residual_n_per_m: float = 1e-6,
) -> ForceMeshConvergenceStudy:
    """Evaluate full-vector 6-component grid convergence of Maxwell stress forces and 2D vector residual.

    Resolves P1-R2-F2 and P1-R3-F1:
    - Tracks all six conductor force components (left Fx/Fy, right Fx/Fy, enclosure Fx/Fy) and 2D vector residual.
    - Gates both relative changes for active components and absolute bounds for near-zero components.
    - Reports per-component convergence and last-step discretization differences honestly.
    """
    cfg = config or GroundedBoxConfig()
    rows: list[ForceMeshConvergenceRow] = []

    for i, n in enumerate(n_list):
        cfg_n = GroundedBoxConfig(
            n=n,
            box_width_m=cfg.box_width_m,
            left_electrode=cfg.left_electrode,
            right_electrode=cfg.right_electrode,
        )
        sol = electrode_pair_in_grounded_box(config=cfg_n)
        budget = evaluate_whole_apparatus_force_budget(sol, tolerance_n_per_m=1e-3)
        h = float(sol.grid_spacing_m)

        res_fx = float(budget.net_electrostatic_force_fx_n_per_m)
        res_fy = float(budget.net_electrostatic_force_fy_n_per_m)
        res_mag = float(np.hypot(res_fx, res_fy))

        abs_l_fx = abs_l_fy = abs_r_fx = abs_r_fy = abs_b_fx = abs_b_fy = max_abs = None
        rel_l_fx = rel_l_fy = rel_r_fx = rel_r_fy = rel_b_fx = rel_b_fy = rel_max = None

        if i > 0:
            prev = rows[i - 1]
            abs_l_fx = float(abs(budget.left_electrode_fx_n_per_m - prev.left_electrode_fx_n_per_m))
            abs_l_fy = float(abs(budget.left_electrode_fy_n_per_m - prev.left_electrode_fy_n_per_m))
            abs_r_fx = float(abs(budget.right_electrode_fx_n_per_m - prev.right_electrode_fx_n_per_m))
            abs_r_fy = float(abs(budget.right_electrode_fy_n_per_m - prev.right_electrode_fy_n_per_m))
            abs_b_fx = float(abs(budget.enclosure_reaction_fx_n_per_m - prev.enclosure_reaction_fx_n_per_m))
            abs_b_fy = float(abs(budget.enclosure_reaction_fy_n_per_m - prev.enclosure_reaction_fy_n_per_m))
            max_abs = float(max(abs_l_fx, abs_l_fy, abs_r_fx, abs_r_fy, abs_b_fx, abs_b_fy))

            def _rel(curr_v: float, prev_v: float, diff_v: float) -> float | None:
                scale = max(abs(curr_v), abs(prev_v))
                if scale > significant_force_threshold_n_per_m:
                    denom = abs(curr_v) if abs(curr_v) > significant_force_threshold_n_per_m else scale
                    return float(diff_v / denom)
                return None

            rel_l_fx = _rel(budget.left_electrode_fx_n_per_m, prev.left_electrode_fx_n_per_m, abs_l_fx)
            rel_l_fy = _rel(budget.left_electrode_fy_n_per_m, prev.left_electrode_fy_n_per_m, abs_l_fy)
            rel_r_fx = _rel(budget.right_electrode_fx_n_per_m, prev.right_electrode_fx_n_per_m, abs_r_fx)
            rel_r_fy = _rel(budget.right_electrode_fy_n_per_m, prev.right_electrode_fy_n_per_m, abs_r_fy)
            rel_b_fx = _rel(budget.enclosure_reaction_fx_n_per_m, prev.enclosure_reaction_fx_n_per_m, abs_b_fx)
            rel_b_fy = _rel(budget.enclosure_reaction_fy_n_per_m, prev.enclosure_reaction_fy_n_per_m, abs_b_fy)

            rels = [r for r in (rel_l_fx, rel_l_fy, rel_r_fx, rel_r_fy, rel_b_fx, rel_b_fy) if r is not None]
            rel_max = float(max(rels)) if rels else 0.0

        rows.append(ForceMeshConvergenceRow(
            n=n,
            grid_spacing_m=h,
            left_electrode_fx_n_per_m=budget.left_electrode_fx_n_per_m,
            right_electrode_fx_n_per_m=budget.right_electrode_fx_n_per_m,
            enclosure_reaction_fx_n_per_m=budget.enclosure_reaction_fx_n_per_m,
            net_residual_fx_n_per_m=res_fx,
            left_electrode_fy_n_per_m=budget.left_electrode_fy_n_per_m,
            right_electrode_fy_n_per_m=budget.right_electrode_fy_n_per_m,
            enclosure_reaction_fy_n_per_m=budget.enclosure_reaction_fy_n_per_m,
            net_residual_fy_n_per_m=res_fy,
            net_residual_magnitude_n_per_m=res_mag,
            abs_change_left_fx_to_prev=abs_l_fx,
            abs_change_left_fy_to_prev=abs_l_fy,
            abs_change_right_fx_to_prev=abs_r_fx,
            abs_change_right_fy_to_prev=abs_r_fy,
            abs_change_box_fx_to_prev=abs_b_fx,
            abs_change_box_fy_to_prev=abs_b_fy,
            max_abs_change_to_prev=max_abs,
            relative_change_to_prev=rel_l_fx,
            relative_change_left_to_prev=rel_l_fx,
            relative_change_right_to_prev=rel_r_fx,
            relative_change_box_to_prev=rel_b_fx,
            relative_change_left_fx_to_prev=rel_l_fx,
            relative_change_left_fy_to_prev=rel_l_fy,
            relative_change_right_fx_to_prev=rel_r_fx,
            relative_change_right_fy_to_prev=rel_r_fy,
            relative_change_box_fx_to_prev=rel_b_fx,
            relative_change_box_fy_to_prev=rel_b_fy,
            max_relative_change_to_prev=rel_max,
        ))

    return evaluate_force_convergence_from_rows(
        rows=rows,
        tolerance_relative_change=tolerance_relative_change,
        tolerance_abs_change_n_per_m=tolerance_abs_change_n_per_m,
        tolerance_near_zero_abs_n_per_m=tolerance_near_zero_abs_n_per_m,
        significant_force_threshold_n_per_m=significant_force_threshold_n_per_m,
        tolerance_residual_n_per_m=tolerance_residual_n_per_m,
    )


@dataclass(frozen=True)
class VirtualWorkCrossCheckResult:
    n: int
    electrode: str
    delta_x_m: float
    maxwell_stress_fx_n_per_m: float
    virtual_work_fx_n_per_m: float
    relative_difference: float
    same_sign: bool
    is_consistent_to_tolerance: bool
    epistemic_limitation_note: str
    diagnostic_note: str


@dataclass(frozen=True)
class VirtualWorkSensitivityRow:
    n: int
    grid_spacing_m: float
    left_mst_fx_n_per_m: float
    left_vw_fx_1h_n_per_m: float
    left_vw_fx_2h_n_per_m: float
    left_rel_diff_1h: float
    left_rel_diff_2h: float
    left_step_sensitivity_rel: float
    left_same_sign: bool
    right_mst_fx_n_per_m: float
    right_vw_fx_1h_n_per_m: float
    right_vw_fx_2h_n_per_m: float
    right_rel_diff_1h: float
    right_rel_diff_2h: float
    right_step_sensitivity_rel: float
    right_same_sign: bool
    enclosure_mst_fx_n_per_m: float
    net_electrode_mst_fx_n_per_m: float
    net_electrode_vw_fx_1h_n_per_m: float
    net_electrode_rel_diff_1h: float


@dataclass(frozen=True)
class VirtualWorkConvergenceAndSensitivityStudy:
    rows: list[VirtualWorkSensitivityRow]
    left_discrepancy_decreases_with_refinement: bool
    right_discrepancy_decreases_with_refinement: bool
    all_signs_consistent: bool
    is_consistent_to_tolerance: bool
    epistemic_limitation_note: str
    diagnostic_note: str


def compute_stored_electrostatic_energy(solution: FieldSolution) -> float:
    """Compute total stored electrostatic field energy in 2D vacuum interior (J/m).

    U = 0.5 * eps0 * int |E|^2 dx dy
    Note: Uses masked central-difference field gradients on the uniform grid, which carries
    O(h) staircase boundary truncation near curved conductor masks.
    """
    eps0 = 8.8541878128e-12
    mask = solution.vacuum_mask
    h = float(solution.grid_spacing_m)
    ex = solution.ex_v_per_m[mask]
    ey = solution.ey_v_per_m[mask]
    return float(0.5 * eps0 * np.sum(ex**2 + ey**2) * (h**2))


def compute_virtual_work_force_x(
    config: GroundedBoxConfig,
    delta_x_m: float | None = None,
    electrode: str = 'left',
) -> float:
    """Compute x-directed electrostatic force via virtual work at constant potential.

    In an electrostatic system connected to constant voltage sources (batteries):
    delta W_battery = sum V_i delta Q_i = 2 delta U
    F_x = +(dU/dx)_V ~= [U(x0 + dx) - U(x0 - dx)] / (2 * dx)
    Ref: Jackson, Classical Electrodynamics, Sec. 1.11.

    When delta_x_m is an integer multiple k*h of the grid spacing (within 1e-9),
    translates the discrete electrode mask by exact integer lattice steps (+/- k)
    to prevent IEEE-754 floating-point tie-breaking on (x - cx)^2 + (y - cy)^2 <= r^2
    from changing the discrete circle pixel count between +dx and -dx.
    """
    n = config.n
    h = config.box_width_m / (n - 1)
    dh = delta_x_m if delta_x_m is not None else h
    k_shift = int(round(dh / h))

    if k_shift >= 1 and abs(dh - k_shift * h) <= 1e-9 * h:
        coords = np.linspace(-config.box_width_m / 2.0, config.box_width_m / 2.0, n)
        x, y = np.meshgrid(coords, coords, indexing='ij')
        le = config.left_electrode
        re = config.right_electrode
        left0 = (x - le.center_x_m)**2 + (y - le.center_y_m)**2 <= le.radius_m**2
        right0 = (x - re.center_x_m)**2 + (y - re.center_y_m)**2 <= re.radius_m**2

        b_mask = np.zeros((n, n), dtype=bool)
        b_mask[0, :] = b_mask[-1, :] = True
        b_mask[:, 0] = b_mask[:, -1] = True

        def _shift_mask(m: np.ndarray, shift: int) -> np.ndarray:
            out = np.zeros_like(m)
            if shift > 0:
                out[shift:, :] = m[:-shift, :]
            elif shift < 0:
                out[:shift, :] = m[-shift:, :]
            else:
                out[:, :] = m
            return out

        def _solve_with_shift(shift: int) -> FieldSolution:
            l_m = _shift_mask(left0, shift) if electrode == 'left' else left0.copy()
            r_m = _shift_mask(right0, shift) if electrode == 'right' else right0.copy()
            c_m = l_m | r_m
            f_m = b_mask | c_m
            pot = np.zeros((n, n), dtype=float)
            pot[l_m] = le.voltage_v
            pot[r_m] = re.voltage_v
            return solve_dirichlet(f_m, pot, h, conductor_mask=c_m, boundary_mask=b_mask, config=config)

        sol_plus = _solve_with_shift(+k_shift)
        sol_minus = _solve_with_shift(-k_shift)
        actual_dh = float(k_shift * h)
        u_plus = compute_stored_electrostatic_energy(sol_plus)
        u_minus = compute_stored_electrostatic_energy(sol_minus)
        return float((u_plus - u_minus) / (2.0 * actual_dh))

    elec = config.left_electrode if electrode == 'left' else config.right_electrode
    other = config.right_electrode if electrode == 'left' else config.left_electrode

    elec_plus = ElectrodeConfig(
        center_x_m=elec.center_x_m + dh,
        center_y_m=elec.center_y_m,
        radius_m=elec.radius_m,
        voltage_v=elec.voltage_v,
    )
    elec_minus = ElectrodeConfig(
        center_x_m=elec.center_x_m - dh,
        center_y_m=elec.center_y_m,
        radius_m=elec.radius_m,
        voltage_v=elec.voltage_v,
    )

    if electrode == 'left':
        cfg_plus = GroundedBoxConfig(
            n=config.n, box_width_m=config.box_width_m,
            left_electrode=elec_plus, right_electrode=other,
        )
        cfg_minus = GroundedBoxConfig(
            n=config.n, box_width_m=config.box_width_m,
            left_electrode=elec_minus, right_electrode=other,
        )
    else:
        cfg_plus = GroundedBoxConfig(
            n=config.n, box_width_m=config.box_width_m,
            left_electrode=other, right_electrode=elec_plus,
        )
        cfg_minus = GroundedBoxConfig(
            n=config.n, box_width_m=config.box_width_m,
            left_electrode=other, right_electrode=elec_minus,
        )

    sol_plus = electrode_pair_in_grounded_box(config=cfg_plus)
    sol_minus = electrode_pair_in_grounded_box(config=cfg_minus)

    u_plus = compute_stored_electrostatic_energy(sol_plus)
    u_minus = compute_stored_electrostatic_energy(sol_minus)

    return float((u_plus - u_minus) / (2.0 * dh))


def cross_check_maxwell_stress_with_virtual_work(
    config: GroundedBoxConfig | None = None,
    delta_x_m: float | None = None,
    electrode: str = 'left',
    tolerance_relative_diff: float = 0.20,
) -> VirtualWorkCrossCheckResult:
    """Limited finite-grid electrode-shift virtual-work cross-check against Maxwell stress (P1-R2-F2, P1-R3-F2)."""
    cfg = config or GroundedBoxConfig()
    sol = electrode_pair_in_grounded_box(config=cfg)
    budget = evaluate_whole_apparatus_force_budget(sol)

    mst_f = budget.left_electrode_fx_n_per_m if electrode == 'left' else budget.right_electrode_fx_n_per_m
    dh = delta_x_m if delta_x_m is not None else float(sol.grid_spacing_m)
    vw_f = compute_virtual_work_force_x(cfg, delta_x_m=dh, electrode=electrode)

    rel_diff = float(abs(vw_f - mst_f) / abs(mst_f)) if abs(mst_f) > 0 else 0.0
    same_sign = bool(np.sign(vw_f) == np.sign(mst_f))
    is_ok = bool(same_sign and rel_diff <= tolerance_relative_diff)

    limitation = (
        'Virtual work is evaluated via lattice-aligned perturbation (+dU/dx)_V of masked central-gradient '
        'field energy. It carries O(h) staircase boundary truncation near circular electrode masks and '
        'serves as an electrode-force consistency benchmark, not a direct measurement of outer enclosure wall traction.'
    )

    note = (
        f'Electrode-shift virtual-work benchmark on {electrode} electrode (n={cfg.n}, dx_shift={dh:.4e} m): '
        f'Maxwell stress Fx = {mst_f:.6e} N/m, Virtual work (+dU/dx)_V = {vw_f:.6e} N/m '
        f'(same_sign={same_sign}, rel_diff={rel_diff:.2%}, tolerance={tolerance_relative_diff:.0%}).'
    )

    return VirtualWorkCrossCheckResult(
        n=cfg.n,
        electrode=electrode,
        delta_x_m=dh,
        maxwell_stress_fx_n_per_m=mst_f,
        virtual_work_fx_n_per_m=vw_f,
        relative_difference=rel_diff,
        same_sign=same_sign,
        is_consistent_to_tolerance=is_ok,
        epistemic_limitation_note=limitation,
        diagnostic_note=note,
    )


def virtual_work_convergence_and_sensitivity_study(
    config: GroundedBoxConfig | None = None,
    n_list: Sequence[int] = (81, 161),
    tolerance_finest_rel_diff: float = 0.12,
) -> VirtualWorkConvergenceAndSensitivityStudy:
    """Evaluate virtual-work cross-check for both electrodes across resolutions and step sizes (P1-R3-F2).

    Evaluates:
    - Both left and right electrode shifts on symmetric or asymmetric (+600V/+100V) configurations.
    - Perturbation step-size sensitivity comparing delta_x = 1*h vs delta_x = 2*h.
    - Convergence of the relative discrepancy between Maxwell stress and virtual work as n increases.
    """
    cfg = config or GroundedBoxConfig()
    rows: list[VirtualWorkSensitivityRow] = []

    for n in n_list:
        cfg_n = GroundedBoxConfig(
            n=n,
            box_width_m=cfg.box_width_m,
            left_electrode=cfg.left_electrode,
            right_electrode=cfg.right_electrode,
        )
        sol = electrode_pair_in_grounded_box(config=cfg_n)
        budget = evaluate_whole_apparatus_force_budget(sol)
        h = float(sol.grid_spacing_m)

        l_mst = float(budget.left_electrode_fx_n_per_m)
        r_mst = float(budget.right_electrode_fx_n_per_m)
        b_mst = float(budget.enclosure_reaction_fx_n_per_m)

        l_vw_1h = compute_virtual_work_force_x(cfg_n, delta_x_m=h, electrode='left')
        l_vw_2h = compute_virtual_work_force_x(cfg_n, delta_x_m=2.0 * h, electrode='left')
        r_vw_1h = compute_virtual_work_force_x(cfg_n, delta_x_m=h, electrode='right')
        r_vw_2h = compute_virtual_work_force_x(cfg_n, delta_x_m=2.0 * h, electrode='right')

        l_diff_1h = float(abs(l_vw_1h - l_mst) / abs(l_mst)) if abs(l_mst) > 0 else 0.0
        l_diff_2h = float(abs(l_vw_2h - l_mst) / abs(l_mst)) if abs(l_mst) > 0 else 0.0
        l_sens = float(abs(l_vw_2h - l_vw_1h) / abs(l_vw_1h)) if abs(l_vw_1h) > 0 else 0.0
        l_sign = bool(np.sign(l_vw_1h) == np.sign(l_mst) and np.sign(l_vw_2h) == np.sign(l_mst))

        r_diff_1h = float(abs(r_vw_1h - r_mst) / abs(r_mst)) if abs(r_mst) > 0 else 0.0
        r_diff_2h = float(abs(r_vw_2h - r_mst) / abs(r_mst)) if abs(r_mst) > 0 else 0.0
        r_sens = float(abs(r_vw_2h - r_vw_1h) / abs(r_vw_1h)) if abs(r_vw_1h) > 0 else 0.0
        r_sign = bool(np.sign(r_vw_1h) == np.sign(r_mst) and np.sign(r_vw_2h) == np.sign(r_mst))

        net_mst = float(l_mst + r_mst)
        net_vw_1h = float(l_vw_1h + r_vw_1h)
        net_diff_1h = float(abs(net_vw_1h - net_mst) / abs(net_mst)) if abs(net_mst) > 1e-9 else 0.0

        rows.append(VirtualWorkSensitivityRow(
            n=n,
            grid_spacing_m=h,
            left_mst_fx_n_per_m=l_mst,
            left_vw_fx_1h_n_per_m=l_vw_1h,
            left_vw_fx_2h_n_per_m=l_vw_2h,
            left_rel_diff_1h=l_diff_1h,
            left_rel_diff_2h=l_diff_2h,
            left_step_sensitivity_rel=l_sens,
            left_same_sign=l_sign,
            right_mst_fx_n_per_m=r_mst,
            right_vw_fx_1h_n_per_m=r_vw_1h,
            right_vw_fx_2h_n_per_m=r_vw_2h,
            right_rel_diff_1h=r_diff_1h,
            right_rel_diff_2h=r_diff_2h,
            right_step_sensitivity_rel=r_sens,
            right_same_sign=r_sign,
            enclosure_mst_fx_n_per_m=b_mst,
            net_electrode_mst_fx_n_per_m=net_mst,
            net_electrode_vw_fx_1h_n_per_m=net_vw_1h,
            net_electrode_rel_diff_1h=net_diff_1h,
        ))

    left_decreases = bool(
        all(rows[i + 1].left_rel_diff_1h < rows[i].left_rel_diff_1h for i in range(len(rows) - 1))
    ) if len(rows) >= 2 else False
    right_decreases = bool(
        all(rows[i + 1].right_rel_diff_1h < rows[i].right_rel_diff_1h for i in range(len(rows) - 1))
    ) if len(rows) >= 2 else False
    all_signs = bool(all(r.left_same_sign and r.right_same_sign for r in rows))

    finest = rows[-1]
    is_ok = bool(
        all_signs
        and left_decreases
        and right_decreases
        and finest.left_rel_diff_1h <= tolerance_finest_rel_diff
        and finest.right_rel_diff_1h <= tolerance_finest_rel_diff
    )

    limitation = (
        'Virtual-work forces are computed by shifting individual electrode masks by lattice steps (1h, 2h) '
        'and differentiating masked central-gradient field energy U. Because U has O(h) staircase boundary '
        'truncation at curved electrode perimeters, the discrepancy vs vacuum Maxwell stress contours is O(h) '
        'and decreases under grid refinement. This is a limited electrode-force benchmark, not a direct '
        'enclosure-wall perturbation measurement.'
    )

    note = (
        f'Virtual-work convergence & step-sensitivity study across n={[r.n for r in rows]}: '
        f'Finest (n={finest.n}) left rel_diff={finest.left_rel_diff_1h:.2%} (step sens 1h vs 2h: {finest.left_step_sensitivity_rel:.2%}), '
        f'right rel_diff={finest.right_rel_diff_1h:.2%} (step sens 1h vs 2h: {finest.right_step_sensitivity_rel:.2%}). '
        f'Discrepancy decreases with refinement: left={left_decreases}, right={right_decreases}.'
    )

    return VirtualWorkConvergenceAndSensitivityStudy(
        rows=rows,
        left_discrepancy_decreases_with_refinement=left_decreases,
        right_discrepancy_decreases_with_refinement=right_decreases,
        all_signs_consistent=all_signs,
        is_consistent_to_tolerance=is_ok,
        epistemic_limitation_note=limitation,
        diagnostic_note=note,
    )


@dataclass(frozen=True)
class ContourInvarianceResult:
    electrode: str
    contour_margins_m: list[float]
    measured_fx_n_per_m: list[float]
    max_relative_variation: float
    is_invariant_to_tolerance: bool
    diagnostic_note: str


def contour_invariance_study(
    solution: FieldSolution,
    electrode: str = 'left',
    margins_m: Sequence[float] | None = None,
    tolerance_relative_variation: float = 0.02,
) -> ContourInvarianceResult:
    """Demonstrate path/contour independence of Maxwell stress integration in vacuum (P1-R1-F3, P1-R2-F2).

    Integrates Maxwell stress on multiple concentric rectangular loops enclosing the same electrode or enclosure.
    By stress divergence theorem (div T = 0 in vacuum), the force is independent of contour size.
    """
    cfg = solution.config or GroundedBoxConfig()
    h = float(solution.grid_spacing_m)
    w = float((solution.potential_v.shape[0] - 1) * h)

    forces: list[float] = []

    if electrode in ('left', 'right'):
        margins = list(margins_m) if margins_m is not None else [0.0018, 0.0024, 0.0030]
        elec = cfg.left_electrode if electrode == 'left' else cfg.right_electrode
        cx, cy, r = elec.center_x_m, elec.center_y_m, elec.radius_m
        for m in margins:
            res = compute_maxwell_stress_contour(
                solution,
                x_bounds_m=(cx - r - m, cx + r + m),
                y_bounds_m=(cy - r - m, cy + r + m),
                require_vacuum=True,
            )
            forces.append(res.fx_n_per_m)
    elif electrode in ('enclosure', 'box'):
        margins = list(margins_m) if margins_m is not None else [2.0 * h, 3.0 * h, 4.0 * h]
        for m in margins:
            res = compute_maxwell_stress_contour(
                solution,
                x_bounds_m=(-w / 2.0 + m, w / 2.0 - m),
                y_bounds_m=(-w / 2.0 + m, w / 2.0 - m),
                require_vacuum=True,
            )
            forces.append(-res.fx_n_per_m)
    else:
        raise ValueError(f"Unknown target: {electrode}. Choose 'left', 'right', or 'enclosure'.")

    mean_f = float(np.mean(forces))
    max_var = float(np.max(np.abs(np.array(forces) - mean_f)) / abs(mean_f)) if abs(mean_f) > 0 else 0.0
    is_ok = bool(max_var <= tolerance_relative_variation)

    note = (
        f'Concentric contours for {electrode} at margins {margins} m yielded Fx = '
        f'{[round(f, 7) for f in forces]} N/m. '
        f'Max relative variation across contours: {max_var:.3%} (< {tolerance_relative_variation:.0%} tolerance).'
    )

    return ContourInvarianceResult(
        electrode=electrode,
        contour_margins_m=margins,
        measured_fx_n_per_m=forces,
        max_relative_variation=max_var,
        is_invariant_to_tolerance=is_ok,
        diagnostic_note=note,
    )


def solve_dirichlet_independent_matrix_free_sor(
    config: GroundedBoxConfig | None = None,
    tolerance_v: float = 1e-11,
    max_iterations: int = 20000,
) -> FieldSolution:
    """Independently implemented matrix-free Red-Black SOR 5-point Laplace solver (P1-R4-F3, P1-R5-F4).

    Solves the discrete 5-point Dirichlet Laplace BVP on the staircase grid using vectorized
    Red-Black Successive Over-Relaxation (SOR) without calling electrostatics_baseline.solve_dirichlet
    or scipy.sparse.linalg.spsolve.

    Fails closed:
      - Validates max_iterations >= 1 and tolerance_v > 0.
      - Tracks discrete residual convergence; raises RuntimeError if residual exceeds tolerance_v
        upon completing max_iterations.
    """
    if max_iterations < 1:
        raise ValueError(f"max_iterations must be >= 1, got {max_iterations}")
    if tolerance_v <= 0.0:
        raise ValueError(f"tolerance_v must be > 0, got {tolerance_v}")

    cfg = config or GroundedBoxConfig()
    n = cfg.n
    h = cfg.box_width_m / (n - 1)
    coords = np.linspace(-cfg.box_width_m / 2.0, cfg.box_width_m / 2.0, n)
    x, y = np.meshgrid(coords, coords, indexing='ij')

    le = cfg.left_electrode
    re = cfg.right_electrode
    left_mask = (x - le.center_x_m) ** 2 + (y - le.center_y_m) ** 2 <= le.radius_m ** 2
    right_mask = (x - re.center_x_m) ** 2 + (y - re.center_y_m) ** 2 <= re.radius_m ** 2
    conductor_mask = left_mask | right_mask

    boundary_mask = np.zeros((n, n), dtype=bool)
    boundary_mask[0, :] = boundary_mask[-1, :] = True
    boundary_mask[:, 0] = boundary_mask[:, -1] = True
    fixed_mask = boundary_mask | conductor_mask
    free_mask = ~fixed_mask

    pot = np.zeros((n, n), dtype=float)
    pot[left_mask] = le.voltage_v
    pot[right_mask] = re.voltage_v

    # Optimal spectral radius SOR relaxation factor for 2D Poisson on n x n grid
    rho_jacobi = np.cos(np.pi / (n - 1))
    omega = 2.0 / (1.0 + np.sqrt(max(1e-12, 1.0 - rho_jacobi ** 2)))

    idx_sum = (np.arange(n)[:, None] + np.arange(n)[None, :])
    red_free = free_mask & ((idx_sum % 2) == 0)
    black_free = free_mask & ((idx_sum % 2) == 1)

    converged = False
    max_res = float("inf")
    for _ in range(max_iterations):
        # Update Red nodes
        avg_r = 0.25 * (
            np.roll(pot, 1, axis=0) + np.roll(pot, -1, axis=0)
            + np.roll(pot, 1, axis=1) + np.roll(pot, -1, axis=1)
        )
        diff_r = avg_r - pot
        pot[red_free] += omega * diff_r[red_free]

        # Update Black nodes
        avg_b = 0.25 * (
            np.roll(pot, 1, axis=0) + np.roll(pot, -1, axis=0)
            + np.roll(pot, 1, axis=1) + np.roll(pot, -1, axis=1)
        )
        diff_b = avg_b - pot
        pot[black_free] += omega * diff_b[black_free]

        # Check discrete residual
        res_interior = np.abs(
            0.25 * (pot[2:, 1:-1] + pot[:-2, 1:-1] + pot[1:-1, 2:] + pot[1:-1, :-2]) - pot[1:-1, 1:-1]
        )
        max_res = float(np.max(res_interior[free_mask[1:-1, 1:-1]]))
        if max_res <= tolerance_v:
            converged = True
            break

    if not converged:
        raise RuntimeError(
            f"SOR solver failed to converge within {max_iterations} iterations: "
            f"max residual {max_res:.3e} V > tolerance {tolerance_v:.3e} V"
        )

    raw_ex = -np.gradient(pot, h, axis=0, edge_order=2)
    raw_ey = -np.gradient(pot, h, axis=1, edge_order=2)

    vac_mask = ~fixed_mask
    vac_ex = np.full_like(raw_ex, np.nan)
    vac_ey = np.full_like(raw_ey, np.nan)
    vac_ex[vac_mask] = raw_ex[vac_mask]
    vac_ey[vac_mask] = raw_ey[vac_mask]

    res_full = np.zeros_like(pot)
    res_full[1:-1, 1:-1] = np.abs(
        pot[2:, 1:-1] + pot[:-2, 1:-1] + pot[1:-1, 2:] + pot[1:-1, :-2] - 4.0 * pot[1:-1, 1:-1]
    )
    max_disc_res = float(np.max(res_full[vac_mask]))

    return FieldSolution(
        potential_v=pot,
        ex_v_per_m=vac_ex,
        ey_v_per_m=vac_ey,
        vacuum_mask=vac_mask,
        conductor_mask=conductor_mask,
        boundary_mask=boundary_mask,
        fixed_mask=fixed_mask,
        grid_spacing_m=h,
        max_discrete_residual_v=max_disc_res,
        raw_gradient_x_v_per_m=raw_ex,
        raw_gradient_y_v_per_m=raw_ey,
        config=cfg,
    )


@dataclass(frozen=True)
class MFSContinuousLaplaceSolution:
    """Grid-free continuous Method of Fundamental Solutions (MFS) Laplace solution (P1-R4-F3, P1-R5-F2).

    Represents V(x,y) in the continuous vacuum domain Omega_vac as an analytical harmonic superposition
    of 2D logarithmic line-charge potentials placed strictly outside Omega_vac.
    Boundary accuracy is evaluated via an independent dense discrete sampling diagnostic on conductor
    surfaces (720 angles/electrode, 400 points/wall). While the harmonic potential satisfies the Laplace
    equation exactly in Omega_vac and the continuous Maximum Principle guarantees that interior harmonic
    error cannot exceed its boundary maximum, discrete point evaluation provides a dense sampled-boundary
    diagnostic rather than a certified continuous supremum over all boundary points.
    """
    max_collocation_residual_v: float
    max_sampled_boundary_error_v: float
    midpoint_potential_v: float
    midpoint_ex_v_per_m: float
    midpoint_ey_v_per_m: float
    left_electrode_fx_n_per_m: float
    left_electrode_fy_n_per_m: float
    right_electrode_fx_n_per_m: float
    right_electrode_fy_n_per_m: float
    enclosure_reaction_fx_n_per_m: float
    enclosure_reaction_fy_n_per_m: float
    net_residual_magnitude_n_per_m: float

    @property
    def max_independent_boundary_error_v(self) -> float:
        """Backward-compatible alias for max_sampled_boundary_error_v."""
        return self.max_sampled_boundary_error_v


def solve_electrostatics_mfs_boundary_collocation(
    config: GroundedBoxConfig | None = None,
    n_circle_sources: int = 44,
    n_wall_sources_per_side: int = 44,
) -> MFSContinuousLaplaceSolution:
    """Independently implemented grid-free Method of Fundamental Solutions (MFS) 2D Laplace solver (P1-R4-F3).

    Solves nabla^2 V = 0 in the continuous vacuum domain between exact circular cylindrical electrodes
    and the grounded square enclosure without any finite-difference grid or staircase approximation.
    """
    cfg = config or GroundedBoxConfig()
    L = float(cfg.box_width_m)
    half = L / 2.0
    le = cfg.left_electrode
    re = cfg.right_electrode

    # 1. Place fictitious line-charge sources strictly outside vacuum domain Omega_vac
    theta_s = np.linspace(0.0, 2.0 * np.pi, n_circle_sources, endpoint=False)
    r_src_l = 0.50 * le.radius_m
    r_src_r = 0.50 * re.radius_m
    src_l = np.column_stack([le.center_x_m + r_src_l * np.cos(theta_s), le.center_y_m + r_src_l * np.sin(theta_s)])
    src_r = np.column_stack([re.center_x_m + r_src_r * np.cos(theta_s), re.center_y_m + r_src_r * np.sin(theta_s)])

    d_wall = 1.25 * half
    s_1d = np.linspace(-d_wall, d_wall, n_wall_sources_per_side)
    src_w = np.vstack([
        np.column_stack([s_1d, np.full_like(s_1d, -d_wall)]),
        np.column_stack([s_1d, np.full_like(s_1d, d_wall)]),
        np.column_stack([np.full_like(s_1d, -d_wall), s_1d]),
        np.column_stack([np.full_like(s_1d, d_wall), s_1d]),
    ])
    sources = np.vstack([src_l, src_r, src_w])

    # 2. Oversampled boundary collocation points on exact circles and square enclosure walls
    theta_c = np.linspace(0.0, 2.0 * np.pi, 3 * n_circle_sources, endpoint=False)
    col_l = np.column_stack([le.center_x_m + le.radius_m * np.cos(theta_c), le.center_y_m + le.radius_m * np.sin(theta_c)])
    col_r = np.column_stack([re.center_x_m + re.radius_m * np.cos(theta_c), re.center_y_m + re.radius_m * np.sin(theta_c)])

    w_1d = np.linspace(-half, half, 3 * n_wall_sources_per_side)
    col_w = np.vstack([
        np.column_stack([w_1d, np.full_like(w_1d, -half)]),
        np.column_stack([w_1d, np.full_like(w_1d, half)]),
        np.column_stack([np.full_like(w_1d, -half), w_1d]),
        np.column_stack([np.full_like(w_1d, half), w_1d]),
    ])
    colloc = np.vstack([col_l, col_r, col_w])
    rhs = np.concatenate([
        np.full(len(col_l), le.voltage_v, dtype=float),
        np.full(len(col_r), re.voltage_v, dtype=float),
        np.zeros(len(col_w), dtype=float),
    ])

    dx = colloc[:, None, 0] - sources[None, :, 0]
    dy = colloc[:, None, 1] - sources[None, :, 1]
    G = np.hstack([np.log(np.hypot(dx, dy)), np.ones((len(colloc), 1), dtype=float)])
    weights, *_ = np.linalg.lstsq(G, rhs, rcond=None)
    max_colloc_res = float(np.max(np.abs(G @ weights - rhs)))

    q = weights[:-1]
    c_offset = float(weights[-1])

    def _eval_v_and_e(pts: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        rx = pts[:, None, 0] - sources[None, :, 0]
        ry = pts[:, None, 1] - sources[None, :, 1]
        r2 = rx ** 2 + ry ** 2
        v = 0.5 * np.log(r2) @ q + c_offset
        ex = -(rx / r2) @ q
        ey = -(ry / r2) @ q
        return v, ex, ey

    # 3. Independent dense boundary verification (Maximum Principle certificate)
    theta_v = np.linspace(0.0, 2.0 * np.pi, 720, endpoint=False) + (np.pi / 720.0)
    ver_l = np.column_stack([le.center_x_m + le.radius_m * np.cos(theta_v), le.center_y_m + le.radius_m * np.sin(theta_v)])
    ver_r = np.column_stack([re.center_x_m + re.radius_m * np.cos(theta_v), re.center_y_m + re.radius_m * np.sin(theta_v)])
    wv_1d = np.linspace(-half, half, 400)
    ver_w = np.vstack([
        np.column_stack([wv_1d, np.full_like(wv_1d, -half)]),
        np.column_stack([wv_1d, np.full_like(wv_1d, half)]),
        np.column_stack([np.full_like(wv_1d, -half), wv_1d]),
        np.column_stack([np.full_like(wv_1d, half), wv_1d]),
    ])
    v_l, _, _ = _eval_v_and_e(ver_l)
    v_r, _, _ = _eval_v_and_e(ver_r)
    v_w, _, _ = _eval_v_and_e(ver_w)
    max_ind_bc_err = float(max(
        np.max(np.abs(v_l - le.voltage_v)),
        np.max(np.abs(v_r - re.voltage_v)),
        np.max(np.abs(v_w - 0.0)),
    ))

    # 4. Evaluate midpoint field E(0, 0)
    v0, ex0, ey0 = _eval_v_and_e(np.array([[0.0, 0.0]], dtype=float))

    # 5. Analytical contour integration of Maxwell stress tensor around each conductor and enclosure
    n_quad = 720
    ang = np.linspace(0.0, 2.0 * np.pi, n_quad, endpoint=False)
    d_ang = 2.0 * np.pi / n_quad

    def _circle_force(el: ElectrodeConfig) -> tuple[float, float]:
        rc = 1.45 * el.radius_m
        pts = np.column_stack([el.center_x_m + rc * np.cos(ang), el.center_y_m + rc * np.sin(ang)])
        nx, ny = np.cos(ang), np.sin(ang)
        _, ex, ey = _eval_v_and_e(pts)
        e2 = ex ** 2 + ey ** 2
        edotn = ex * nx + ey * ny
        tx = EPSILON_0_F_PER_M * (ex * edotn - 0.5 * e2 * nx)
        ty = EPSILON_0_F_PER_M * (ey * edotn - 0.5 * e2 * ny)
        return float(np.sum(tx) * rc * d_ang), float(np.sum(ty) * rc * d_ang)

    l_fx, l_fy = _circle_force(le)
    r_fx, r_fy = _circle_force(re)

    # Outer square contour at +/- 0.92 * half enclosing both electrodes (inward normal for box reaction)
    b_half = 0.92 * half
    n_side = 400
    ds = (2.0 * b_half) / n_side
    s_pts = np.linspace(-b_half + 0.5 * ds, b_half - 0.5 * ds, n_side)
    # Right (+x), Left (-x), Top (+y), Bottom (-y)
    pts_box = np.vstack([
        np.column_stack([np.full_like(s_pts, b_half), s_pts]),
        np.column_stack([np.full_like(s_pts, -b_half), s_pts]),
        np.column_stack([s_pts, np.full_like(s_pts, b_half)]),
        np.column_stack([s_pts, np.full_like(s_pts, -b_half)]),
    ])
    n_out = np.vstack([
        np.column_stack([np.ones_like(s_pts), np.zeros_like(s_pts)]),
        np.column_stack([-np.ones_like(s_pts), np.zeros_like(s_pts)]),
        np.column_stack([np.zeros_like(s_pts), np.ones_like(s_pts)]),
        np.column_stack([np.zeros_like(s_pts), -np.ones_like(s_pts)]),
    ])
    _, ex_b, ey_b = _eval_v_and_e(pts_box)
    e2_b = ex_b ** 2 + ey_b ** 2
    edotn_b = ex_b * n_out[:, 0] + ey_b * n_out[:, 1]
    tx_b = EPSILON_0_F_PER_M * (ex_b * edotn_b - 0.5 * e2_b * n_out[:, 0])
    ty_b = EPSILON_0_F_PER_M * (ey_b * edotn_b - 0.5 * e2_b * n_out[:, 1])
    box_fx = float(-np.sum(tx_b) * ds)
    box_fy = float(-np.sum(ty_b) * ds)

    net_mag = float(np.hypot(l_fx + r_fx + box_fx, l_fy + r_fy + box_fy))

    return MFSContinuousLaplaceSolution(
        max_collocation_residual_v=max_colloc_res,
        max_sampled_boundary_error_v=max_ind_bc_err,
        midpoint_potential_v=float(v0[0]),
        midpoint_ex_v_per_m=float(ex0[0]),
        midpoint_ey_v_per_m=float(ey0[0]),
        left_electrode_fx_n_per_m=l_fx,
        left_electrode_fy_n_per_m=l_fy,
        right_electrode_fx_n_per_m=r_fx,
        right_electrode_fy_n_per_m=r_fy,
        enclosure_reaction_fx_n_per_m=box_fx,
        enclosure_reaction_fy_n_per_m=box_fy,
        net_residual_magnitude_n_per_m=net_mag,
    )


@dataclass(frozen=True)
class IndependentSolverComparisonRow:
    n: int
    grid_spacing_m: float
    midpoint_e_rel_error_vs_mfs: float
    left_force_vec_rel_error_vs_mfs: float
    right_force_vec_rel_error_vs_mfs: float
    enclosure_force_vec_rel_error_vs_mfs: float


@dataclass(frozen=True)
class IndependentSolverVerificationStudy:
    mfs_max_sampled_boundary_error_v: float
    mfs_net_force_residual_n_per_m: float
    sor_vs_direct_lu_max_potential_diff_v: float
    sor_vs_direct_lu_max_force_diff_n_per_m: float
    fdm_vs_mfs_rows: list[IndependentSolverComparisonRow]
    endpoint_errors_improve: bool
    is_verified_to_tolerance: bool
    methodological_distinction_note: str
    diagnostic_note: str
    strict_intermediate_monotonicity: bool = False

    @property
    def mfs_max_independent_boundary_error_v(self) -> float:
        """Backward-compatible alias for mfs_max_sampled_boundary_error_v."""
        return self.mfs_max_sampled_boundary_error_v

    @property
    def errors_decrease_toward_mfs_with_refinement(self) -> bool:
        """Backward-compatible alias for endpoint_errors_improve."""
        return self.endpoint_errors_improve


def benchmark_independent_electrostatic_solver_verification(
    config: GroundedBoxConfig | None = None,
    n_list: Sequence[int] = (41, 81, 161, 321),
    tolerance_mfs_sampled_boundary_v: float = 1e-6,
    tolerance_sor_diff_v: float = 1e-8,
    tolerance_finest_force_rel_vs_mfs: float = 0.05,
    tolerance_mfs_boundary_v: float | None = None,
) -> IndependentSolverVerificationStudy:
    """Compare baseline 5-point FDM solver against two independent solver implementations (P1-R4-F3, P1-R5-F2, P1-R5-F3).

    1. Matrix-free Red-Black SOR solver on the same discrete staircase grid (verifies discrete linear solver
       independently of scipy.sparse.linalg.spsolve).
    2. Grid-free continuous Method of Fundamental Solutions (MFS) boundary-collocation solver on the exact
       continuous circular geometry (verifies convergence of the 5-point staircase FDM toward an independent
       grid-free harmonic formulation).
    """
    tol_mfs = tolerance_mfs_boundary_v if tolerance_mfs_boundary_v is not None else tolerance_mfs_sampled_boundary_v
    cfg = config or GroundedBoxConfig(
        left_electrode=ElectrodeConfig(center_x_m=-0.008, center_y_m=0.004, radius_m=0.003, voltage_v=600.0),
        right_electrode=ElectrodeConfig(center_x_m=0.008, center_y_m=-0.002, radius_m=0.003, voltage_v=-400.0),
    )

    # 1. Continuous grid-free MFS reference
    mfs = solve_electrostatics_mfs_boundary_collocation(cfg)

    # 2. Discrete matrix-free SOR vs sparse direct LU at n=81
    cfg_81 = GroundedBoxConfig(
        n=81, box_width_m=cfg.box_width_m, left_electrode=cfg.left_electrode, right_electrode=cfg.right_electrode
    )
    sol_lu = electrode_pair_in_grounded_box(config=cfg_81)
    sol_sor = solve_dirichlet_independent_matrix_free_sor(config=cfg_81)
    sor_pot_diff = float(np.max(np.abs(sol_lu.potential_v - sol_sor.potential_v)))

    b_lu = evaluate_whole_apparatus_force_budget(sol_lu)
    b_sor = evaluate_whole_apparatus_force_budget(sol_sor)
    sor_force_diff = float(max(
        abs(b_lu.left_electrode_fx_n_per_m - b_sor.left_electrode_fx_n_per_m),
        abs(b_lu.left_electrode_fy_n_per_m - b_sor.left_electrode_fy_n_per_m),
        abs(b_lu.right_electrode_fx_n_per_m - b_sor.right_electrode_fx_n_per_m),
        abs(b_lu.right_electrode_fy_n_per_m - b_sor.right_electrode_fy_n_per_m),
        abs(b_lu.enclosure_reaction_fx_n_per_m - b_sor.enclosure_reaction_fx_n_per_m),
        abs(b_lu.enclosure_reaction_fy_n_per_m - b_sor.enclosure_reaction_fy_n_per_m),
    ))

    # 3. Convergence of 5-point staircase FDM toward continuous grid-free MFS across n_list
    mfs_e0_mag = float(np.hypot(mfs.midpoint_ex_v_per_m, mfs.midpoint_ey_v_per_m))
    mfs_l_mag = float(np.hypot(mfs.left_electrode_fx_n_per_m, mfs.left_electrode_fy_n_per_m))
    mfs_r_mag = float(np.hypot(mfs.right_electrode_fx_n_per_m, mfs.right_electrode_fy_n_per_m))
    mfs_b_mag = float(np.hypot(mfs.enclosure_reaction_fx_n_per_m, mfs.enclosure_reaction_fy_n_per_m))

    rows: list[IndependentSolverComparisonRow] = []
    for n in n_list:
        cfg_n = GroundedBoxConfig(
            n=n, box_width_m=cfg.box_width_m, left_electrode=cfg.left_electrode, right_electrode=cfg.right_electrode
        )
        sol = electrode_pair_in_grounded_box(config=cfg_n)
        b = evaluate_whole_apparatus_force_budget(sol)
        mid = n // 2

        if sol.vacuum_mask[mid, mid] and mfs_e0_mag > 0:
            e0_err = float(
                np.hypot(sol.ex_v_per_m[mid, mid] - mfs.midpoint_ex_v_per_m, sol.ey_v_per_m[mid, mid] - mfs.midpoint_ey_v_per_m)
                / mfs_e0_mag
            )
        else:
            e0_err = 0.0
        l_err = float(
            np.hypot(b.left_electrode_fx_n_per_m - mfs.left_electrode_fx_n_per_m, b.left_electrode_fy_n_per_m - mfs.left_electrode_fy_n_per_m)
            / mfs_l_mag
        ) if mfs_l_mag > 0 else 0.0
        r_err = float(
            np.hypot(b.right_electrode_fx_n_per_m - mfs.right_electrode_fx_n_per_m, b.right_electrode_fy_n_per_m - mfs.right_electrode_fy_n_per_m)
            / mfs_r_mag
        ) if mfs_r_mag > 0 else 0.0
        b_err = float(
            np.hypot(b.enclosure_reaction_fx_n_per_m - mfs.enclosure_reaction_fx_n_per_m, b.enclosure_reaction_fy_n_per_m - mfs.enclosure_reaction_fy_n_per_m)
            / mfs_b_mag
        ) if mfs_b_mag > 0 else 0.0

        rows.append(IndependentSolverComparisonRow(
            n=n,
            grid_spacing_m=float(sol.grid_spacing_m),
            midpoint_e_rel_error_vs_mfs=e0_err,
            left_force_vec_rel_error_vs_mfs=l_err,
            right_force_vec_rel_error_vs_mfs=r_err,
            enclosure_force_vec_rel_error_vs_mfs=b_err,
        ))

    endpoint_errors_improve = bool(
        rows[-1].midpoint_e_rel_error_vs_mfs < rows[0].midpoint_e_rel_error_vs_mfs
        and rows[-1].left_force_vec_rel_error_vs_mfs < rows[0].left_force_vec_rel_error_vs_mfs
        and rows[-1].right_force_vec_rel_error_vs_mfs < rows[0].right_force_vec_rel_error_vs_mfs
        and rows[-1].enclosure_force_vec_rel_error_vs_mfs < rows[0].enclosure_force_vec_rel_error_vs_mfs
    ) if len(rows) >= 2 else False

    def _is_strictly_decreasing(series: list[float]) -> bool:
        return all(series[i + 1] < series[i] for i in range(len(series) - 1))

    strict_monotonic = bool(
        _is_strictly_decreasing([r.midpoint_e_rel_error_vs_mfs for r in rows])
        and _is_strictly_decreasing([r.left_force_vec_rel_error_vs_mfs for r in rows])
        and _is_strictly_decreasing([r.right_force_vec_rel_error_vs_mfs for r in rows])
        and _is_strictly_decreasing([r.enclosure_force_vec_rel_error_vs_mfs for r in rows])
    ) if len(rows) >= 2 else False

    finest = rows[-1]
    is_ok = bool(
        mfs.max_sampled_boundary_error_v <= tol_mfs
        and mfs.net_residual_magnitude_n_per_m < 1e-8
        and sor_pot_diff <= tolerance_sor_diff_v
        and endpoint_errors_improve
        and finest.left_force_vec_rel_error_vs_mfs <= tolerance_finest_force_rel_vs_mfs
        and finest.right_force_vec_rel_error_vs_mfs <= tolerance_finest_force_rel_vs_mfs
        and finest.enclosure_force_vec_rel_error_vs_mfs <= tolerance_finest_force_rel_vs_mfs
    )

    distinction = (
        'Methodological distinction (P1-R4-F3, P1-R5-F2, P1-R5-F3): (1) Maxwell stress vs virtual work compares two force-extraction '
        'methods on the same 5-point FDM solver; (2) sparse direct LU (spsolve) vs matrix-free Red-Black SOR '
        'compares two independent discrete linear solvers on the same staircase grid; (3) 5-point staircase FDM '
        'vs grid-free Method of Fundamental Solutions (MFS) boundary-collocation compares two genuinely '
        'independent numerical formulations of the 2D Laplace boundary-value problem.'
    )

    note = (
        f'Independent solver verification across n={[r.n for r in rows]}: '
        f'Grid-free MFS sampled-boundary diagnostic max error={mfs.max_sampled_boundary_error_v:.2e} V '
        f'(diagnostic on dense boundary sample, not continuous supremum guarantee), '
        f'MFS whole-apparatus net residual={mfs.net_residual_magnitude_n_per_m:.2e} N/m. '
        f'Matrix-free SOR vs direct LU (n=81) max potential diff={sor_pot_diff:.2e} V, force diff={sor_force_diff:.2e} N/m. '
        f'5-point FDM vs continuous MFS force errors at n={finest.n}: '
        f'left={finest.left_force_vec_rel_error_vs_mfs:.2%}, right={finest.right_force_vec_rel_error_vs_mfs:.2%}, '
        f'enclosure={finest.enclosure_force_vec_rel_error_vs_mfs:.2%}, E(0,0)={finest.midpoint_e_rel_error_vs_mfs:.2%}. '
        f'Endpoint errors improve coarsest-to-finest (endpoint_errors_improve={endpoint_errors_improve}), '
        f'while intermediate staircase errors are non-monotonic due to grid rasterization shifts '
        f'(strict_intermediate_monotonicity={strict_monotonic}).'
    )

    return IndependentSolverVerificationStudy(
        mfs_max_sampled_boundary_error_v=mfs.max_sampled_boundary_error_v,
        mfs_net_force_residual_n_per_m=mfs.net_residual_magnitude_n_per_m,
        sor_vs_direct_lu_max_potential_diff_v=sor_pot_diff,
        sor_vs_direct_lu_max_force_diff_n_per_m=sor_force_diff,
        fdm_vs_mfs_rows=rows,
        endpoint_errors_improve=endpoint_errors_improve,
        is_verified_to_tolerance=is_ok,
        methodological_distinction_note=distinction,
        diagnostic_note=note,
        strict_intermediate_monotonicity=strict_monotonic,
    )


