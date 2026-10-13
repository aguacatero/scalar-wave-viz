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
    field = np.hypot(result.ex_v_per_m,result.ey_v_per_m)
    image2 = axes[1].contourf(x,y,field/1000,levels=25,cmap='viridis')
    fig.colorbar(image2, ax=axes[1],label='|E| (kV/m)')
    stride = 8
    axes[1].quiver(x[::stride,::stride],y[::stride,::stride],
                   result.ex_v_per_m[::stride,::stride],result.ey_v_per_m[::stride,::stride],
                   color='white',alpha=0.65)
    axes[1].set(title='B · Electric field',xlabel='x (mm)',ylabel='y (mm)',aspect='equal')
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
