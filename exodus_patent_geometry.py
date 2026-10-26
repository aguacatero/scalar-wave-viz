"""Exodus patent US11511891B2 geometry specification, parameter audit, and discretization.

Primary source:
    United States Patent US 11,511,891 B2
    "System and method for generating forces using asymmetrical electrostatic pressure"
    Inventors: Andrew Neil Aurigema and Charles Raymond Buhler, IV
    Issued: November 29, 2022
    Official EPT Patent Collection: https://ept.space/patents/

Key figures:
    FIGS. 4–8: Single-stage asymmetrical electrostatic pressure force apparatus
    FIGS. 21–23: Multi-blade test article and reported force measurements
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np

# Permittivity of free space (CODATA 2018 / exact SI)
EPSILON_0 = 8.8541878128e-12  # F/m

INCHES_TO_METERS = 0.0254


@dataclass(frozen=True)
class ExodusPatentParameters:
    """Explicit parameters extracted directly from US11511891B2 text and drawings.

    Distinguishes directly cited parameters from unstated / missing parameters.
    """

    # Operating voltage
    applied_voltage_v: float = 25000.0  # Nominally +25 kVDC (up to +40 kVDC)

    # Geometry from FIG. 21 test article and FIGS. 4-8 single-stage embodiment
    num_blades: int = 1  # 1 for single-stage FIGS. 4-8; 9 for FIG. 21 test article
    blade_height_m: float = 0.25 * INCHES_TO_METERS  # Parameter P: 0.25 inches (6.35 mm)
    blade_pitch_m: float = 0.25 * INCHES_TO_METERS  # Parameter N: 0.25 inches (6.35 mm)
    blade_thickness_m: float = 0.05 * INCHES_TO_METERS  # Parameter T1: 0.05 inches (1.27 mm)
    blade_length_m: float = 4.0 * INCHES_TO_METERS  # Parameter Q: 4.0 inches (101.6 mm)
    gap_spacing_m: float = 0.25 * INCHES_TO_METERS  # Parameter S: gap between 100a and 102a (6.35 mm)

    # Ground plane dimensions (FIG. 21 test article)
    ground_plane_width_m: float = 2.0 * INCHES_TO_METERS  # 2.0 inches (50.8 mm) initial (or 3.0 in)
    ground_plane_thickness_m: float = 0.01 * INCHES_TO_METERS  # Thin copper tape backing (~0.25 mm)

    # Material properties
    dielectric_relative_permittivity: float = 1.0  # 1.0 for vacuum / air; ~3.8 for cured high-voltage epoxy

    # Outer grounded enclosure / environmental shield (Faraday cage / vacuum chamber walls)
    enclosure_margin_x_m: float = 0.025  # 25 mm margin in x beyond electrodes
    enclosure_margin_y_m: float = 0.025  # 25 mm margin in y beyond electrodes

    # Numerical grid spacing
    dx_m: float = 0.0005  # 0.5 mm spatial discretization
    dy_m: float = 0.0005  # 0.5 mm spatial discretization


@dataclass(frozen=True)
class SourcedParameterRecord:
    """Record of a geometric or operating parameter with its source citation."""
    symbol: str
    name: str
    patent_reference: str
    nominal_value_si: float
    units: str
    status: str  # "SOURCED_EXPLICIT", "SOURCED_RANGE", or "MISSING_IN_PATENT"
    notes: str


def get_patent_parameter_ledger() -> List[SourcedParameterRecord]:
    """Return the authoritative source-bound parameter audit for US11511891B2."""
    return [
        SourcedParameterRecord(
            symbol="V / Delta_V",
            name="Applied voltage difference",
            patent_reference="Col. 14 / FIG. 21-22 ('up to +40 kVDC', '+25 kV' test)",
            nominal_value_si=25000.0,
            units="V",
            status="SOURCED_EXPLICIT",
            notes="Nominal test voltage is +25 kVDC; maximum reported is +40 kVDC.",
        ),
        SourcedParameterRecord(
            symbol="P",
            name="Blade height (protrusion from distal 101a to proximal 100a)",
            patent_reference="FIG. 5 / FIG. 21 ('each blade being substantially 0.25 inches in height')",
            nominal_value_si=0.25 * INCHES_TO_METERS,
            units="m",
            status="SOURCED_EXPLICIT",
            notes="Blade height 6.35 mm.",
        ),
        SourcedParameterRecord(
            symbol="N",
            name="Blade spacing / pitch",
            patent_reference="FIG. 5 / FIG. 21 ('spaced 0.25 inches apart')",
            nominal_value_si=0.25 * INCHES_TO_METERS,
            units="m",
            status="SOURCED_EXPLICIT",
            notes="Blade center-to-edge or edge-to-edge spacing 6.35 mm.",
        ),
        SourcedParameterRecord(
            symbol="T1",
            name="Blade thickness",
            patent_reference="FIG. 5 / FIG. 21 ('The 0.05 inch thick blades 100')",
            nominal_value_si=0.05 * INCHES_TO_METERS,
            units="m",
            status="SOURCED_EXPLICIT",
            notes="Blade thickness 1.27 mm.",
        ),
        SourcedParameterRecord(
            symbol="Q / L_z",
            name="Blade length along z (extrusion dimension)",
            patent_reference="FIG. 5 / FIG. 21 ('each blade being substantially four inches in length')",
            nominal_value_si=4.0 * INCHES_TO_METERS,
            units="m",
            status="SOURCED_EXPLICIT",
            notes="Blade extrusion length 101.6 mm.",
        ),
        SourcedParameterRecord(
            symbol="S",
            name="Inter-electrode gap spacing (proximal 100a to ground 102a)",
            patent_reference="FIG. 5 / FIG. 21 ('gap between surfaces 100a and 102a was 0.25 inches')",
            nominal_value_si=0.25 * INCHES_TO_METERS,
            units="m",
            status="SOURCED_EXPLICIT",
            notes="Minimum inter-electrode gap 6.35 mm.",
        ),
        SourcedParameterRecord(
            symbol="S1",
            name="Distal separation distance (distal 101a to ground 102a)",
            patent_reference="FIGS. 2, 3, 5, 21 (S1 = S + P = 0.50 inches)",
            nominal_value_si=0.50 * INCHES_TO_METERS,
            units="m",
            status="SOURCED_EXPLICIT",
            notes="Distal electrode surface to ground plane distance 12.7 mm.",
        ),
        SourcedParameterRecord(
            symbol="epsilon_r",
            name="Dielectric material relative permittivity",
            patent_reference="Col. 14 / FIG. 21 ('filled with high voltage epoxy dielectric')",
            nominal_value_si=3.8,
            units="dimensionless",
            status="SOURCED_RANGE",
            notes="Generic 'high voltage epoxy dielectric'; typical epoxy range is 3.5 to 4.5.",
        ),
        SourcedParameterRecord(
            symbol="r_tip",
            name="Blade tip edge fillet radius",
            patent_reference="Not specified in patent text",
            nominal_value_si=0.0,
            units="m",
            status="MISSING_IN_PATENT",
            notes="Blade tip sharpness / curvature is omitted and not quantified in patent; modeled as rectangular blade edge.",
        ),
        SourcedParameterRecord(
            symbol="tan_delta",
            name="Dielectric loss tangent / conductivity",
            patent_reference="Not specified in patent text",
            nominal_value_si=0.0,
            units="dimensionless",
            status="MISSING_IN_PATENT",
            notes="Leakage current / dissipation factor omitted in patent specification.",
        ),
        SourcedParameterRecord(
            symbol="D_enclosure",
            name="Enclosure wall standoff distance",
            patent_reference="FIG. 21 ('transparent box lined with ITO-coated PET film that was grounded')",
            nominal_value_si=0.025,
            units="m",
            status="MISSING_IN_PATENT",
            notes="Exact dimensions and clearance of ITO-coated PET screening box are not reported in patent.",
        ),
        SourcedParameterRecord(
            symbol="wiring_geometry",
            name="High voltage lead and feedthrough configuration",
            patent_reference="FIG. 21 ('wire carrying V+ was connected... through the back of the device')",
            nominal_value_si=0.0,
            units="m",
            status="MISSING_IN_PATENT",
            notes="Lead wire diameter, insulation, and routing omitted; introduces unmodeled electrostatic coupling.",
        ),
    ]


@dataclass
class ExodusGrid2D:
    """Discretized 2D domain representing the Exodus patent electrode geometry.

    Orientation (matching patent FIGS. 4–8 coordinate system):
        - X axis: perpendicular to ground plane.
          Thrust vector Fx is asserted to act along +x (from ground 102a toward blade 101).
        - Y axis: lateral across blade width / array pitch.
        - Z axis: parallel to blade length (extrusion dimension Lz = 0.1016 m).
    """

    params: ExodusPatentParameters
    nx: int
    ny: int
    dx: float
    dy: float
    x_coords_m: np.ndarray
    y_coords_m: np.ndarray

    # Conductor masks (boolean arrays of shape (ny, nx))
    mask_blade_101: np.ndarray
    mask_ground_102: np.ndarray
    mask_enclosure_box: np.ndarray

    # Sub-surface masks on the blade electrode
    mask_proximal_100a: np.ndarray  # Tip surface closest to ground
    mask_distal_101a: np.ndarray    # Base plate surface farthest from ground
    mask_connecting_100b: np.ndarray  # Lateral blade flank surfaces

    # Relative permittivity map
    permittivity_map: np.ndarray

    # Prescribed Dirichlet potential (V)
    potential_bc: np.ndarray
    fixed_mask: np.ndarray

    @property
    def domain_size_x_m(self) -> float:
        return self.nx * self.dx

    @property
    def domain_size_y_m(self) -> float:
        return self.ny * self.dy


def build_exodus_2d_grid(params: Optional[ExodusPatentParameters] = None) -> ExodusGrid2D:
    """Construct the discretized 2D grid for the Exodus patent geometry.

    Follows FIGS. 4–8 single-stage embodiment (or multi-blade if num_blades > 1).
    Domain layout along X:
        x = 0: outer grounded shield left wall
        x = x_ground_left to x_ground_right: Ground electrode 102 (flat plate at V = 0)
        x = x_ground_right to x_blade_tip: Gap S (distance S = 6.35 mm)
        x = x_blade_tip: Proximal surface 100a (tip of blade 100)
        x = x_blade_tip to x_blade_base: Blade structure 100 of height P = 6.35 mm
        x = x_blade_base to x_blade_back: Distal base plate 101a of thickness T1 = 1.27 mm
        x = x_max: outer grounded shield right wall
    """
    if params is None:
        params = ExodusPatentParameters()

    dx = params.dx_m
    dy = params.dy_m

    # Structural dimensions
    ground_th = max(dx, 0.001)  # 1 mm ground plate
    gap_s = params.gap_spacing_m  # 6.35 mm
    blade_p = params.blade_height_m  # 6.35 mm
    base_th = params.blade_thickness_m  # 1.27 mm
    blade_th = params.blade_thickness_m  # 1.27 mm

    margin_x = params.enclosure_margin_x_m
    margin_y = params.enclosure_margin_y_m

    # Compute array width in Y
    num_blades = params.num_blades
    pitch = params.blade_pitch_m
    if num_blades <= 1:
        electrode_width_y = 0.030  # 30 mm for single blade section
    else:
        electrode_width_y = num_blades * pitch + 0.010

    total_size_x = margin_x + ground_th + gap_s + blade_p + base_th + margin_x
    total_size_y = margin_y + electrode_width_y + margin_y

    nx = int(math.ceil(total_size_x / dx))
    ny = int(math.ceil(total_size_y / dy))

    x_coords = np.linspace(0.0, (nx - 1) * dx, nx)
    y_coords = np.linspace(0.0, (ny - 1) * dy, ny)

    # Coordinates of features along X
    x_ground_left = margin_x
    x_ground_right = x_ground_left + ground_th

    x_blade_tip = x_ground_right + gap_s
    x_blade_base = x_blade_tip + blade_p
    x_blade_back = x_blade_base + base_th

    # Y center of the domain
    y_center = total_size_y / 2.0
    y_blade_min = y_center - (electrode_width_y / 2.0)
    y_blade_max = y_center + (electrode_width_y / 2.0)

    # Initialize masks
    mask_blade_101 = np.zeros((ny, nx), dtype=bool)
    mask_ground_102 = np.zeros((ny, nx), dtype=bool)
    mask_enclosure_box = np.zeros((ny, nx), dtype=bool)

    mask_proximal_100a = np.zeros((ny, nx), dtype=bool)
    mask_distal_101a = np.zeros((ny, nx), dtype=bool)
    mask_connecting_100b = np.zeros((ny, nx), dtype=bool)

    # 1. Enclosure box (Dirichlet ground V = 0 on boundary)
    mask_enclosure_box[0, :] = True
    mask_enclosure_box[-1, :] = True
    mask_enclosure_box[:, 0] = True
    mask_enclosure_box[:, -1] = True

    # 2. Ground electrode 102 (flat plate at V = 0)
    ix_ground_l = int(round(x_ground_left / dx))
    ix_ground_r = int(round(x_ground_right / dx))
    iy_ground_min = int(round((y_center - params.ground_plane_width_m / 2.0) / dy))
    iy_ground_max = int(round((y_center + params.ground_plane_width_m / 2.0) / dy))

    iy_ground_min = max(1, min(ny - 2, iy_ground_min))
    iy_ground_max = max(1, min(ny - 2, iy_ground_max))
    ix_ground_l = max(1, min(nx - 2, ix_ground_l))
    ix_ground_r = max(ix_ground_l + 1, min(nx - 2, ix_ground_r))

    mask_ground_102[iy_ground_min:iy_ground_max + 1, ix_ground_l:ix_ground_r + 1] = True

    # 3. First electrode 101: base plate (distal) + blade(s) (proximal)
    ix_blade_tip = int(round(x_blade_tip / dx))
    ix_blade_base = int(round(x_blade_base / dx))
    ix_blade_back = int(round(x_blade_back / dx))

    iy_base_min = int(round(y_blade_min / dy))
    iy_base_max = int(round(y_blade_max / dy))

    # Base plate (distal surface 101a)
    mask_blade_101[iy_base_min:iy_base_max + 1, ix_blade_base:ix_blade_back + 1] = True
    mask_distal_101a[iy_base_min:iy_base_max + 1, ix_blade_base:ix_blade_back + 1] = True

    # Blade(s)
    blade_half_th_idx = max(1, int(round((blade_th / 2.0) / dy)))
    blade_y_positions = []
    if num_blades <= 1:
        blade_y_positions.append(y_center)
    else:
        y_start = y_center - ((num_blades - 1) * pitch / 2.0)
        for b in range(num_blades):
            blade_y_positions.append(y_start + b * pitch)

    for by in blade_y_positions:
        iy_b = int(round(by / dy))
        iy_b_min = max(iy_base_min, iy_b - blade_half_th_idx)
        iy_b_max = min(iy_base_max, iy_b + blade_half_th_idx)

        # Full blade body
        mask_blade_101[iy_b_min:iy_b_max + 1, ix_blade_tip:ix_blade_base + 1] = True
        # Blade flank connecting surface 100b
        mask_connecting_100b[iy_b_min:iy_b_max + 1, ix_blade_tip + 1:ix_blade_base] = True
        # Blade tip proximal surface 100a
        mask_proximal_100a[iy_b_min:iy_b_max + 1, ix_blade_tip:ix_blade_tip + 1] = True

    # Ensure no overlap between conductors
    mask_blade_101 = mask_blade_101 & (~mask_ground_102) & (~mask_enclosure_box)
    mask_ground_102 = mask_ground_102 & (~mask_enclosure_box)

    # 4. Permittivity map: dielectric filled in gap/blade region or vacuum
    permittivity_map = np.ones((ny, nx), dtype=float)
    if params.dielectric_relative_permittivity > 1.0:
        # Dielectric epoxy occupies the inter-electrode region between ground and base plate
        ix_dielectric_start = ix_ground_r + 1
        ix_dielectric_end = ix_blade_back
        permittivity_map[iy_base_min:iy_base_max + 1, ix_dielectric_start:ix_dielectric_end + 1] = (
            params.dielectric_relative_permittivity
        )

    # 5. Boundary conditions
    potential_bc = np.zeros((ny, nx), dtype=float)
    potential_bc[mask_blade_101] = params.applied_voltage_v
    potential_bc[mask_ground_102] = 0.0
    potential_bc[mask_enclosure_box] = 0.0

    fixed_mask = mask_blade_101 | mask_ground_102 | mask_enclosure_box

    return ExodusGrid2D(
        params=params,
        nx=nx,
        ny=ny,
        dx=dx,
        dy=dy,
        x_coords_m=x_coords,
        y_coords_m=y_coords,
        mask_blade_101=mask_blade_101,
        mask_ground_102=mask_ground_102,
        mask_enclosure_box=mask_enclosure_box,
        mask_proximal_100a=mask_proximal_100a,
        mask_distal_101a=mask_distal_101a,
        mask_connecting_100b=mask_connecting_100b,
        permittivity_map=permittivity_map,
        potential_bc=potential_bc,
        fixed_mask=fixed_mask,
    )
