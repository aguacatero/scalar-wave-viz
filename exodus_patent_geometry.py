"""Exodus patent US11511891B2 geometry specification, parameter audit, and discretization.

Primary source:
    United States Patent US 11,511,891 B2
    "System and method for generating forces using asymmetrical electrostatic pressure"
    Inventors: Andrew Neil Aurigema and Charles Raymond Buhler, IV
    Issued: November 29, 2022
    Official EPT Patent Collection: https://ept.space/patents/

Key figures:
    FIGS. 4–8: Single-stage asymmetrical electrostatic pressure force apparatus schematic
    FIGS. 21–23: Multi-blade experimental test article and reported measurements
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Tuple
import numpy as np

# Permittivity of free space (CODATA 2018 / exact SI)
EPSILON_0 = 8.8541878128e-12  # F/m

INCHES_TO_METERS = 0.0254

ParameterStatus = Literal[
    "PATENT_EXPLICIT_VALUE",      # Stated explicitly in patent text or tables
    "PATENT_UNSPECIFIED_ESTIMATE",# Mentioned in patent without quantified value
    "MODELING_ASSUMPTION",        # Numerical domain / boundary setup assumption
    "PATENT_OMITTED_UNKNOWN",     # Omitted in patent specification; unknown
]


@dataclass(frozen=True)
class ExodusPatentParameters:
    """Explicit parameters for the Exodus patent US11511891B2 embodiments.

    Cleanly separates:
        1. FIGS. 4–8 single-stage schematic embodiment (num_blades = 1)
        2. FIG. 21 multi-blade experimental test article (num_blades = 9)
    """

    # Operating voltage
    applied_voltage_v: float = 25000.0  # Nominally +25 kVDC in FIG. 21-22 test (up to +40 kVDC)

    # Geometry from FIG. 21 test article and FIGS. 4-8 single-stage embodiment
    num_blades: int = 1  # 1 for FIGS. 4-8 single-stage; 9 for FIG. 21 test article
    blade_height_m: float = 0.25 * INCHES_TO_METERS  # Parameter P: 0.25 inches (6.35 mm)
    blade_pitch_m: float = 0.25 * INCHES_TO_METERS  # Parameter N: 0.25 inches (6.35 mm)
    blade_thickness_m: float = 0.05 * INCHES_TO_METERS  # Parameter T1: 0.05 inches (1.27 mm)
    blade_length_m: float = 4.0 * INCHES_TO_METERS  # Parameter Q / Lz: 4.0 inches (101.6 mm)
    gap_spacing_m: float = 0.25 * INCHES_TO_METERS  # Parameter S: gap between 100a and 102a (6.35 mm)

    # Base plate (distal electrode 101a backing)
    base_plate_thickness_m: float = 0.05 * INCHES_TO_METERS  # T1: 0.05 inches (1.27 mm)
    base_plate_width_m: float = 0.030  # Modeling assumption for single blade: 30 mm width

    # Ground plane dimensions (FIG. 21 test article)
    ground_plane_width_m: float = 2.0 * INCHES_TO_METERS  # 2.0 inches (50.8 mm) initial (or 3.0 in)
    ground_plane_thickness_m: float = 0.00025  # Copper tape backing (~0.25 mm)

    # Material properties
    # Note: FIG. 21 specifies "high voltage epoxy dielectric" without giving epsilon_r.
    # Vacuum baseline is 1.0; generic epoxy is ~3.5 to 4.5.
    dielectric_relative_permittivity: float = 1.0

    # Outer grounded shielding enclosure (Faraday cage / chamber walls)
    # Parameter U: enclosure clearance margin
    enclosure_margin_x_m: float = 0.025  # Parameter U: 25 mm margin along x
    enclosure_margin_y_m: float = 0.025  # Parameter U: 25 mm margin along y

    # Numerical grid spacing (2D)
    dx_m: float = 0.0005  # 0.5 mm spatial discretization
    dy_m: float = 0.0005  # 0.5 mm spatial discretization


@dataclass(frozen=True)
class SourcedParameterRecord:
    """Record of a geometric or operating parameter with its source citation and status."""
    symbol: str
    name: str
    patent_reference: str
    nominal_value_si: float
    units: str
    status: ParameterStatus
    notes: str


def get_patent_parameter_ledger() -> List[SourcedParameterRecord]:
    """Return the authoritative source-bound parameter audit for US11511891B2.

    Audits all 12 patent geometry symbols (T, T1, T2, M, N, O, P, Q, S, S1, U, V)
    cited in Column 11 and FIGS. 2-8, plus material and unmodeled parameters.
    """
    return [
        SourcedParameterRecord(
            symbol="V",
            name="Applied voltage difference Delta_V",
            patent_reference="Col. 14 / FIGS. 21-22 ('up to +40 kVDC', '+25 kV' test)",
            nominal_value_si=25000.0,
            units="V",
            status="PATENT_EXPLICIT_VALUE",
            notes="Nominal test voltage is +25 kVDC; power supply capability up to +40 kVDC.",
        ),
        SourcedParameterRecord(
            symbol="P",
            name="Blade height (protrusion from distal 101a to proximal 100a)",
            patent_reference="FIG. 5 / FIG. 21 ('each blade being substantially 0.25 inches in height')",
            nominal_value_si=0.25 * INCHES_TO_METERS,
            units="m",
            status="PATENT_EXPLICIT_VALUE",
            notes="Blade height 0.25 in (6.35 mm).",
        ),
        SourcedParameterRecord(
            symbol="N",
            name="Blade pitch / inter-blade spacing",
            patent_reference="FIG. 5 / FIG. 21 ('spaced 0.25 inches apart')",
            nominal_value_si=0.25 * INCHES_TO_METERS,
            units="m",
            status="PATENT_EXPLICIT_VALUE",
            notes="Blade center-to-edge or edge-to-edge spacing 0.25 in (6.35 mm).",
        ),
        SourcedParameterRecord(
            symbol="T1",
            name="Blade thickness / first electrode thickness",
            patent_reference="FIG. 5 / FIG. 21 ('The 0.05 inch thick blades 100')",
            nominal_value_si=0.05 * INCHES_TO_METERS,
            units="m",
            status="PATENT_EXPLICIT_VALUE",
            notes="Blade conductive thickness 0.05 in (1.27 mm).",
        ),
        SourcedParameterRecord(
            symbol="Q",
            name="Blade length along z (extrusion dimension Lz)",
            patent_reference="FIG. 5 / FIG. 21 ('each blade being substantially four inches in length')",
            nominal_value_si=4.0 * INCHES_TO_METERS,
            units="m",
            status="PATENT_EXPLICIT_VALUE",
            notes="Blade extrusion length 4.0 in (101.6 mm).",
        ),
        SourcedParameterRecord(
            symbol="S",
            name="Inter-electrode gap spacing (proximal 100a to ground 102a)",
            patent_reference="FIG. 5 / FIG. 21 ('gap between surfaces 100a and 102a was 0.25 inches')",
            nominal_value_si=0.25 * INCHES_TO_METERS,
            units="m",
            status="PATENT_EXPLICIT_VALUE",
            notes="Minimum inter-electrode gap 0.25 in (6.35 mm).",
        ),
        SourcedParameterRecord(
            symbol="S1",
            name="Distal separation distance (distal 101a to ground 102a)",
            patent_reference="FIGS. 2, 3, 5, 21 (S1 = S + P = 0.50 inches)",
            nominal_value_si=0.50 * INCHES_TO_METERS,
            units="m",
            status="PATENT_EXPLICIT_VALUE",
            notes="Distal base plate to ground plane distance 0.50 in (12.7 mm).",
        ),
        SourcedParameterRecord(
            symbol="T",
            name="Total apparatus thickness / depth along x",
            patent_reference="FIGS. 2, 3, 5 (T = S1 + base thickness)",
            nominal_value_si=0.55 * INCHES_TO_METERS,
            units="m",
            status="PATENT_EXPLICIT_VALUE",
            notes="Total core electrode thickness S + P + T1 = 0.55 in (13.97 mm).",
        ),
        SourcedParameterRecord(
            symbol="T2",
            name="Second electrode (ground plane) thickness",
            patent_reference="FIG. 21 ('copper tape that only covered the electrode area')",
            nominal_value_si=0.00025,
            units="m",
            status="PATENT_UNSPECIFIED_ESTIMATE",
            notes="Copper tape thickness not quantified in patent; estimated at 0.25 mm (0.01 in).",
        ),
        SourcedParameterRecord(
            symbol="M",
            name="Width of proximal electrode tip 100a",
            patent_reference="FIGS. 2, 3, 5 (rectangular blade tip width)",
            nominal_value_si=0.05 * INCHES_TO_METERS,
            units="m",
            status="PATENT_EXPLICIT_VALUE",
            notes="For rectangular blade, tip width equals blade thickness T1 = 1.27 mm.",
        ),
        SourcedParameterRecord(
            symbol="O",
            name="Lateral offset / overlap between electrodes",
            patent_reference="FIGS. 2, 3, 5",
            nominal_value_si=0.0,
            units="m",
            status="MODELING_ASSUMPTION",
            notes="Symmetric centered placement in nominal alignment; lateral offset O = 0.",
        ),
        SourcedParameterRecord(
            symbol="U",
            name="Dielectric extent / enclosure clearance margin",
            patent_reference="FIGS. 2, 3, 5, 21",
            nominal_value_si=0.025,
            units="m",
            status="MODELING_ASSUMPTION",
            notes="Clearance from electrodes to outer grounded shield box; assumed 25 mm.",
        ),
        SourcedParameterRecord(
            symbol="epsilon_r",
            name="Dielectric material relative permittivity",
            patent_reference="Col. 14 / FIG. 21 ('filled with high voltage epoxy dielectric')",
            nominal_value_si=3.8,
            units="dimensionless",
            status="PATENT_UNSPECIFIED_ESTIMATE",
            notes="Specific epoxy resin brand/grade omitted in patent; generic high-voltage epoxy range is 3.5 to 4.5.",
        ),
        SourcedParameterRecord(
            symbol="r_tip",
            name="Blade tip edge fillet radius",
            patent_reference="Not specified in patent text (omitted)",
            nominal_value_si=0.0,
            units="m",
            status="PATENT_OMITTED_UNKNOWN",
            notes="Blade tip sharpness / curvature radius omitted in patent; modeled as sharp rectangular corners.",
        ),
        SourcedParameterRecord(
            symbol="tan_delta",
            name="Dielectric loss tangent / bulk conductivity",
            patent_reference="Not specified in patent text (omitted)",
            nominal_value_si=0.0,
            units="dimensionless",
            status="PATENT_OMITTED_UNKNOWN",
            notes="Dielectric loss factor and DC leakage conductivity omitted in patent specification.",
        ),
        SourcedParameterRecord(
            symbol="D_enclosure",
            name="Enclosure wall standoff distance",
            patent_reference="FIG. 21 ('transparent box lined with ITO-coated PET film that was grounded')",
            nominal_value_si=0.025,
            units="m",
            status="PATENT_OMITTED_UNKNOWN",
            notes="Exact dimensions and clearance of ITO-coated PET box omitted in patent.",
        ),
        SourcedParameterRecord(
            symbol="wiring_geometry",
            name="High voltage lead wire routing and feedthroughs",
            patent_reference="FIG. 21 ('wire carrying V+ was connected... through the back of the device')",
            nominal_value_si=0.0,
            units="m",
            status="PATENT_OMITTED_UNKNOWN",
            notes="Lead wire diameter, insulation, and routing omitted in patent; introduces unmodeled electrostatic coupling.",
        ),
    ]


@dataclass(frozen=True)
class ConductorBoundaryFace:
    """An exterior boundary face of a conductor with exact coordinates and outward unit normals."""
    face_name: str
    conductor_id: str  # "blade_101", "ground_102", "enclosure_box"
    outward_normal: Tuple[float, float]  # (nx, ny)
    length_m: float  # Length / width in meters along the face
    # Arrays of sample point indices in dielectric/vacuum immediately adjacent to the face
    sample_ix_ext: np.ndarray
    sample_iy_ext: np.ndarray


@dataclass
class ExodusGrid2D:
    """Discretized 2D domain representing the Exodus patent electrode geometry."""

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

    # Explicit exterior boundary faces for rigorous surface traction integration
    boundary_faces: List[ConductorBoundaryFace]

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
    All dimensions match the authoritative parameter ledger.
    """
    if params is None:
        params = ExodusPatentParameters()

    dx = params.dx_m
    dy = params.dy_m

    # Structural dimensions from parameters
    ground_th = max(dx, params.ground_plane_thickness_m)
    gap_s = params.gap_spacing_m
    blade_p = params.blade_height_m
    base_th = params.base_plate_thickness_m
    blade_th = params.blade_thickness_m

    margin_x = params.enclosure_margin_x_m
    margin_y = params.enclosure_margin_y_m

    num_blades = params.num_blades
    pitch = params.blade_pitch_m
    if num_blades <= 1:
        electrode_width_y = params.base_plate_width_m
    else:
        electrode_width_y = num_blades * pitch + 0.010

    total_size_x = margin_x + ground_th + gap_s + blade_p + base_th + margin_x
    total_size_y = margin_y + max(electrode_width_y, params.ground_plane_width_m) + margin_y

    nx = int(math.ceil(total_size_x / dx))
    ny = int(math.ceil(total_size_y / dy))

    x_coords = np.linspace(0.0, (nx - 1) * dx, nx)
    y_coords = np.linspace(0.0, (ny - 1) * dy, ny)

    # Feature positions along X
    x_ground_left = margin_x
    x_ground_right = x_ground_left + ground_th

    x_blade_tip = x_ground_right + gap_s
    x_blade_base = x_blade_tip + blade_p
    x_blade_back = x_blade_base + base_th

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

    # 1. Enclosure box (grounded outer boundary)
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

    # Disjointness enforcement
    mask_blade_101 = mask_blade_101 & (~mask_ground_102) & (~mask_enclosure_box)
    mask_ground_102 = mask_ground_102 & (~mask_enclosure_box)

    # 4. Build explicit boundary face structures with material-side sampling
    boundary_faces: List[ConductorBoundaryFace] = []

    # Face 100a: proximal blade tip(s) facing ground (normal = -x)
    tip_sample_ix = []
    tip_sample_iy = []
    for by in blade_y_positions:
        iy_b = int(round(by / dy))
        iy_b_min = max(iy_base_min, iy_b - blade_half_th_idx)
        iy_b_max = min(iy_base_max, iy_b + blade_half_th_idx)
        for j in range(iy_b_min, iy_b_max + 1):
            tip_sample_iy.append(j)
            tip_sample_ix.append(max(0, ix_blade_tip - 1))

    total_tip_width = len(blade_y_positions) * (2 * blade_half_th_idx + 1) * dy
    boundary_faces.append(ConductorBoundaryFace(
        face_name="proximal_tip_100a",
        conductor_id="blade_101",
        outward_normal=(-1.0, 0.0),
        length_m=total_tip_width,
        sample_ix_ext=np.array(tip_sample_ix, dtype=int),
        sample_iy_ext=np.array(tip_sample_iy, dtype=int),
    ))

    # Face 101a: distal rear face of base plate (normal = +x)
    distal_sample_ix = []
    distal_sample_iy = []
    for j in range(iy_base_min, iy_base_max + 1):
        distal_sample_iy.append(j)
        distal_sample_ix.append(min(nx - 1, ix_blade_back + 1))

    distal_width = (iy_base_max - iy_base_min + 1) * dy
    boundary_faces.append(ConductorBoundaryFace(
        face_name="distal_rear_101a",
        conductor_id="blade_101",
        outward_normal=(1.0, 0.0),
        length_m=distal_width,
        sample_ix_ext=np.array(distal_sample_ix, dtype=int),
        sample_iy_ext=np.array(distal_sample_iy, dtype=int),
    ))

    # Ground front face 102a facing blade (normal = +x)
    ground_front_ix = []
    ground_front_iy = []
    for j in range(iy_ground_min, iy_ground_max + 1):
        ground_front_iy.append(j)
        ground_front_ix.append(min(nx - 1, ix_ground_r + 1))

    ground_width = (iy_ground_max - iy_ground_min + 1) * dy
    boundary_faces.append(ConductorBoundaryFace(
        face_name="ground_front_102a",
        conductor_id="ground_102",
        outward_normal=(1.0, 0.0),
        length_m=ground_width,
        sample_ix_ext=np.array(ground_front_ix, dtype=int),
        sample_iy_ext=np.array(ground_front_iy, dtype=int),
    ))

    # Ground rear face facing left enclosure wall (normal = -x)
    ground_rear_ix = []
    ground_rear_iy = []
    for j in range(iy_ground_min, iy_ground_max + 1):
        ground_rear_iy.append(j)
        ground_rear_ix.append(max(0, ix_ground_l - 1))

    boundary_faces.append(ConductorBoundaryFace(
        face_name="ground_rear_102b",
        conductor_id="ground_102",
        outward_normal=(-1.0, 0.0),
        length_m=ground_width,
        sample_ix_ext=np.array(ground_rear_ix, dtype=int),
        sample_iy_ext=np.array(ground_rear_iy, dtype=int),
    ))

    # 5. Permittivity map
    permittivity_map = np.ones((ny, nx), dtype=float)
    if params.dielectric_relative_permittivity > 1.0:
        # Dielectric epoxy occupies the inter-electrode region between ground and base plate
        ix_dielectric_start = ix_ground_r + 1
        ix_dielectric_end = ix_blade_back
        permittivity_map[iy_base_min:iy_base_max + 1, ix_dielectric_start:ix_dielectric_end + 1] = (
            params.dielectric_relative_permittivity
        )

    # 6. Boundary conditions
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
        boundary_faces=boundary_faces,
        permittivity_map=permittivity_map,
        potential_bc=potential_bc,
        fixed_mask=fixed_mask,
    )


