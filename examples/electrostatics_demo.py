"""Generate evidence-labeled conventional-electrostatics figure and paired JSON manifest.

From repository root: python examples/electrostatics_demo.py
"""
from __future__ import annotations

import json
from pathlib import Path
import platform
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import scipy

from electrostatics_baseline import (
    FieldSolution,
    GroundedBoxConfig,
    PlateBenchmark,
    coaxial_cylinder_benchmark,
    electrode_pair_in_grounded_box,
    electrode_pair_mesh_study,
    evaluate_conductor_surface_interface,
    parallel_plate_benchmark,
    verify_plate_force_virtual_work,
)


def get_git_commit() -> str:
    """Retrieve git HEAD commit SHA if available."""
    try:
        sha = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'],
            cwd=str(Path(__file__).resolve().parents[1]),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return sha
    except Exception:
        return 'unknown'


def display_field_data(result: FieldSolution):
    """Mask conductor interior and boundary cells; return normalized unit vector field in vacuum.

    Gradient samples on/inside fixed conducting cells are not physical interior fields.
    Vector lengths are normalized to unit vectors so arrow length does not mislead;
    the color scale displays field magnitude.
    """
    hidden = ~result.vacuum_mask
    magnitude = result.vacuum_e_magnitude_v_per_m
    mag_masked = np.ma.array(np.nan_to_num(magnitude, nan=0.0), mask=hidden)

    ux = np.divide(
        result.ex_v_per_m,
        magnitude,
        out=np.zeros_like(magnitude),
        where=(magnitude > 0) & result.vacuum_mask,
    )
    uy = np.divide(
        result.ey_v_per_m,
        magnitude,
        out=np.zeros_like(magnitude),
        where=(magnitude > 0) & result.vacuum_mask,
    )
    ux_masked = np.ma.array(ux, mask=hidden | np.isnan(magnitude) | (magnitude == 0))
    uy_masked = np.ma.array(uy, mask=hidden | np.isnan(magnitude) | (magnitude == 0))
    return mag_masked, ux_masked, uy_masked


def generate_manifest(
    result_2d: FieldSolution,
    plate_result: PlateBenchmark,
    study_results: list,
    coax_benchmarks: list,
    output_png: str,
    config_2d: GroundedBoxConfig | None = None,
) -> dict:
    """Build machine-readable run manifest with provenance, parameters, and validation status."""
    git_sha = get_git_commit()
    vw_check = verify_plate_force_virtual_work(
        plate_result.voltage_v, plate_result.gap_m, plate_result.area_m2
    )

    # Resolve configuration dynamically from result or passed config (R2-F3)
    active_config = config_2d or result_2d.config or GroundedBoxConfig()

    study_table = [
        {
            'n': r.n,
            'grid_spacing_m': r.grid_spacing_m,
            'probe_xy_m': [r.probe_x_m, r.probe_y_m],
            'probe_ex_v_per_m': r.probe_ex_v_per_m,
            'max_vacuum_e_v_per_m': r.max_vacuum_e_v_per_m,
            'max_conductor_raw_gradient_v_per_m': r.max_conductor_raw_gradient_v_per_m,
            'max_discrete_residual_v': r.max_discrete_residual_v,
            'potential_antisymmetry_error_v': r.potential_antisymmetry_error_v,
        }
        for r in study_results
    ]

    coax_table = [
        {
            'n': c.n,
            'grid_spacing_m': c.grid_spacing_m,
            'probe_r_m': c.probe_r_m,
            'analytic_potential_v': c.analytic_potential_v,
            'numerical_potential_v': c.numerical_potential_v,
            'potential_error_v': c.potential_error_v,
            'analytic_field_er_v_per_m': c.analytic_field_er_v_per_m,
            'numerical_field_ex_v_per_m': c.numerical_field_ex_v_per_m,
            'field_error_v_per_m': c.field_error_v_per_m,
        }
        for c in coax_benchmarks
    ]

    manifest = {
        'schema_version': '1.0.0',
        'artifact_file': output_png,
        'git_commit': git_sha,
        'environment': {
            'python_version': platform.python_version(),
            'platform': platform.platform(),
            'packages': {
                'numpy': np.__version__,
                'scipy': scipy.__version__,
                'matplotlib': matplotlib.__version__,
            },
        },
        'cases': {
            'case_1_grounded_box_2d': {
                'description': '2D Dirichlet Laplace potential for cylindrical electrode cross-sections in grounded square box',
                'validation_status': 'ILLUSTRATIVE / NON-CONVERGED',
                'epistemic_warning': (
                    'Peak vacuum |E| on staircase conductor boundaries varies with grid resolution '
                    'and is NOT converged. Probe field away from boundaries converges smoothly. '
                    'Conductor interior field is masked (E=0). Not an isolated thruster. Not patent geometry.'
                ),
                'geometry': {
                    'enclosure_width_m': float(active_config.box_width_m),
                    'boundary_condition': 'Grounded outer enclosure (0 V Dirichlet)',
                    'left_electrode': {
                        'center_x_m': float(active_config.left_electrode.center_x_m),
                        'center_y_m': float(active_config.left_electrode.center_y_m),
                        'radius_m': float(active_config.left_electrode.radius_m),
                        'voltage_v': float(active_config.left_electrode.voltage_v),
                    },
                    'right_electrode': {
                        'center_x_m': float(active_config.right_electrode.center_x_m),
                        'center_y_m': float(active_config.right_electrode.center_y_m),
                        'radius_m': float(active_config.right_electrode.radius_m),
                        'voltage_v': float(active_config.right_electrode.voltage_v),
                    },
                },
                'discretization': {
                    'grid_dimension': int(result_2d.potential_v.shape[0]),
                    'grid_spacing_m': float(result_2d.grid_spacing_m),
                    'stencil': '5-point Laplace finite-difference',
                    'max_discrete_residual_v': float(result_2d.max_discrete_residual_v),
                },
                'mesh_study_probe_midpoint': study_table,
                'coaxial_analytic_benchmark': coax_table,
            },
            'case_2_parallel_plate_1d': {
                'description': '1D ideal parallel-plate capacitor analytic reference (neglecting fringing)',
                'validation_status': 'ANALYTIC BENCHMARK',
                'epistemic_note': (
                    'Opposing attraction forces sum to zero (Newton third law). '
                    'Distinct calculation from Case 1; NOT force derived from Case 1.'
                ),
                'parameters': {
                    'voltage_v': float(plate_result.voltage_v),
                    'gap_m': float(plate_result.gap_m),
                    'area_m2': float(plate_result.area_m2),
                },
                'results': {
                    'electric_field_v_per_m': float(plate_result.electric_field_v_per_m),
                    'pressure_pa': float(plate_result.pressure_pa),
                    'force_on_positive_plate_n': float(plate_result.force_on_positive_plate_n),
                    'force_on_negative_plate_n': float(plate_result.force_on_negative_plate_n),
                    'net_pair_force_n': float(plate_result.net_pair_force_n),
                    'stored_energy_j': float(plate_result.stored_energy_j),
                },
                'virtual_work_crosscheck': vw_check,
            },
        },
        'disclaimer': (
            'Conventional electrostatics baseline. No anomalous thrust model. '
            'Not Exodus patent geometry. Not experimental data.'
        ),
    }
    return manifest


