"""Generate evidence-labeled conventional-electrostatics figure and paired JSON manifest.

From repository root: python examples/electrostatics_demo.py
"""
from __future__ import annotations

import functools
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
    ElectrodeConfig,
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
import electrostatics_numerics as en
import scalar_wave_3d as sw



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
            'requested_probe_in_vacuum': getattr(r, 'requested_probe_in_vacuum', r.probe_in_vacuum),
            'sampled_node_in_vacuum': getattr(r, 'sampled_node_in_vacuum', r.probe_in_vacuum),
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

    # Derive and validate common requested probe target from study results (R6-F3)
    if study_results:
        distinct_targets = {
            (float(r.requested_probe_x_m), float(r.requested_probe_y_m))
            for r in study_results
        }
        if len(distinct_targets) == 1:
            target_probe_xy = next(iter(distinct_targets))
        else:
            # Conflicting requested targets across rows
            target_probe_xy = (float(study_results[0].requested_probe_x_m), float(study_results[0].requested_probe_y_m))
    else:
        target_probe_xy = (0.0, 0.0)

    assessment = assess_probe_convergence(study_results or [], requested_probe_xy_m=target_probe_xy)
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
                'mesh_study_probe': study_table,
                'mesh_study_probe_midpoint': study_table,
                'probe_convergence_assessment': probe_eval,
                'probe_convergence_details': {
                    'vacuum_status': assessment.vacuum_status,
                    'convergence_status': assessment.convergence_status,
                    'is_converged': assessment.is_converged,
                    'is_stable': assessment.is_stable,
                    'convergence_flag_note': (
                        'is_converged is reserved for formal asymptotic convergence proofs (e.g. Richardson extrapolation); '
                        'finite-grid stability across tested resolutions is indicated by is_stable.'
                    ),
                    'requested_probe_xy_m': list(assessment.requested_probe_xy_m),
                    'is_midpoint': bool(target_probe_xy == (0.0, 0.0)),
                    'sampled_probe_coords': [list(c) for c in assessment.sampled_probe_coords],
                    'coords_stable': assessment.coords_stable,
                    'relative_field_drift': assessment.relative_field_drift,
                },
                'coaxial_analytic_benchmark': coax_table,
                'maxwell_stress_force_budget_2d': {
                    'description': '2D Maxwell stress closed-contour integration on all conductors (force per unit depth, N/m)',
                    'units': 'N/m',
                    'left_electrode_fx_n_per_m': float(en.evaluate_whole_apparatus_force_budget(result_2d).left_electrode_fx_n_per_m),
                    'left_electrode_fy_n_per_m': float(en.evaluate_whole_apparatus_force_budget(result_2d).left_electrode_fy_n_per_m),
                    'right_electrode_fx_n_per_m': float(en.evaluate_whole_apparatus_force_budget(result_2d).right_electrode_fx_n_per_m),
                    'right_electrode_fy_n_per_m': float(en.evaluate_whole_apparatus_force_budget(result_2d).right_electrode_fy_n_per_m),
                    'enclosure_reaction_fx_n_per_m': float(en.evaluate_whole_apparatus_force_budget(result_2d).enclosure_reaction_fx_n_per_m),
                    'enclosure_reaction_fy_n_per_m': float(en.evaluate_whole_apparatus_force_budget(result_2d).enclosure_reaction_fy_n_per_m),
                    'net_modeled_force_fx_n_per_m': float(en.evaluate_whole_apparatus_force_budget(result_2d).net_electrostatic_force_fx_n_per_m),
                    'net_modeled_force_fy_n_per_m': float(en.evaluate_whole_apparatus_force_budget(result_2d).net_electrostatic_force_fy_n_per_m),
                    'is_force_balanced': bool(en.evaluate_whole_apparatus_force_budget(result_2d).is_force_balanced_to_tolerance),
                    'unmodeled_reaction_note': en.evaluate_whole_apparatus_force_budget(result_2d).unmodeled_reaction_explanation,
                    **_get_cached_force_sub_studies(active_config),
                    'contour_invariance_study': {
                        'description': 'Demonstration of path independence of Maxwell stress in vacuum across concentric loops',
                        'contour_margins_m': en.contour_invariance_study(result_2d, electrode='left').contour_margins_m,
                        'measured_fx_n_per_m': en.contour_invariance_study(result_2d, electrode='left').measured_fx_n_per_m,
                        'max_relative_variation': en.contour_invariance_study(result_2d, electrode='left').max_relative_variation,
                        'is_invariant_to_tolerance': en.contour_invariance_study(result_2d, electrode='left').is_invariant_to_tolerance,
                    },
                },
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
            'p1_analytic_convergence_benchmarks': _get_cached_analytic_benchmarks(float(active_config.box_width_m)),
            'p1_3d_scalar_wave_numerics_audit': _get_cached_wave_audit(),
        },
        'disclaimer': (
            'Conventional electrostatics and mathematical wave baseline. No anomalous thrust model. '
            'Not Exodus patent geometry. Not experimental data.'
        ),
    }
    return manifest