def build_symmetric_control_grid(params: Optional[ExodusPatentParameters] = None) -> ExodusGrid2D:
    """Build a symmetric control geometry where two identical flat plates oppose each other.

    Used for adversarial control verification: symmetric capacitor must produce zero net force.
    """
    if params is None:
        params = ExodusPatentParameters()

    grid = build_exodus_2d_grid(params)

    # Clear asymmetric features
    grid.mask_blade_101.fill(False)
    grid.mask_ground_102.fill(False)
    grid.mask_proximal_100a.fill(False)
    grid.mask_distal_101a.fill(False)
    grid.mask_connecting_100b.fill(False)

    nx = grid.nx
    ny = grid.ny
    dx = grid.dx
    dy = grid.dy

    # Symmetric positioning along y
    plate_w_cells = int(round(params.ground_plane_width_m / dy))
    iy_min = max(2, (ny - plate_w_cells) // 2)
    iy_max = min(ny - 3, iy_min + plate_w_cells)

    # Symmetric positioning along x
    th_cells = max(1, int(round(params.base_plate_thickness_m / dx)))
    gap_cells = max(2, int(round(params.gap_spacing_m / dx)))

    mid_x = (nx - 1) / 2.0
    half_gap = gap_cells / 2.0

    # Ensure symmetric placement about grid center
    ix_g_r = int(round(mid_x - half_gap))
    ix_g_l = max(2, ix_g_r - th_cells)

    ix_b_l = int(round(mid_x + half_gap))
    ix_b_r = min(nx - 3, ix_b_l + th_cells)

    grid.mask_ground_102[iy_min:iy_max + 1, ix_g_l:ix_g_r + 1] = True
    grid.mask_blade_101[iy_min:iy_max + 1, ix_b_l:ix_b_r + 1] = True

    # Symmetrical excitation (+V/2 and -V/2) relative to grounded outer enclosure
    grid.potential_bc.fill(0.0)
    grid.potential_bc[grid.mask_blade_101] = params.applied_voltage_v / 2.0
    grid.potential_bc[grid.mask_ground_102] = -params.applied_voltage_v / 2.0
    grid.potential_bc[grid.mask_enclosure_box] = 0.0
    grid.fixed_mask = grid.mask_blade_101 | grid.mask_ground_102 | grid.mask_enclosure_box

    return grid