def render(
    output_png: str = 'electrostatics_baseline.png',
    output_json: str = 'electrostatics_manifest.json',
    config_2d: GroundedBoxConfig | None = None,
) -> tuple[Path, Path]:
    cfg = config_2d or GroundedBoxConfig(n=101)
    result = electrode_pair_in_grounded_box(config=cfg)
    plate = parallel_plate_benchmark(1000.0, 0.001, 1e-4)
    study = electrode_pair_mesh_study(n_list=(41, 81, 101, 161), box_width_m=cfg.box_width_m)
    coax_bench = coaxial_cylinder_benchmark(n_list=(41, 81, 161), box_width_m=cfg.box_width_m)

    n = result.potential_v.shape[0]
    length_m = result.grid_spacing_m * (n - 1)
    coords_mm = np.linspace(-length_m / 2, length_m / 2, n) * 1000
    x, y = np.meshgrid(coords_mm, coords_mm, indexing='ij')

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 5.2), layout='constrained')

    # Panel A: Potential
    image0 = axes[0].contourf(x, y, result.potential_v, levels=25, cmap='coolwarm')
    fig.colorbar(image0, ax=axes[0], label='Potential (V)')
    axes[0].contour(x, y, result.fixed_mask.astype(float), levels=[0.5], colors=['black'], linewidths=0.9)
    axes[0].set(
        title=f'A · Case 1: Grounded Box (±{abs(cfg.left_electrode.voltage_v):.0f} V)\nDirichlet Potential (V)',
        xlabel='x (mm)',
        ylabel='y (mm)',
        aspect='equal',
    )

    # Panel B: Electric Field (masked conductors and explicit non-convergence label)
    field_mag, unit_ex, unit_ey = display_field_data(result)
    image1 = axes[1].contourf(x, y, field_mag / 1000.0, levels=25, cmap='viridis')
    fig.colorbar(image1, ax=axes[1], label='|E| (kV/m), vacuum only [grid-sensitive peak]')
    stride = 8
    axes[1].quiver(
        x[::stride, ::stride],
        y[::stride, ::stride],
        unit_ex[::stride, ::stride],
        unit_ey[::stride, ::stride],
        color='white',
        alpha=0.75,
        scale_units='xy',
        scale=0.9,
    )
    axes[1].contour(x, y, result.conductor_mask.astype(float), levels=[0.5], colors=['white'], linewidths=1.0)
    axes[1].set(
        title='B · Case 1: Grounded Box Vacuum Field\n[ILLUSTRATIVE / NON-CONVERGED]',
        xlabel='x (mm)',
        ylabel='y (mm)',
        aspect='equal',
    )

    # Panel C: Separate Ideal Parallel-Plate Analytic Benchmark (R2-F5: clean headroom & label placement)
    micro_n = 1e6
    bar_labels = ['Pos. plate (+x)', 'Neg. plate (-x)', 'Net pair (sum)']
    bar_values = [
        plate.force_on_positive_plate_n * micro_n,
        plate.force_on_negative_plate_n * micro_n,
        plate.net_pair_force_n * micro_n,
    ]
    colors = ['#1f77b4', '#d62728', '#2ca02c']
    bars = axes[2].bar(bar_labels, bar_values, color=colors, width=0.50)
    axes[2].axhline(0, color='black', lw=0.8, ls='--')
    axes[2].set_ylabel('Force along x-axis (µN)')
    axes[2].set_ylim(-650, 650)
    axes[2].tick_params(axis='x', rotation=12)
    axes[2].set_title('C · Case 2: SEPARATE 1D Ideal Plates\nAnalytic Forces (1 kV, 1 mm, 1 cm²)')

    # Labels above/below bars with clear clearance
    for bar, val in zip(bars, bar_values):
        if val > 0:
            axes[2].annotate(
                f'{val:+.1f} µN',
                xy=(bar.get_x() + bar.get_width() / 2, val),
                xytext=(0, 6),
                textcoords='offset points',
                ha='center',
                va='bottom',
                fontsize=8.5,
                fontweight='bold',
            )
        elif val < 0:
            axes[2].annotate(
                f'{val:+.1f} µN',
                xy=(bar.get_x() + bar.get_width() / 2, val),
                xytext=(0, -8),
                textcoords='offset points',
                ha='center',
                va='top',
                fontsize=8.5,
                fontweight='bold',
            )
        else:
            axes[2].annotate(
                f'{val:+.1f} µN',
                xy=(bar.get_x() + bar.get_width() / 2, 0),
                xytext=(0, 6),
                textcoords='offset points',
                ha='center',
                va='bottom',
                fontsize=8.5,
                fontweight='bold',
            )

    axes[2].set_xlabel(
        'Components along x-axis (Newton 3rd law: net pair = 0)\nSEPARATE calculation; NOT force from Case 1',
        fontsize=8.5,
        labelpad=8,
    )

    fig.suptitle(
        'CONVENTIONAL ELECTROSTATICS BASELINE\n'
        'Case 1: 2D grounded box (unconverged peak |E|) · Case 2: Distinct 1D ideal-plate analytic check\n'
        'No anomalous thrust · Not patent geometry · Not experimental data',
        fontsize=10.5,
    )

    png_path = Path(output_png)
    fig.savefig(png_path, dpi=160)
    plt.close(fig)

    manifest = generate_manifest(result, plate, study, coax_bench, str(png_path.name), config_2d=cfg)
    json_path = Path(output_json)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)

    return png_path, json_path