@functools.lru_cache(maxsize=8)
def _get_cached_force_sub_studies(active_config: GroundedBoxConfig) -> dict:
    """Compute and cache deterministic P1 force convergence and virtual-work sub-studies for active_config."""
    f_study = en.force_mesh_convergence_study((41, 81, 161), config=active_config)
    vw = en.cross_check_maxwell_stress_with_virtual_work(active_config, electrode='left')
    vw_sym = en.virtual_work_convergence_and_sensitivity_study(active_config, n_list=(81, 161))
    vw_asym = en.virtual_work_convergence_and_sensitivity_study(
        GroundedBoxConfig(
            box_width_m=active_config.box_width_m,
            left_electrode=ElectrodeConfig(center_x_m=-0.008, voltage_v=600.0),
            right_electrode=ElectrodeConfig(center_x_m=0.008, voltage_v=100.0),
        ),
        n_list=(81, 161),
    )
    b_asym = en.evaluate_whole_apparatus_force_budget(
        electrode_pair_in_grounded_box(config=GroundedBoxConfig(
            box_width_m=active_config.box_width_m,
            left_electrode=ElectrodeConfig(center_x_m=-0.008, voltage_v=600.0),
            right_electrode=ElectrodeConfig(center_x_m=0.008, voltage_v=100.0),
            n=81,
        )),
        tolerance_n_per_m=1e-6,
    )
    asym_study = en.force_mesh_convergence_study(
        (41, 81, 161),
        config=GroundedBoxConfig(
            box_width_m=active_config.box_width_m,
            left_electrode=ElectrodeConfig(center_x_m=-0.008, voltage_v=600.0),
            right_electrode=ElectrodeConfig(center_x_m=0.008, voltage_v=100.0),
        ),
        tolerance_relative_change=0.05,
        tolerance_residual_n_per_m=1e-7,
    )
    off_study = en.force_mesh_convergence_study(
        (41, 81, 161),
        config=GroundedBoxConfig(
            box_width_m=active_config.box_width_m,
            left_electrode=ElectrodeConfig(center_x_m=-0.008, center_y_m=0.004, radius_m=0.003, voltage_v=600.0),
            right_electrode=ElectrodeConfig(center_x_m=0.008, center_y_m=-0.002, radius_m=0.003, voltage_v=-400.0),
        ),
        tolerance_relative_change=0.05,
        tolerance_residual_n_per_m=1e-7,
    )
    indep_study = en.benchmark_independent_electrostatic_solver_verification(
        n_list=(41, 81, 161, 321),
    )
    return {
        'force_mesh_convergence_study': {
            'description': 'Full-vector 6-component mesh convergence of Maxwell stress forces and 2D net balance residual across resolutions (P1-R3-F1)',
            'parameters': {
                'n_list': [41, 81, 161],
                'tolerance_relative_change': 0.05,
                'tolerance_abs_change_n_per_m': 5e-4,
                'tolerance_near_zero_n_per_m': 1e-6,
                'tolerance_residual_n_per_m': 1e-6,
            },
            'rows': [
                {
                    'n': r.n,
                    'grid_spacing_m': r.grid_spacing_m,
                    'left_electrode_fx_n_per_m': r.left_electrode_fx_n_per_m,
                    'left_electrode_fy_n_per_m': r.left_electrode_fy_n_per_m,
                    'right_electrode_fx_n_per_m': r.right_electrode_fx_n_per_m,
                    'right_electrode_fy_n_per_m': r.right_electrode_fy_n_per_m,
                    'enclosure_reaction_fx_n_per_m': r.enclosure_reaction_fx_n_per_m,
                    'enclosure_reaction_fy_n_per_m': r.enclosure_reaction_fy_n_per_m,
                    'net_residual_fx_n_per_m': r.net_residual_fx_n_per_m,
                    'net_residual_fy_n_per_m': r.net_residual_fy_n_per_m,
                    'net_residual_magnitude_n_per_m': r.net_residual_magnitude_n_per_m,
                    'relative_change_left_to_prev': r.relative_change_left_to_prev,
                    'relative_change_right_to_prev': r.relative_change_right_to_prev,
                    'relative_change_box_to_prev': r.relative_change_box_to_prev,
                    'max_relative_change_to_prev': r.max_relative_change_to_prev,
                    'max_abs_change_to_prev_n_per_m': r.max_abs_change_to_prev,
                }
                for r in f_study.rows
            ],
            'component_assessments': {
                k: {
                    'regime': v.regime,
                    'finest_value_n_per_m': v.finest_value_n_per_m,
                    'penultimate_value_n_per_m': v.penultimate_value_n_per_m,
                    'last_step_abs_diff_n_per_m': v.last_step_abs_diff_n_per_m,
                    'last_step_relative_change': v.last_step_relative_change,
                    'observed_order': v.observed_order,
                    'is_converged': v.is_converged,
                }
                for k, v in f_study.component_assessments.items()
            },
            'observed_order_left_electrode': f_study.observed_order_left_electrode,
            'observed_order_right_electrode': f_study.observed_order_right_electrode,
            'observed_order_enclosure': f_study.observed_order_enclosure,
            'max_component_relative_change': f_study.max_component_relative_change,
            'per_component_last_step_diff_n_per_m': f_study.per_component_last_step_diff_n_per_m,
            'max_component_last_step_diff_n_per_m': f_study.max_component_last_step_diff_n_per_m,
            'max_vector_last_step_diff_n_per_m': f_study.max_vector_last_step_diff_n_per_m,
            'left_fx_last_step_diff_n_per_m': f_study.left_fx_last_step_diff_n_per_m,
            'discretization_error_note': f_study.discretization_error_note,
            'is_converged_to_tolerance': f_study.is_converged_to_tolerance,
        },
        'virtual_work_crosscheck': {
            'description': 'Independent cross-check comparing Maxwell stress tensor force to virtual work (+dU/dx)_V at constant potential',
            'electrode': 'left',
            'n': vw.n,
            'delta_x_m': vw.delta_x_m,
            'maxwell_stress_fx_n_per_m': vw.maxwell_stress_fx_n_per_m,
            'virtual_work_fx_n_per_m': vw.virtual_work_fx_n_per_m,
            'relative_difference': vw.relative_difference,
            'is_consistent_to_tolerance': vw.is_consistent_to_tolerance,
            'epistemic_limitation_note': vw.epistemic_limitation_note,
            'diagnostic_note': vw.diagnostic_note,
        },
        'virtual_work_multi_resolution_and_sensitivity_study': {
            'description': 'Multi-resolution (n=81, 161) and step-size (1h vs 2h) virtual-work cross-check for both electrodes on symmetric and asymmetric setups (P1-R3-F2)',
            'symmetric_setup': {
                'rows': [
                    {
                        'n': r.n,
                        'grid_spacing_m': r.grid_spacing_m,
                        'left_mst_fx_n_per_m': r.left_mst_fx_n_per_m,
                        'left_vw_fx_1h_n_per_m': r.left_vw_fx_1h_n_per_m,
                        'left_vw_fx_2h_n_per_m': r.left_vw_fx_2h_n_per_m,
                        'left_rel_diff_1h': r.left_rel_diff_1h,
                        'left_rel_diff_2h': r.left_rel_diff_2h,
                        'left_step_sensitivity_rel': r.left_step_sensitivity_rel,
                        'left_same_sign': r.left_same_sign,
                        'right_mst_fx_n_per_m': r.right_mst_fx_n_per_m,
                        'right_vw_fx_1h_n_per_m': r.right_vw_fx_1h_n_per_m,
                        'right_vw_fx_2h_n_per_m': r.right_vw_fx_2h_n_per_m,
                        'right_rel_diff_1h': r.right_rel_diff_1h,
                        'right_rel_diff_2h': r.right_rel_diff_2h,
                        'right_step_sensitivity_rel': r.right_step_sensitivity_rel,
                        'right_same_sign': r.right_same_sign,
                        'enclosure_mst_fx_n_per_m': r.enclosure_mst_fx_n_per_m,
                        'net_electrode_mst_fx_n_per_m': r.net_electrode_mst_fx_n_per_m,
                        'net_electrode_vw_fx_1h_n_per_m': r.net_electrode_vw_fx_1h_n_per_m,
                        'net_electrode_rel_diff_1h': r.net_electrode_rel_diff_1h,
                    }
                    for r in vw_sym.rows
                ],
                'left_discrepancy_decreases_with_refinement': vw_sym.left_discrepancy_decreases_with_refinement,
                'right_discrepancy_decreases_with_refinement': vw_sym.right_discrepancy_decreases_with_refinement,
                'all_signs_consistent': vw_sym.all_signs_consistent,
                'is_consistent_to_tolerance': vw_sym.is_consistent_to_tolerance,
                'epistemic_limitation_note': vw_sym.epistemic_limitation_note,
                'diagnostic_note': vw_sym.diagnostic_note,
            },
            'asymmetric_setup_600v_100v': {
                'rows': [
                    {
                        'n': r.n,
                        'grid_spacing_m': r.grid_spacing_m,
                        'left_mst_fx_n_per_m': r.left_mst_fx_n_per_m,
                        'left_vw_fx_1h_n_per_m': r.left_vw_fx_1h_n_per_m,
                        'left_vw_fx_2h_n_per_m': r.left_vw_fx_2h_n_per_m,
                        'left_rel_diff_1h': r.left_rel_diff_1h,
                        'left_rel_diff_2h': r.left_rel_diff_2h,
                        'left_step_sensitivity_rel': r.left_step_sensitivity_rel,
                        'left_same_sign': r.left_same_sign,
                        'right_mst_fx_n_per_m': r.right_mst_fx_n_per_m,
                        'right_vw_fx_1h_n_per_m': r.right_vw_fx_1h_n_per_m,
                        'right_vw_fx_2h_n_per_m': r.right_vw_fx_2h_n_per_m,
                        'right_rel_diff_1h': r.right_rel_diff_1h,
                        'right_rel_diff_2h': r.right_rel_diff_2h,
                        'right_step_sensitivity_rel': r.right_step_sensitivity_rel,
                        'right_same_sign': r.right_same_sign,
                        'enclosure_mst_fx_n_per_m': r.enclosure_mst_fx_n_per_m,
                        'net_electrode_mst_fx_n_per_m': r.net_electrode_mst_fx_n_per_m,
                        'net_electrode_vw_fx_1h_n_per_m': r.net_electrode_vw_fx_1h_n_per_m,
                        'net_electrode_rel_diff_1h': r.net_electrode_rel_diff_1h,
                    }
                    for r in vw_asym.rows
                ],
                'left_discrepancy_decreases_with_refinement': vw_asym.left_discrepancy_decreases_with_refinement,
                'right_discrepancy_decreases_with_refinement': vw_asym.right_discrepancy_decreases_with_refinement,
                'all_signs_consistent': vw_asym.all_signs_consistent,
                'is_consistent_to_tolerance': vw_asym.is_consistent_to_tolerance,
                'epistemic_limitation_note': vw_asym.epistemic_limitation_note,
                'diagnostic_note': vw_asym.diagnostic_note,
            },
        },
        'asymmetric_voltage_demonstration': {
            'description': 'Non-trivial whole-apparatus force balance with unequal voltages (+600V, +100V) producing nonzero box reaction',
            'parameters': {
                'left_electrode_voltage_v': 600.0,
                'right_electrode_voltage_v': 100.0,
                'box_width_m': active_config.box_width_m,
            },
            'n81_results': {
                'left_electrode_fx_n_per_m': float(b_asym.left_electrode_fx_n_per_m),
                'left_electrode_fy_n_per_m': float(b_asym.left_electrode_fy_n_per_m),
                'right_electrode_fx_n_per_m': float(b_asym.right_electrode_fx_n_per_m),
                'right_electrode_fy_n_per_m': float(b_asym.right_electrode_fy_n_per_m),
                'enclosure_reaction_fx_n_per_m': float(b_asym.enclosure_reaction_fx_n_per_m),
                'enclosure_reaction_fy_n_per_m': float(b_asym.enclosure_reaction_fy_n_per_m),
                'net_residual_fx_n_per_m': float(b_asym.net_electrostatic_force_fx_n_per_m),
                'net_residual_fy_n_per_m': float(b_asym.net_electrostatic_force_fy_n_per_m),
                'relative_residual': float(abs(b_asym.net_electrostatic_force_fx_n_per_m) / abs(b_asym.enclosure_reaction_fx_n_per_m)),
                'is_force_balanced': bool(b_asym.is_force_balanced_to_tolerance),
            },
            'asymmetric_mesh_convergence': [
                {
                    'n': r.n,
                    'grid_spacing_m': r.grid_spacing_m,
                    'left_electrode_fx_n_per_m': r.left_electrode_fx_n_per_m,
                    'left_electrode_fy_n_per_m': r.left_electrode_fy_n_per_m,
                    'right_electrode_fx_n_per_m': r.right_electrode_fx_n_per_m,
                    'right_electrode_fy_n_per_m': r.right_electrode_fy_n_per_m,
                    'enclosure_reaction_fx_n_per_m': r.enclosure_reaction_fx_n_per_m,
                    'enclosure_reaction_fy_n_per_m': r.enclosure_reaction_fy_n_per_m,
                    'net_residual_fx_n_per_m': r.net_residual_fx_n_per_m,
                    'net_residual_fy_n_per_m': r.net_residual_fy_n_per_m,
                    'net_residual_magnitude_n_per_m': r.net_residual_magnitude_n_per_m,
                    'relative_change_left_to_prev': r.relative_change_left_to_prev,
                    'relative_change_box_to_prev': r.relative_change_box_to_prev,
                    'max_relative_change_to_prev': r.max_relative_change_to_prev,
                }
                for r in asym_study.rows
            ],
            'per_component_last_step_diff_n_per_m': asym_study.per_component_last_step_diff_n_per_m,
            'max_component_last_step_diff_n_per_m': asym_study.max_component_last_step_diff_n_per_m,
            'asymmetric_enclosure_reaction_converged': asym_study.is_converged_to_tolerance,
        },
        'off_axis_y_asymmetric_demonstration': {
            'description': 'Full-vector 2D force balance and convergence with off-axis y-asymmetric electrodes activating all 6 Fx and Fy components (P1-R3-F1)',
            'parameters': {
                'left_electrode': {'center_x_m': -0.008, 'center_y_m': 0.004, 'voltage_v': 600.0},
                'right_electrode': {'center_x_m': 0.008, 'center_y_m': -0.002, 'voltage_v': -400.0},
                'n_list': [41, 81, 161],
            },
            'rows': [
                {
                    'n': r.n,
                    'left_electrode_fx_n_per_m': r.left_electrode_fx_n_per_m,
                    'left_electrode_fy_n_per_m': r.left_electrode_fy_n_per_m,
                    'right_electrode_fx_n_per_m': r.right_electrode_fx_n_per_m,
                    'right_electrode_fy_n_per_m': r.right_electrode_fy_n_per_m,
                    'enclosure_reaction_fx_n_per_m': r.enclosure_reaction_fx_n_per_m,
                    'enclosure_reaction_fy_n_per_m': r.enclosure_reaction_fy_n_per_m,
                    'net_residual_fx_n_per_m': r.net_residual_fx_n_per_m,
                    'net_residual_fy_n_per_m': r.net_residual_fy_n_per_m,
                    'net_residual_magnitude_n_per_m': r.net_residual_magnitude_n_per_m,
                    'max_relative_change_to_prev': r.max_relative_change_to_prev,
                }
                for r in off_study.rows
            ],
            'per_component_last_step_diff_n_per_m': off_study.per_component_last_step_diff_n_per_m,
            'max_component_last_step_diff_n_per_m': off_study.max_component_last_step_diff_n_per_m,
            'max_vector_last_step_diff_n_per_m': off_study.max_vector_last_step_diff_n_per_m,
            'is_converged_to_tolerance': off_study.is_converged_to_tolerance,
        },
        'independent_electrostatic_solver_verification': {
            'description': 'Independent electrostatic solver verification: matrix-free SOR and continuous grid-free Method of Fundamental Solutions (MFS) boundary collocation (P1-R4-F3, P1-R5-F2, P1-R5-F3)',
            'mfs_max_sampled_boundary_error_v': indep_study.mfs_max_sampled_boundary_error_v,
            'mfs_max_independent_boundary_error_v': indep_study.mfs_max_independent_boundary_error_v,
            'mfs_net_force_residual_n_per_m': indep_study.mfs_net_force_residual_n_per_m,
            'sor_vs_direct_lu_max_potential_diff_v': indep_study.sor_vs_direct_lu_max_potential_diff_v,
            'sor_vs_direct_lu_max_force_diff_n_per_m': indep_study.sor_vs_direct_lu_max_force_diff_n_per_m,
            'fdm_vs_mfs_convergence': [
                {
                    'n': r.n,
                    'grid_spacing_m': r.grid_spacing_m,
                    'midpoint_e_rel_error_vs_mfs': r.midpoint_e_rel_error_vs_mfs,
                    'left_force_vec_rel_error_vs_mfs': r.left_force_vec_rel_error_vs_mfs,
                    'right_force_vec_rel_error_vs_mfs': r.right_force_vec_rel_error_vs_mfs,
                    'enclosure_force_vec_rel_error_vs_mfs': r.enclosure_force_vec_rel_error_vs_mfs,
                }
                for r in indep_study.fdm_vs_mfs_rows
            ],
            'endpoint_errors_improve': indep_study.endpoint_errors_improve,
            'strict_intermediate_monotonicity': indep_study.strict_intermediate_monotonicity,
            'errors_decrease_toward_mfs_with_refinement': indep_study.errors_decrease_toward_mfs_with_refinement,
            'is_verified_to_tolerance': indep_study.is_verified_to_tolerance,
            'methodological_distinction_note': indep_study.methodological_distinction_note,
            'diagnostic_note': indep_study.diagnostic_note,
        },
    }


