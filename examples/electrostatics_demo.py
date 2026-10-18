"""Generate evidence-labeled conventional-electrostatics figure and paired JSON manifest.

From repository root: python examples/electrostatics_demo.py
"""
from __future__ import annotations

import json
import os
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
    assess_probe_convergence,
    coaxial_cylinder_benchmark,
    electrode_pair_in_grounded_box,
    electrode_pair_mesh_study,
    evaluate_conductor_surface_interface,
    format_panel_a_title,
    format_voltage_title,
    parallel_plate_benchmark,
    verify_plate_force_virtual_work,
)


def get_git_provenance() -> dict[str, str | bool]:
    """Retrieve git provenance differentiating PR source HEAD SHA from tested checkout SHA.

    In GitHub Actions on pull_request events, actions/checkout checks out refs/pull/<N>/merge
    (a synthetic merge commit). To ensure complete reproducibility and auditability:
    - 'pr_source_head_sha': The exact commit SHA of the source branch being tested (from
      github.event.pull_request.head.sha or local git HEAD).
    - 'tested_checkout_sha': The actual git commit checked out in the working directory (synthetic
      merge commit in PR CI, or local HEAD).
    - 'pr_base_sha': The target base branch commit SHA (e.g. main).
    - 'is_synthetic_pr_merge': True if running on a GitHub Actions pull_request synthetic merge commit.
    """
    repo_dir = Path(__file__).resolve().parents[1]
    checkout_sha = 'unknown'
    try:
        checkout_sha = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'],
            cwd=str(repo_dir),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        pass

    event_name = os.environ.get('GITHUB_EVENT_NAME') or ('ci' if os.environ.get('CI') else 'local')
    env_source_sha = os.environ.get('PR_SOURCE_HEAD_SHA')
    env_base_sha = os.environ.get('PR_BASE_SHA')

    source_sha = env_source_sha.strip() if env_source_sha else checkout_sha

    base_sha = env_base_sha.strip() if env_base_sha else None
    if not base_sha:
        try:
            base_sha = subprocess.check_output(
                ['git', 'rev-parse', 'origin/main'],
                cwd=str(repo_dir),
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except Exception:
            base_sha = 'unknown'

    is_synthetic = bool(env_source_sha and env_source_sha != checkout_sha)

    return {
        'pr_source_head_sha': source_sha,
        'tested_checkout_sha': checkout_sha,
        'pr_base_sha': base_sha or 'unknown',
        'ci_event_name': event_name,
        'is_synthetic_pr_merge': is_synthetic,
    }


def get_git_commit() -> str:
    """Retrieve git PR source HEAD commit SHA (or local checkout SHA)."""
    return str(get_git_provenance()['pr_source_head_sha'])


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
    study_config: GroundedBoxConfig | None = None,
) -> dict:
    """Build machine-readable run manifest with provenance, parameters, and validation status."""
    prov = get_git_provenance()
    vw_check = verify_plate_force_virtual_work(
        plate_result.voltage_v, plate_result.gap_m, plate_result.area_m2
    )

    # Resolve configuration dynamically from result or passed config (R2-F3, R3-F1, R3-F2)
    active_config = config_2d or result_2d.config or GroundedBoxConfig()
    active_study_config = study_config or active_config

    study_table = [
        {
            'n': r.n,
            'grid_spacing_m': r.grid_spacing_m,
            'requested_probe_xy_m': [r.requested_probe_x_m, r.requested_probe_y_m],
            'sampled_probe_coords': [r.probe_x_m, r.probe_y_m],
            'probe_xy_m': [r.probe_x_m, r.probe_y_m],
            'probe_in_vacuum': r.probe_in_vacuum,
            'probe_status': r.probe_status,
            'probe_potential_v': r.probe_potential_v,
            'probe_ex_v_per_m': r.probe_ex_v_per_m,
            'probe_ey_v_per_m': r.probe_ey_v_per_m,
            'max_vacuum_e_v_per_m': r.max_vacuum_e_v_per_m,
            'max_conductor_raw_gradient_v_per_m': r.max_conductor_raw_gradient_v_per_m,
            'max_discrete_residual_v': r.max_discrete_residual_v,
            'potential_antisymmetry_error_v': r.potential_antisymmetry_error_v,
            'potential_central_inversion_error_v': r.potential_central_inversion_error_v,
            'symmetry_status': r.symmetry_status,
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

    assessment = assess_probe_convergence(study_results or [], requested_probe_xy_m=(0.0, 0.0))
    probe_eval = assessment.assessment_summary

    manifest = {
        'schema_version': '1.2.0',
        'artifact_file': output_png,
        'git_commit': prov['pr_source_head_sha'],
        'tested_checkout_sha': prov['tested_checkout_sha'],
        'provenance': {
            'pr_source_head_sha': prov['pr_source_head_sha'],
            'tested_checkout_sha': prov['tested_checkout_sha'],
            'pr_base_sha': prov['pr_base_sha'],
            'ci_event_name': prov['ci_event_name'],
            'is_synthetic_pr_merge': prov['is_synthetic_pr_merge'],
            'provenance_note': (
                'pr_source_head_sha records the PR branch head commit. '
                'tested_checkout_sha records the git commit checked out during CI execution '
                '(which on GitHub pull_request events is a synthetic merge commit refs/pull/PR/merge). '
                'Both are recorded explicitly to eliminate provenance conflation.'
            ),
        },
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
                    'and is NOT converged. Probe field convergence away from boundaries must be '
                    'quantitatively verified. Conductor interior field is masked (E=0). '
                    'Not an isolated thruster. Not patent geometry.'
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
                'mesh_study_geometry': {
                    'enclosure_width_m': float(active_study_config.box_width_m),
                    'left_electrode': {
                        'center_x_m': float(active_study_config.left_electrode.center_x_m),
                        'center_y_m': float(active_study_config.left_electrode.center_y_m),
                        'radius_m': float(active_study_config.left_electrode.radius_m),
                        'voltage_v': float(active_study_config.left_electrode.voltage_v),
                    },
                    'right_electrode': {
                        'center_x_m': float(active_study_config.right_electrode.center_x_m),
                        'center_y_m': float(active_study_config.right_electrode.center_y_m),
                        'radius_m': float(active_study_config.right_electrode.radius_m),
                        'voltage_v': float(active_study_config.right_electrode.voltage_v),
                    },
                },
                'mesh_study_probe_midpoint': study_table,
                'probe_convergence_assessment': probe_eval,
                'probe_convergence_details': {
                    'vacuum_status': assessment.vacuum_status,
                    'convergence_status': assessment.convergence_status,
                    'is_converged': assessment.is_converged,
                    'requested_probe_xy_m': list(assessment.requested_probe_xy_m),
                    'sampled_probe_coords': [list(c) for c in assessment.sampled_probe_coords],
                    'coords_stable': assessment.coords_stable,
                    'relative_field_drift': assessment.relative_field_drift,
                },
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
    study = electrode_pair_mesh_study(n_list=(41, 81, 101, 161), config=cfg)
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
        title=format_panel_a_title(cfg),
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

    manifest = generate_manifest(
        result, plate, study, coax_bench, str(png_path.name), config_2d=cfg, study_config=cfg
    )
    json_path = Path(output_json)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, allow_nan=False)

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
        pex_str = f"{row['probe_ex_v_per_m']/1000:7.2f}" if row['probe_ex_v_per_m'] is not None else "    N/A"
        print(f" {row['n']:4d}  |    {row['grid_spacing_m']*1000:6.3f}      |      {pex_str}         |    {row['max_vacuum_e_v_per_m']/1000:8.2f}        |     {row['max_conductor_raw_gradient_v_per_m']/1000:7.2f}")

    print('\n--- Analytic Benchmark: Coaxial Cylinder Laplace Convergence ---')
    print('   n   | Analytic V (V) | Numerical V (V) | Error V (V) | Analytic Er (kV/m) | Num Ex (kV/m) | Error E (kV/m)')
    print('-------+----------------+-----------------+-------------+--------------------+---------------+---------------')
    for row in mdata['cases']['case_1_grounded_box_2d']['coaxial_analytic_benchmark']:
        print(f" {row['n']:4d}  |    {row['analytic_potential_v']:7.2f}     |     {row['numerical_potential_v']:7.2f}     |   {row['potential_error_v']:6.3f}    |       {row['analytic_field_er_v_per_m']/1000:6.2f}       |     {row['numerical_field_ex_v_per_m']/1000:6.2f}    |    {row['field_error_v_per_m']/1000:6.3f}")