if __name__ == '__main__':
    png, jmanifest = render()
    print(f'Wrote figure to {png}')
    print(f'Wrote manifest to {jmanifest}')

    print('\n--- Mesh Refinement Study: Case 1 (Electrode Pair in Grounded Box) ---')
    print('   n   | Spacing h (mm) | Probe Ex(0,0) (kV/m) | Max Vac |E| (kV/m) | Max Cond |E| (kV/m)')
    print('-------+----------------+----------------------+--------------------+------------------')
    with open(jmanifest, 'r', encoding='utf-8') as f:
        mdata = json.load(f)
    for row in mdata['cases']['case_1_grounded_box_2d']['mesh_study_probe_midpoint']:
        print(f" {row['n']:4d}  |    {row['grid_spacing_m']*1000:6.3f}      |      {row['probe_ex_v_per_m']/1000:7.2f}         |    {row['max_vacuum_e_v_per_m']/1000:8.2f}        |     {row['max_conductor_raw_gradient_v_per_m']/1000:7.2f}")

    print('\n--- Analytic Benchmark: Coaxial Cylinder Laplace Convergence ---')
    print('   n   | Analytic V (V) | Numerical V (V) | Error V (V) | Analytic Er (kV/m) | Num Ex (kV/m) | Error E (kV/m)')
    print('-------+----------------+-----------------+-------------+--------------------+---------------+---------------')
    for row in mdata['cases']['case_1_grounded_box_2d']['coaxial_analytic_benchmark']:
        print(f" {row['n']:4d}  |    {row['analytic_potential_v']:7.2f}     |     {row['numerical_potential_v']:7.2f}     |   {row['potential_error_v']:6.3f}    |       {row['analytic_field_er_v_per_m']/1000:6.2f}       |     {row['numerical_field_ex_v_per_m']/1000:6.2f}    |    {row['field_error_v_per_m']/1000:6.3f}")