@functools.lru_cache(maxsize=8)
def _get_cached_analytic_benchmarks(box_width_m: float) -> dict:
    """Compute and cache P1-A analytic harmonic benchmarks and enclosure sensitivity studies."""
    return {
        'description': 'P1-A independent analytic harmonic benchmarks and enclosure sensitivity studies',
        'cubic_harmonic_polynomial_benchmark': [
            {
                'n': r.n,
                'grid_spacing_m': r.grid_spacing_m,
                'max_potential_error_v': r.max_potential_error_v,
                'max_discrete_residual_v': r.max_discrete_residual_v,
                'is_exact_to_tolerance': r.is_exact_to_tolerance,
            }
            for r in en.harmonic_polynomial_benchmark((21, 41, 81, 161), box_width_m=box_width_m)
        ],
        'smooth_harmonic_trig_convergence': [
            {
                'n': r.n,
                'grid_spacing_m': r.grid_spacing_m,
                'max_potential_error_v': r.max_potential_error_v,
                'l2_potential_error_v': r.l2_potential_error_v,
                'max_field_error_v_per_m': r.max_field_error_v_per_m,
                'observed_order_potential': r.observed_order_potential,
                'observed_order_field': r.observed_order_field,
            }
            for r in en.harmonic_trig_benchmark((21, 41, 81, 161), box_width_m=box_width_m)
        ],
        'enclosure_size_sensitivity_study': [
            {
                'box_width_m': r.box_width_m,
                'n': r.n,
                'midpoint_ex_v_per_m': r.midpoint_ex_v_per_m,
                'max_outer_wall_field_v_per_m': r.max_outer_wall_field_v_per_m,
            }
            for r in en.enclosure_size_sensitivity_study((0.03, 0.04, 0.06, 0.08))
        ],
    }


