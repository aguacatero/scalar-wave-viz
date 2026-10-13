"""Generate a static evidence-labeled conventional-electrostatics figure.

From repository root: python examples/electrostatics_demo.py
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from electrostatics_baseline import (electrode_pair_in_grounded_box,
                                     parallel_plate_benchmark)


def display_field_data(result):
    """Mask fixed-potential conductors and show directional arrows only in vacuum.

    Gradient samples on/inside fixed conducting cells are not trustworthy
    physical interior fields. Vector lengths are normalized for direction;
    the color scale, not arrow length, displays field magnitude.
    """
    magnitude = np.hypot(result.ex_v_per_m, result.ey_v_per_m)
    hidden = result.fixed_mask
    ux = np.divide(result.ex_v_per_m, magnitude, out=np.zeros_like(magnitude),
                   where=magnitude > 0)
    uy = np.divide(result.ey_v_per_m, magnitude, out=np.zeros_like(magnitude),
                   where=magnitude > 0)
    return (np.ma.array(magnitude, mask=hidden),
            np.ma.array(ux, mask=hidden | (magnitude == 0)),
            np.ma.array(uy, mask=hidden | (magnitude == 0)))


def render(output: str = 'electrostatics_baseline.png') -> Path:
    result = electrode_pair_in_grounded_box(n=101)
    plate = parallel_plate_benchmark(1000.0, 0.001, 1e-4)
    n = result.potential_v.shape[0]
    length_m = result.grid_spacing_m * (n-1)
    coords_mm = np.linspace(-length_m/2, length_m/2, n)*1000
    x, y = np.meshgrid(coords_mm, coords_mm, indexing='ij')
    fig, axes = plt.subplots(1,3,figsize=(14,4.8), layout='constrained')
    image = axes[0].contourf(x, y, result.potential_v, levels=25, cmap='coolwarm')
    fig.colorbar(image, ax=axes[0],label='Potential (V)')
    axes[0].set(title='A · Dirichlet potential',xlabel='x (mm)',ylabel='y (mm)',aspect='equal')
    field, unit_ex, unit_ey = display_field_data(result)
    image2 = axes[1].contourf(x, y, field/1000, levels=25, cmap='viridis')
    fig.colorbar(image2, ax=axes[1], label='|E| (kV/m), vacuum only')
    stride = 8
    axes[1].quiver(x[::stride, ::stride], y[::stride, ::stride],
                   unit_ex[::stride, ::stride], unit_ey[::stride, ::stride],
                   color='white', alpha=0.7, scale_units='xy', scale=1.0)
    for axis, color in ((axes[0], 'black'), (axes[1], 'white')):
        axis.contour(x, y, result.fixed_mask.astype(float), levels=[0.5],
                     colors=[color], linewidths=0.9)
    axes[1].set(title='B · Vacuum field (arrows = direction only)',
                xlabel='x (mm)', ylabel='y (mm)', aspect='equal')
    # Analytic forces are from a SEPARATE ideal parallel-plate example.
    micro_n = 1e6
    axes[2].bar(['Positive plate', 'Negative plate', 'Net pair'],
                [plate.force_on_positive_plate_n*micro_n,
                 plate.force_on_negative_plate_n*micro_n,
                 plate.net_pair_force_n*micro_n])
    axes[2].axhline(0,color='black',lw=0.7)
    axes[2].tick_params(axis='x',rotation=20)
    axes[2].set(title='C · Independent plate forces',ylabel='Signed force (µN)')
    fig.suptitle('CONVENTIONAL ELECTROSTATICS · 2D grounded enclosure + separate ideal-plate check\n'
                 'No anomalous thrust model · Not patent geometry · Not experimental data',fontsize=11)
    dest=Path(output)
    fig.savefig(dest,dpi=160)
    plt.close(fig)
    return dest


if __name__ == '__main__':
    print('Wrote',render())
