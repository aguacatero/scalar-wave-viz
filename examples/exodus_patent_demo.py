"""Exodus patent US11511891B2 FIGS. 4–8 reproduction demo and comparison visualizer.

Generates:
    - exodus_patent_comparison.png: 4-panel publication-grade scientific comparison
    - exodus_patent_manifest.json: JSON evidence manifest conforming to schema 1.2.0
"""

from __future__ import annotations

import os
import sys
import subprocess

# Ensure repo root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from exodus_hypothesis_evaluator import (
    evaluate_exodus_patent,
    generate_exodus_patent_manifest,
)
from exodus_patent_geometry import ExodusPatentParameters


def get_current_git_shas() -> tuple[str, str]:
    """Retrieve current branch HEAD SHA and checkout SHA."""
    pr_head = os.environ.get("PR_SOURCE_HEAD_SHA")
    try:
        checkout_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        checkout_sha = "UNKNOWN_CHECKOUT"
    head_sha = pr_head if pr_head else checkout_sha
    return head_sha, checkout_sha


def run_exodus_demo(
    output_image: str = "exodus_patent_comparison.png",
    output_manifest: str = "exodus_patent_manifest.json",
) -> None:
    print("Evaluating Exodus patent US11511891B2 FIGS. 4-8 embodiment...")
    params = ExodusPatentParameters(
        applied_voltage_v=25000.0,
        num_blades=1,
        dx_m=0.0005,
        dy_m=0.0005,
    )
    result = evaluate_exodus_patent(params)

    head_sha, checkout_sha = get_current_git_shas()
    manifest = generate_exodus_patent_manifest(
        result,
        source_head_sha=head_sha,
        tested_checkout_sha=checkout_sha,
        output_path=output_manifest,
    )
    print(f"Generated manifest: {output_manifest}")

    # Generate 4-panel comparison figure
    fig, axes = plt.subplots(2, 2, figsize=(14, 11), constrained_layout=True)
    fig.suptitle(
        "Exodus Patent US11511891B2 FIGS. 4–8: Conventional Maxwell-Stress (H0) vs Patent Prediction (H1)",
        fontsize=14,
        fontweight="bold",
    )

    # Panel A: 2D Potential and Electric Field Map
    ax_a = axes[0, 0]
    grid = result.grid
    x_mm = grid.x_coords_m * 1000.0
    y_mm = grid.y_coords_m * 1000.0
    v_kv = result.potential_v / 1000.0

    im = ax_a.imshow(
        v_kv,
        extent=[x_mm[0], x_mm[-1], y_mm[0], y_mm[-1]],
        origin="lower",
        cmap="viridis",
        aspect="auto",
    )
    cbar_a = fig.colorbar(im, ax=ax_a)
    cbar_a.set_label("Potential V (kV)")

    # Overlay streamplot of electric field
    stride_x = max(1, grid.nx // 30)
    stride_y = max(1, grid.ny // 30)
    xs_sub = x_mm[::stride_x]
    ys_sub = y_mm[::stride_y]
    ex_sub = result.e_field_x_v_per_m[::stride_y, ::stride_x]
    ey_sub = result.e_field_y_v_per_m[::stride_y, ::stride_x]

    # Mask streamplot inside conductors
    cond_sub = grid.fixed_mask[::stride_y, ::stride_x]
    ex_sub[cond_sub] = np.nan
    ey_sub[cond_sub] = np.nan

    try:
        ax_a.streamplot(
            xs_sub,
            ys_sub,
            ex_sub,
            ey_sub,
            color="white",
            density=0.8,
            linewidth=0.6,
            arrowsize=0.8,
        )
    except Exception:
        pass

    ax_a.set_title("Panel A: 2D Potential V(x,y) & Electric Field E", fontsize=11, fontweight="bold")
    ax_a.set_xlabel("X (mm) [Thrust Axis]")
    ax_a.set_ylabel("Y (mm) [Lateral]")
    ax_a.axvline(x=grid.x_coords_m[np.where(grid.mask_ground_102)[1][0]] * 1000, color="cyan", linestyle="--", alpha=0.6, label="Ground 102a")
    ax_a.legend(loc="upper right", fontsize=8)

    # Panel B: Side-by-side Force Accounting Bar Chart (H0 vs H1)
    ax_b = axes[0, 1]
    h0 = result.h0_ledger
    h1 = result.h1_prediction

    labels = ["H0: Blade (101)", "H0: Ground (102)", "H0: Enclosure", "H0: Net System", "H1: Patent Eq.11", "H1: 1/2 Factor"]
    forces_un = [
        h0.blade_force_x.force_3d_n * 1e6,
        h0.ground_force_x.force_3d_n * 1e6,
        h0.enclosure_box_force_x.force_3d_n * 1e6,
        h0.net_system_force_x.force_3d_n * 1e6,
        h1.predicted_force_3d_n * 1e6,
        h1.missing_half_factor_corrected_force_3d_n * 1e6,
    ]
    colors = ["#2563eb", "#3b82f6", "#64748b", "#16a34a" if abs(forces_un[3]) < 10 else "#dc2626", "#d97706", "#f59e0b"]

    bars = ax_b.bar(range(len(labels)), forces_un, color=colors, edgecolor="black", width=0.6)
    ax_b.set_xticks(range(len(labels)))
    ax_b.set_xticklabels(labels, rotation=25, ha="right", fontsize=9)
    ax_b.axhline(0, color="black", linewidth=0.8)
    ax_b.set_ylabel("Force along X (µN)")
    ax_b.set_title("Panel B: Force Accounting (H0 Equilibrium vs H1 Prediction)", fontsize=11, fontweight="bold")
    ax_b.grid(True, linestyle=":", alpha=0.5, axis="y")

    for bar, val in zip(bars, forces_un):
        y_pos = val + (5 if val >= 0 else -15)
        ax_b.text(bar.get_x() + bar.get_width() / 2, y_pos, f"{val:.1f} µN", ha="center", va="bottom", fontsize=8)

    # Panel C: Experimental Null Benchmark (Tajmar & Schreiber 2020) vs Patent Claim
    ax_c = axes[1, 0]
    exp_labels = ["H0 Net Equilibrium\n(Theory)", "Tajmar & Schreiber 2020\nHigh Vacuum (<10⁻⁵ mbar)", "Exodus Patent Claim\nAir Pendulum Stand (FIG. 22)"]
    exp_vals_un = [
        abs(h0.net_system_force_x.force_3d_n) * 1e6,
        result.controls.tajmar_schreiber_2020_null_bound_n * 1e6,
        result.controls.patent_claimed_force_n * 1e6,
    ]
    exp_colors = ["#16a34a", "#0284c7", "#e11d48"]
    exp_bars = ax_c.bar(range(len(exp_labels)), exp_vals_un, color=exp_colors, edgecolor="black", width=0.5)
    ax_c.set_xticks(range(len(exp_labels)))
    ax_c.set_xticklabels(exp_labels, fontsize=9)
    ax_c.set_yscale("log")
    ax_c.set_ylabel("Force Magnitude (µN) [Log Scale]")
    ax_c.set_title("Panel C: Independent Experimental Null Bound vs Patent Claim", fontsize=11, fontweight="bold")
    ax_c.grid(True, which="both", linestyle=":", alpha=0.5)

    for bar, val in zip(exp_bars, exp_vals_un):
        ax_c.text(bar.get_x() + bar.get_width() / 2, val * 1.3, f"{val:.2f} µN", ha="center", va="bottom", fontsize=8, fontweight="bold")

    # Panel D: Mesh Convergence Study (Refinement h -> 0)
    ax_d = axes[1, 1]
    dx_steps = [0.0010, 0.0008, 0.0006, 0.0005]
    residuals = []
    blade_forces = []

    for dxi in dx_steps:
        sub_p = ExodusPatentParameters(applied_voltage_v=25000.0, num_blades=1, dx_m=dxi, dy_m=dxi)
        sub_res = evaluate_exodus_patent(sub_p)
        residuals.append(sub_res.h0_ledger.residual_3d_n * 1e6)
        blade_forces.append(sub_res.h0_ledger.blade_force_x.force_3d_n * 1e6)

    h_mm = np.array(dx_steps) * 1000.0
    ax_d.plot(h_mm, residuals, "o-", color="#16a34a", label="Net Residual F_net (µN)")
    ax_d.set_xlabel("Grid Spacing h (mm)")
    ax_d.set_ylabel("Net Residual Force (µN)", color="#16a34a")
    ax_d.tick_params(axis="y", labelcolor="#16a34a")
    ax_d.grid(True, linestyle=":", alpha=0.5)

    ax_d2 = ax_d.twinx()
    ax_d2.plot(h_mm, blade_forces, "s--", color="#2563eb", label="Blade Force (µN)")
    ax_d2.set_ylabel("Internal Blade Force (µN)", color="#2563eb")
    ax_d2.tick_params(axis="y", labelcolor="#2563eb")

    ax_d.set_title("Panel D: Mesh Convergence (h -> 0)", fontsize=11, fontweight="bold")

    plt.savefig(output_image, dpi=200)
    plt.close()
    print(f"Generated comparison figure: {output_image}")


if __name__ == "__main__":
    run_exodus_demo()