@functools.lru_cache(maxsize=2)
def _get_cached_wave_audit() -> dict:
    """Compute and cache deterministic P1-C 3D scalar wave numerics audit section."""
    res_prop = sw.benchmark_pulse_propagation_speed(40, 20)
    res_sponge = sw.benchmark_sponge_reflection_reference_subtracted(40, 8, max_sigma=3.0, n_steps=80)
    ctrl_rows = sw.benchmark_sponge_reflection_controls((0.0, 0.5, 1.5, 3.0, 15.0), grid_size=40, sponge_width=8, n_steps=80)
    sweep = sw.benchmark_sponge_reflection_parameter_sweep()
    res_legacy = sw.fixed_window_late_early_probe_amplitude_proxy(48, 10, max_sigma=3.0, n_steps=70)
    res_energy = sw.benchmark_two_material_energy_conservation(36, 35)
    slow = sw.benchmark_two_material_interface_transmission(c1=1.0, c2=0.6, dx_list=(1.0, 0.5, 0.25))
    fast = sw.benchmark_two_material_interface_transmission(c1=0.6, c2=1.0, dx_list=(1.0, 0.5, 0.25))
    res_grid = sw.benchmark_wave_grid_convergence((17, 33, 65))
    return {
        'description': 'P1-C 3D scalar wave numerics, CFL stability, energy conservation, interface reflection/transmission, and sponge absorption benchmarks',
        'cfl_standard': 'dt = 0.85 * dx / (c * sqrt(3)) <= 1/sqrt(3)',
        'sponge_boundary_absorption': 'Quadratic damping conductivity layer sigma(d) = max_sigma * (d/w)^2',
        'energy_density_units': 'arbitrary_energy_units (dimensionless toy field model, not Joules)',
        'pulse_propagation_benchmark': {
            'description': 'Pulse propagation velocity tracking centroid along 3D axis',
            'parameters': {'grid_size': 40, 'n_steps': 20, 'c_m_per_s': 1.0, 'tolerance': 0.05},
            'n_steps': res_prop.n_steps,
            'dt_s': res_prop.dt_s,
            'theoretical_distance_m': res_prop.theoretical_distance_m,
            'measured_distance_m': res_prop.measured_distance_m,
            'relative_speed_error': res_prop.relative_speed_error,
            'is_accurate_to_tolerance': res_prop.is_accurate_to_tolerance,
        },
        'sponge_boundary_reflection_reference_subtracted_benchmark': {
            'description': 'Reference-subtracted reflection measurement with closed discrete energy budget, surface-integrated return flux, and geometric travel-time gating (P1-R2-F1, P1-R3-F4, P1-R4-F1)',
            'parameters': {
                'grid_size': res_sponge.grid_size,
                'sponge_width': res_sponge.sponge_width,
                'max_sigma': res_sponge.max_sigma,
                'n_steps': res_sponge.n_steps,
                'ref_grid_size': res_sponge.ref_grid_size,
                'probe_offset': 6,
                'dt_factor': res_sponge.dt_factor,
                'tolerance_proxy_max': 0.05,
            },
            'incident_peak_amplitude': res_sponge.incident_peak_amplitude,
            'reflected_peak_amplitude': res_sponge.reflected_peak_amplitude,
            'probe_local_amplitude_ratio_proxy': res_sponge.probe_local_amplitude_ratio_proxy,
            'probe_local_peak_squared_proxy': res_sponge.probe_local_peak_squared_proxy,
            'probe_amplitude_reflection_ratio': res_sponge.probe_amplitude_reflection_ratio,
            'probe_peak_squared_reflection_proxy': res_sponge.probe_peak_squared_reflection_proxy,
            'terminal_interior_reflected_energy_snapshot_proxy': res_sponge.terminal_interior_reflected_energy_snapshot_proxy,
            'peak_window_interior_reflected_energy_snapshot_proxy': res_sponge.peak_window_interior_reflected_energy_snapshot_proxy,
            'initial_discrete_hamiltonian': res_sponge.initial_discrete_hamiltonian,
            'final_total_discrete_hamiltonian': res_sponge.final_total_discrete_hamiltonian,
            'cumulative_sponge_dissipated_energy': res_sponge.cumulative_sponge_dissipated_energy,
            'sponge_dissipated_energy_fraction': res_sponge.sponge_dissipated_energy_fraction,
            'remaining_total_energy_fraction': res_sponge.remaining_total_energy_fraction,
            'discrete_energy_budget_closure_error': res_sponge.discrete_energy_budget_closure_error,
            'cumulative_incident_outgoing_surface_flux': res_sponge.cumulative_incident_outgoing_surface_flux,
            'cumulative_reflected_return_surface_flux': res_sponge.cumulative_reflected_return_surface_flux,
            'surface_flux_return_ratio_proxy': res_sponge.surface_flux_return_ratio_proxy,
            'surface_integrated_return_flux_ratio': res_sponge.surface_integrated_return_flux_ratio,
            'geometric_pre_arrival_step': res_sponge.geometric_pre_arrival_step,
            'geometric_peak_return_step': res_sponge.geometric_peak_return_step,
            'reference_wall_return_step': res_sponge.reference_wall_return_step,
            'reference_domain_free_of_wall_return': res_sponge.reference_domain_free_of_wall_return,
            'pre_arrival_difference_max': res_sponge.pre_arrival_difference_max,
            'is_simulation_setup_valid': res_sponge.is_simulation_setup_valid,
            'is_sponge_absorbed_to_tolerance': res_sponge.is_sponge_absorbed_to_tolerance,
            'is_sponge_benchmark_valid': res_sponge.is_sponge_benchmark_valid,
            'metric_definition_note': res_sponge.metric_definition_note,
            'diagnostic_note': res_sponge.diagnostic_note,
        },
        'sponge_absorption_control_sweep': [
            {
                'max_sigma': r.max_sigma,
                'reflected_peak': r.reflected_peak,
                'probe_local_amplitude_ratio_proxy': r.probe_local_amplitude_ratio_proxy,
                'probe_local_peak_squared_proxy': r.probe_local_peak_squared_proxy,
                'probe_amplitude_reflection_ratio': r.probe_amplitude_reflection_ratio,
                'probe_peak_squared_reflection_proxy': r.probe_peak_squared_reflection_proxy,
                'terminal_interior_reflected_energy_snapshot_proxy': r.terminal_interior_reflected_energy_snapshot_proxy,
                'peak_window_interior_reflected_energy_snapshot_proxy': r.peak_window_interior_reflected_energy_snapshot_proxy,
                'sponge_dissipated_energy_fraction': r.sponge_dissipated_energy_fraction,
                'remaining_total_energy_fraction': r.remaining_total_energy_fraction,
                'discrete_energy_budget_closure_error': r.discrete_energy_budget_closure_error,
                'surface_flux_return_ratio_proxy': r.surface_flux_return_ratio_proxy,
                'surface_integrated_return_flux_ratio': r.surface_integrated_return_flux_ratio,
                'description': r.description,
            }
            for r in ctrl_rows
        ],
        'sponge_reflection_parameter_sweep': {
            'description': 'Parameter sweep verifying reference-domain size invariance, dt refinement stability, observation window bounds, spatial dx refinement, and monotonic sponge-width absorption (P1-R3-F4, P1-R4-F1)',
            'rows': [
                {
                    'label': r.label,
                    'sweep_category': r.sweep_category,
                    'grid_size': r.grid_size,
                    'sponge_width': r.sponge_width,
                    'dx_m': r.dx_m,
                    'max_sigma': r.max_sigma,
                    'dt_factor': r.dt_factor,
                    'n_steps': r.n_steps,
                    'physical_observation_time_s': r.physical_observation_time_s,
                    'ref_grid_size': r.ref_grid_size,
                    'probe_local_peak_squared_proxy': r.probe_local_peak_squared_proxy,
                    'probe_peak_squared_reflection_proxy': r.probe_peak_squared_reflection_proxy,
                    'terminal_interior_reflected_energy_snapshot_proxy': r.terminal_interior_reflected_energy_snapshot_proxy,
                    'peak_window_interior_reflected_energy_snapshot_proxy': r.peak_window_interior_reflected_energy_snapshot_proxy,
                    'sponge_dissipated_energy_fraction': r.sponge_dissipated_energy_fraction,
                    'discrete_energy_budget_closure_error': r.discrete_energy_budget_closure_error,
                    'surface_flux_return_ratio_proxy': r.surface_flux_return_ratio_proxy,
                    'surface_integrated_return_flux_ratio': r.surface_integrated_return_flux_ratio,
                    'reference_wall_return_step': r.reference_wall_return_step,
                    'reference_domain_free_of_wall_return': r.reference_domain_free_of_wall_return,
                }
                for r in sweep.rows
            ],
            'reference_domain_invariance_diff': sweep.reference_domain_invariance_diff,
            'dt_refinement_relative_diff': sweep.dt_refinement_relative_diff,
            'monotonic_with_sponge_width': sweep.monotonic_with_sponge_width,
            'dx_refinement_consistent': sweep.dx_refinement_consistent,
            'observation_window_bounded': sweep.observation_window_bounded,
            'is_sweep_stable': sweep.is_sweep_stable,
            'diagnostic_note': sweep.diagnostic_note,
        },
        'fixed_window_late_early_probe_amplitude_proxy': {
            'description': 'Fixed-window late/early probe amplitude proxy (legacy metric, retained purely for historical audit comparison, P1-R2-F1, P1-R6-F2)',
            'parameters': {'grid_size': 48, 'sponge_width': 10, 'max_sigma': 3.0, 'n_steps': 70, 'arrival_window': 25},
            'incident_peak_amplitude': res_legacy.incident_peak_amplitude,
            'reflected_peak_amplitude': res_legacy.reflected_peak_amplitude,
            'amplitude_reflection_coefficient': res_legacy.amplitude_reflection_coefficient,
            'power_reflection_coefficient': res_legacy.power_reflection_coefficient,
            'initial_total_energy': res_legacy.initial_total_energy,
            'final_interior_energy': res_legacy.final_interior_energy,
            'interior_energy_retention_ratio': res_legacy.interior_energy_retention_ratio,
            'legacy_masked_proxy_ratio': res_legacy.masked_proxy_ratio,
            'is_absorbed_to_tolerance': res_legacy.is_absorbed_to_tolerance,
            'legacy_metric_invalid_for_absorption': res_legacy.legacy_metric_invalid_for_absorption,
            'epistemic_note': 'Measures outgoing pulse tail at step 25 without reference subtraction (~3.2% power ratio for all sigma including sigma=0); demonstrably invalid for certifying absorption.',
        },
        'two_material_energy_conservation_benchmark': {
            'description': 'Long-time discrete Hamiltonian conservation and actual terminal continuum energy across c1=1.0 -> c2=0.6 step interface (P1-R2-F4, P1-R3-F5)',
            'parameters': {'grid_size': 36, 'n_steps': 35, 'dx_m': 1.0, 'c1': 1.0, 'c2': 0.60, 'courant_factor': 0.85, 'tolerance_drift': 0.08},
            'initial_energy': res_energy.initial_energy,
            'final_energy': res_energy.final_energy,
            'terminal_continuum_signed_drift_ratio': res_energy.terminal_continuum_signed_drift_ratio,
            'max_discrete_hamiltonian_drift_ratio': res_energy.max_discrete_hamiltonian_drift_ratio,
            'max_continuum_diagnostic_drift_ratio': res_energy.max_continuum_diagnostic_drift_ratio,
            'initial_discrete_hamiltonian': res_energy.initial_discrete_hamiltonian,
            'final_discrete_hamiltonian': res_energy.final_discrete_hamiltonian,
            'is_conserved_to_tolerance': res_energy.is_conserved_to_tolerance,
            'diagnostic_note': res_energy.diagnostic_note,
        },
        'two_material_interface_transmission_benchmark': {
            'description': 'Analytical reflection & transmission benchmark across planar two-medium step interface with mesh refinement convergence (P1-R3-F3)',
            'interface_derivation_note': slow.interface_derivation_note,
            'high_to_low_speed_c1_1p0_to_c2_0p6': {
                'c1': slow.c1,
                'c2': slow.c2,
                'analytical_r_amp': slow.analytical_r_amp,
                'analytical_t_amp': slow.analytical_t_amp,
                'analytical_r_energy': slow.analytical_r_energy,
                'analytical_t_energy': slow.analytical_t_energy,
                'measured_r_amp_finest': slow.measured_r_amp,
                'measured_t_amp_finest': slow.measured_t_amp,
                'r_amp_abs_error_finest': slow.r_amp_abs_error,
                't_amp_abs_error_finest': slow.t_amp_abs_error,
                'measured_energy_partition_sum_finest': slow.measured_energy_partition_sum,
                'energy_partition_abs_error_finest': slow.energy_partition_abs_error,
                'errors_decrease_with_refinement': slow.errors_decrease_with_refinement,
                'is_consistent': slow.is_consistent,
                'refinement_rows': [
                    {
                        'dx': r.dx,
                        'nx': r.nx,
                        'n_steps': r.n_steps,
                        'measured_r_amp': r.measured_r_amp,
                        'measured_t_amp': r.measured_t_amp,
                        'r_amp_abs_error': r.r_amp_abs_error,
                        't_amp_abs_error': r.t_amp_abs_error,
                        'measured_energy_partition_sum': r.measured_energy_partition_sum,
                        'energy_partition_abs_error': r.energy_partition_abs_error,
                    }
                    for r in slow.refinement_rows
                ],
                'diagnostic_note': slow.diagnostic_note,
            },
            'low_to_high_speed_c1_0p6_to_c2_1p0': {
                'c1': fast.c1,
                'c2': fast.c2,
                'analytical_r_amp': fast.analytical_r_amp,
                'analytical_t_amp': fast.analytical_t_amp,
                'analytical_r_energy': fast.analytical_r_energy,
                'analytical_t_energy': fast.analytical_t_energy,
                'measured_r_amp_finest': fast.measured_r_amp,
                'measured_t_amp_finest': fast.measured_t_amp,
                'r_amp_abs_error_finest': fast.r_amp_abs_error,
                't_amp_abs_error_finest': fast.t_amp_abs_error,
                'measured_energy_partition_sum_finest': fast.measured_energy_partition_sum,
                'energy_partition_abs_error_finest': fast.energy_partition_abs_error,
                'errors_decrease_with_refinement': fast.errors_decrease_with_refinement,
                'is_consistent': fast.is_consistent,
                'refinement_rows': [
                    {
                        'dx': r.dx,
                        'nx': r.nx,
                        'n_steps': r.n_steps,
                        'measured_r_amp': r.measured_r_amp,
                        'measured_t_amp': r.measured_t_amp,
                        'r_amp_abs_error': r.r_amp_abs_error,
                        't_amp_abs_error': r.t_amp_abs_error,
                        'measured_energy_partition_sum': r.measured_energy_partition_sum,
                        'energy_partition_abs_error': r.energy_partition_abs_error,
                    }
                    for r in fast.refinement_rows
                ],
                'diagnostic_note': fast.diagnostic_note,
            },
        },
        'wave_grid_convergence_benchmark': {
            'description': 'Spatial and temporal second-order convergence against exact 3D standing analytical mode',
            'parameters': {'n_list': [17, 33, 65], 'T_s': 0.5, 'c0': 1.0, 'tolerance_min_order': 1.70},
            'rows': [
                {'n': r.n, 'dx': r.dx, 'dt': r.dt, 'n_steps': r.n_steps, 'linf_error': r.linf_error}
                for r in res_grid.rows
            ],
            'observed_orders': res_grid.observed_orders,
            'is_second_order_converged': res_grid.is_second_order_converged,
            'diagnostic_note': res_grid.diagnostic_note,
        },
        'materials_library_audit': [
            {
                'material': a.material_name,
                'wave_speed': a.wave_speed,
                'points_per_wavelength': a.points_per_wavelength,
                'status': a.status,
                'epistemic_label': a.epistemic_label,
                'diagnostic_note': a.diagnostic_note,
            }
            for a in [
                sw.audit_wavelength_resolution('Air (baseline)', 1.00),
                sw.audit_wavelength_resolution('Bismuth', 0.55),
                sw.audit_wavelength_resolution('Element 115 — Moscovium', 0.15),
                sw.audit_wavelength_resolution('Exotic metamaterial', 0.04),
            ]
        ],
    }


def render(
    output_png: str = 'electrostatics_baseline.png',
    output_json: str = 'electrostatics_manifest.json',
    config_2d: GroundedBoxConfig | None = None,
    study_probe_xy_m: tuple[float, float] = (0.0, 0.0),
    study_n_list: tuple[int, ...] = (41, 81, 101, 161),
) -> tuple[Path, Path]:
    cfg = config_2d or GroundedBoxConfig(n=101)
    result = electrode_pair_in_grounded_box(config=cfg)
    plate = parallel_plate_benchmark(1000.0, 0.001, 1e-4)
    study = electrode_pair_mesh_study(n_list=study_n_list, config=cfg, probe_xy_m=study_probe_xy_m)
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
