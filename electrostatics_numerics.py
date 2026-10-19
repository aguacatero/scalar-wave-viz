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
    tolerance_n_per_m: float = 1e-6,
) -> WholeApparatusForceBudget:
    """Evaluate closed Maxwell stress contours for both electrodes and the grounded enclosure."""
    cfg = solution.config or GroundedBoxConfig()
    le = cfg.left_electrode
    re = cfg.right_electrode
    w = cfg.box_width_m

    # Left electrode contour: tight box around left cylinder in vacuum
    # Cylinder radius is r, center is (cx, cy)
    # Put contour at cx +/- (r + margin), cy +/- (r + margin)
    # Ensure it stays in vacuum between electrodes and outer box
    sep = re.center_x_m - le.center_x_m
    mid_x = (le.center_x_m + re.center_x_m) / 2.0
    margin_x = min(abs(mid_x - le.center_x_m) * 0.4, 0.003)
    margin_y = 0.003

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
    h = solution.grid_spacing_m
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
    # Note that c_enclosure_inner by divergence theorem equals F_left + F_right + numerical residual
    net_fx = c_left.fx_n_per_m + c_right.fx_n_per_m + f_enc_x
    net_fy = c_left.fy_n_per_m + c_right.fy_n_per_m + f_enc_y

    is_balanced = bool(np.hypot(net_fx, net_fy) < tolerance_n_per_m)

    note = (
        'The 2D modeled conductors (left electrode, right electrode, grounded enclosure) '
        'form a closed electro-mechanical system. The electrostatic attraction between electrodes '
        'is transferred via field lines to each other and to the grounded shielding enclosure. '
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
