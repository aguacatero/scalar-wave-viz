"""Exodus patent US11511891B2 geometry specification, parameter audit, and discretization.

Primary source:
    United States Patent US 11,511,891 B2
    "System and method for generating forces using asymmetrical electrostatic pressure"
    Inventors: Andrew Neil Aurigema and Charles Raymond Buhler, IV
    Issued: November 29, 2022
    Official EPT Patent Collection: https://ept.space/patents/

Key figures separated in this module:
    1. FIGS. 4–8: Single-stage asymmetrical electrostatic pressure apparatus schematic (num_blades = 1)
    2. FIGS. 21–23: Nine-blade epoxy-potted experimental test article (num_blades = 9)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import List, Literal, Optional, Tuple
import numpy as np

# Permittivity of free space (CODATA 2018 / exact SI)
EPSILON_0 = 8.8541878128e-12  # F/m

INCHES_TO_METERS = 0.0254

ParameterStatus = Literal[
    "PATENT_EXPLICIT_VALUE",             # Stated explicitly with numerical value in US11511891B2
    "DERIVED_FROM_PATENT",               # Derived algebraically from explicit patent dimensions (e.g. S1 = S + P)
    "EXTERNAL_ESTIMATE_FOR_UNSPECIFIED", # External engineering estimate where patent names feature without value
    "MODELING_ASSUMPTION",               # Numerical domain / boundary setup assumption
    "PATENT_OMITTED_UNKNOWN",            # Omitted in patent specification; unknown / unmodeled
]


@dataclass(frozen=True)
class ExodusPatentParameters:
    """Explicit parameters for the Exodus patent US11511891B2 embodiments.

    Cleanly separates:
        1. FIGS. 4–8 single-stage schematic embodiment (ExodusPatentParameters.figs_4_to_8_schematic)
        2. FIG. 21 multi-blade experimental test article (ExodusPatentParameters.fig_21_nine_blade_article)
    """

    embodiment_id: str = "FIGS_4_TO_8_SINGLE_STAGE_SCHEMATIC"

    # Operating voltage (Symbol V)
    applied_voltage_v: float = 25000.0  # Nominally +25 kVDC in FIG. 21-22 test (power supply up to +40 kVDC)

    # Geometry from FIG. 5 / FIG. 21
    num_blades: int = 1  # 1 for FIGS. 4-8 single-stage schematic; 9 for FIG. 21 test article
    blade_height_m: float = 0.25 * INCHES_TO_METERS     # Symbol P: 0.25 inches (6.35 mm)
    blade_pitch_m: float = 0.25 * INCHES_TO_METERS      # Symbol N: 0.25 inches (6.35 mm)
    blade_thickness_m: float = 0.05 * INCHES_TO_METERS  # Symbol T1: 0.05 inches (1.27 mm)
    blade_length_m: float = 4.0 * INCHES_TO_METERS      # Symbol Q / Lz: 4.0 inches (101.6 mm)
    gap_spacing_m: float = 0.25 * INCHES_TO_METERS       # Symbol S: gap between 100a and 102a (6.35 mm)

    # Base plate (distal electrode 101a backing)
    base_plate_thickness_m: float = 0.05 * INCHES_TO_METERS  # T1: 0.05 inches (1.27 mm)
    base_plate_width_m: float = 0.030  # Modeling assumption for single-blade section width: 30 mm

    # Ground plane dimensions (Symbol T2 & width)
    ground_plane_width_m: float = 2.0 * INCHES_TO_METERS  # 2.0 inches (50.8 mm) initial in FIG. 21 (or 3.0 in)
    ground_plane_thickness_m: float = 0.00025  # Symbol T2: Copper tape backing estimate (~0.25 mm)

    # Lateral offset (Symbol O)
    lateral_offset_m: float = 0.0  # Symbol O: lateral offset between electrodes (0.0 for centered)

    # Material properties
    # Note: FIG. 21 specifies "high voltage epoxy dielectric" without giving epsilon_r.
    # Single-stage schematic baseline is vacuum (1.0); generic potting epoxy is ~3.8.
    dielectric_relative_permittivity: float = 1.0

    # Outer grounded shielding enclosure (Faraday cage / chamber walls)
    # Symbol U: enclosure clearance margin
    enclosure_margin_x_m: float = 0.025  # Symbol U: 25 mm margin along x
    enclosure_margin_y_m: float = 0.025  # Symbol U: 25 mm margin along y
    enclosure_margin_left_x_m: Optional[float] = None   # Optional asymmetric left wall clearance
    enclosure_margin_right_x_m: Optional[float] = None  # Optional asymmetric right wall clearance
    enclosure_margin_z_m: float = 0.020  # Symbol U_z: 20 mm end clearance margin along z

    # Numerical grid spacing (2D)
    dx_m: float = 0.0005  # 0.5 mm spatial discretization
    dy_m: float = 0.0005  # 0.5 mm spatial discretization

    @property
    def distal_separation_s1_m(self) -> float:
        """Derived parameter S1 = S + P (distance from ground 102a to distal base front)."""
        return self.gap_spacing_m + self.blade_height_m

    @property
    def total_core_thickness_t_m(self) -> float:
        """Derived parameter T = S + P + base_plate_thickness_m."""
        return self.gap_spacing_m + self.blade_height_m + self.base_plate_thickness_m

    @property
    def proximal_tip_width_m_symbol(self) -> float:
        """Derived parameter M: width of each proximal blade tip 100a (equals T1 for rectangular blade)."""
        return self.blade_thickness_m

    @classmethod
    def figs_4_to_8_schematic(cls, **overrides) -> "ExodusPatentParameters":
        """Return parameters for the FIGS. 4–8 single-stage schematic embodiment."""
        defaults = dict(
            embodiment_id="FIGS_4_TO_8_SINGLE_STAGE_SCHEMATIC",
            applied_voltage_v=25000.0,
            num_blades=1,
            dielectric_relative_permittivity=1.0,
            base_plate_width_m=0.030,
            ground_plane_width_m=2.0 * INCHES_TO_METERS,
        )
        defaults.update(overrides)
        return cls(**defaults)

    @classmethod
    def fig_21_nine_blade_article(cls, **overrides) -> "ExodusPatentParameters":
        """Return parameters for the FIG. 21 nine-blade epoxy-potted test article."""
        defaults = dict(
            embodiment_id="FIG_21_NINE_BLADE_EPOXY_TEST_ARTICLE",
            applied_voltage_v=25000.0,
            num_blades=9,
            dielectric_relative_permittivity=3.8,
            base_plate_width_m=9 * 0.25 * INCHES_TO_METERS,  # 2.25 inches (57.15 mm) span
            ground_plane_width_m=2.0 * INCHES_TO_METERS,     # 2.0 inches (50.8 mm) initial copper tape
        )
        defaults.update(overrides)
        return cls(**defaults)


@dataclass(frozen=True)
class SourcedParameterRecord:
    """Record of a geometric or operating parameter with its source citation, status, and consumed value."""
    symbol: str
    name: str
    patent_reference: str
    nominal_value_si: float
    consumed_value_si: float
    units: str
    status: ParameterStatus
    notes: str


def get_patent_parameter_ledger(
    params: Optional[ExodusPatentParameters] = None,
) -> List[SourcedParameterRecord]:
    """Return the authoritative source-bound parameter audit for US11511891B2.

    Audits all 12 patent geometry symbols (T, T1, T2, M, N, O, P, Q, S, S1, U, V)
    cited in Column 11 and FIGS. 2-8, plus material and unmodeled parameters.
    Synchronizes consumed_value_si directly with the active ExodusPatentParameters instance.
    """
    if params is None:
        params = ExodusPatentParameters()

    return [
        SourcedParameterRecord(
            symbol="V",
            name="Applied voltage difference Delta_V",
            patent_reference="Col. 14 / FIGS. 21-22 ('up to +40 kVDC', '+25 kV' test)",
            nominal_value_si=25000.0,
            consumed_value_si=float(params.applied_voltage_v),
            units="V",
            status="PATENT_EXPLICIT_VALUE",
            notes="Nominal test voltage is +25 kVDC; power supply capability up to +40 kVDC.",
        ),
        SourcedParameterRecord(
            symbol="P",
            name="Blade height (protrusion from distal base to proximal tip 100a)",
            patent_reference="FIG. 5 / FIG. 21 ('each blade being substantially 0.25 inches in height')",
            nominal_value_si=0.25 * INCHES_TO_METERS,
            consumed_value_si=float(params.blade_height_m),
            units="m",
            status="PATENT_EXPLICIT_VALUE",
            notes="Blade height 0.25 in (6.35 mm).",
        ),
        SourcedParameterRecord(
            symbol="N",
            name="Blade pitch / inter-blade spacing",
            patent_reference="FIG. 5 / FIG. 21 ('spaced 0.25 inches apart')",
            nominal_value_si=0.25 * INCHES_TO_METERS,
            consumed_value_si=float(params.blade_pitch_m),
            units="m",
            status="PATENT_EXPLICIT_VALUE",
            notes="Blade spacing 0.25 in (6.35 mm) in multi-blade embodiment.",
        ),
        SourcedParameterRecord(
            symbol="T1",
            name="Blade thickness / first electrode thickness",
            patent_reference="FIG. 5 / FIG. 21 ('The 0.05 inch thick blades 100')",
            nominal_value_si=0.05 * INCHES_TO_METERS,
            consumed_value_si=float(params.blade_thickness_m),
            units="m",
            status="PATENT_EXPLICIT_VALUE",
            notes="Blade conductive thickness 0.05 in (1.27 mm).",
        ),
        SourcedParameterRecord(
            symbol="Q",
            name="Blade length along z (extrusion dimension Lz)",
            patent_reference="FIG. 5 / FIG. 21 ('each blade being substantially four inches in length')",
            nominal_value_si=4.0 * INCHES_TO_METERS,
            consumed_value_si=float(params.blade_length_m),
            units="m",
            status="PATENT_EXPLICIT_VALUE",
            notes="Blade length 4.0 in (101.6 mm).",
        ),
        SourcedParameterRecord(
            symbol="S",
            name="Inter-electrode gap spacing (proximal 100a to ground 102a)",
            patent_reference="FIG. 5 / FIG. 21 ('gap between surfaces 100a and 102a was 0.25 inches')",
            nominal_value_si=0.25 * INCHES_TO_METERS,
            consumed_value_si=float(params.gap_spacing_m),
            units="m",
            status="PATENT_EXPLICIT_VALUE",
            notes="Minimum inter-electrode gap 0.25 in (6.35 mm).",
        ),
        SourcedParameterRecord(
            symbol="S1",
            name="Distal separation distance (distal base front to ground 102a)",
            patent_reference="FIGS. 2, 3, 5, 21 (Derived relation S1 = S + P = 0.50 inches)",
            nominal_value_si=0.50 * INCHES_TO_METERS,
            consumed_value_si=float(params.distal_separation_s1_m),
            units="m",
            status="DERIVED_FROM_PATENT",
            notes="Derived sum of gap S (0.25 in) and blade height P (0.25 in) = 0.50 in (12.7 mm).",
        ),
        SourcedParameterRecord(
            symbol="T",
            name="Total electrode assembly core depth along x",
            patent_reference="FIGS. 2, 3, 5 (Derived relation T = S1 + T1 = 0.55 inches)",
            nominal_value_si=0.55 * INCHES_TO_METERS,
            consumed_value_si=float(params.total_core_thickness_t_m),
            units="m",
            status="DERIVED_FROM_PATENT",
            notes="Derived core depth S + P + T1 = 0.55 in (13.97 mm).",
        ),
        SourcedParameterRecord(
            symbol="T2",
            name="Second electrode (ground plane) thickness",
            patent_reference="FIG. 21 ('copper tape that only covered the electrode area')",
            nominal_value_si=0.00025,
            consumed_value_si=float(params.ground_plane_thickness_m),
            units="m",
            status="EXTERNAL_ESTIMATE_FOR_UNSPECIFIED",
            notes="Copper tape thickness not quantified in patent text; external engineering estimate 0.25 mm.",
        ),
        SourcedParameterRecord(
            symbol="M",
            name="Width of proximal electrode tip 100a",
            patent_reference="FIGS. 2, 3, 5 (Derived from rectangular blade thickness M = T1)",
            nominal_value_si=0.05 * INCHES_TO_METERS,
            consumed_value_si=float(params.proximal_tip_width_m_symbol),
            units="m",
            status="DERIVED_FROM_PATENT",
            notes="For rectangular blade profile without taper, proximal tip width M equals T1 = 1.27 mm.",
        ),
        SourcedParameterRecord(
            symbol="O",
            name="Lateral offset / overlap between electrodes",
            patent_reference="FIGS. 2, 3, 5 (Symbol O in schematic diagrams)",
            nominal_value_si=0.0,
            consumed_value_si=float(params.lateral_offset_m),
            units="m",
            status="MODELING_ASSUMPTION",
            notes="Symmetric centered alignment assumed in baseline (O = 0).",
        ),
        SourcedParameterRecord(
            symbol="U",
            name="Dielectric extent / enclosure clearance margin",
            patent_reference="FIGS. 2, 3, 5, 21 (Symbol U margin)",
            nominal_value_si=0.025,
            consumed_value_si=float(params.enclosure_margin_x_m),
            units="m",
            status="MODELING_ASSUMPTION",
            notes="Clearance from electrodes to outer grounded shield box; modeled at 25 mm (and swept in sensitivity studies).",
        ),
        SourcedParameterRecord(
            symbol="W_base",
            name="Base plate lateral width (distal electrode 101a width)",
            patent_reference="FIGS. 4-8 single-stage schematic / FIG. 21 9-blade span",
            nominal_value_si=0.030,
            consumed_value_si=float(params.base_plate_width_m),
            units="m",
            status="MODELING_ASSUMPTION",
            notes="30 mm width assumed for single-blade FIGS. 4-8 schematic; 57.15 mm (2.25 in) for 9-blade FIG. 21 article.",
        ),
        SourcedParameterRecord(
            symbol="epsilon_r",
            name="Dielectric material relative permittivity",
            patent_reference="Col. 14 / FIG. 21 ('filled with high voltage epoxy dielectric')",
            nominal_value_si=3.8,
            consumed_value_si=float(params.dielectric_relative_permittivity),
            units="dimensionless",
            status="EXTERNAL_ESTIMATE_FOR_UNSPECIFIED",
            notes="Specific epoxy formulation omitted in patent; generic high-voltage potting epoxy is ~3.5-4.5 (1.0 in vacuum schematic).",
        ),
        SourcedParameterRecord(
            symbol="r_tip",
            name="Blade tip edge fillet radius",
            patent_reference="Not specified in patent text (omitted)",
            nominal_value_si=0.0,
            consumed_value_si=0.0,
            units="m",
            status="PATENT_OMITTED_UNKNOWN",
            notes="Blade tip sharpness / curvature radius omitted in patent; modeled as rectangular grid cells.",
        ),
        SourcedParameterRecord(
            symbol="tan_delta",
            name="Dielectric loss tangent / bulk DC leakage conductivity",
            patent_reference="Not specified in patent text (omitted)",
            nominal_value_si=0.0,
            consumed_value_si=0.0,
            units="dimensionless",
            status="PATENT_OMITTED_UNKNOWN",
            notes="Dielectric loss factor and volume/surface conductivity omitted in patent specification.",
        ),
        SourcedParameterRecord(
            symbol="D_enclosure",
            name="ITO-lined box dimensions and pendulum stand clearances",
            patent_reference="FIG. 21 ('transparent box lined with ITO-coated PET film that was grounded')",
            nominal_value_si=0.025,
            consumed_value_si=float(params.enclosure_margin_x_m),
            units="m",
            status="PATENT_OMITTED_UNKNOWN",
            notes="Exact dimensions and clearances of ITO-coated PET box and plastic bag omitted in patent.",
        ),
        SourcedParameterRecord(
            symbol="wiring_geometry",
            name="High voltage lead wire routing and feedthroughs",
            patent_reference="FIG. 21 ('wire carrying V+ was connected... through the back of the device')",
            nominal_value_si=0.0,
            consumed_value_si=0.0,
            units="m",
            status="PATENT_OMITTED_UNKNOWN",
            notes="Lead wire diameter, stiffness, insulation, and routing omitted in patent.",
        ),
    ]


@dataclass(frozen=True)
class ConductorBoundaryFace:
    """An exterior boundary face of a conductor with exact coordinates and outward unit normals."""
    face_name: str
    conductor_id: str  # "blade_101", "ground_102", "enclosure_box"
    outward_normal: Tuple[float, float]  # (nx, ny) pointing into dielectric/vacuum
    length_m: float  # Physical length / width in meters along the face
    # Arrays of conductor surface cell indices
    conductor_ix: np.ndarray
    conductor_iy: np.ndarray
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

    # Explicit 1-cell-thick exterior surface masks on the blade electrode
    mask_proximal_100a: np.ndarray    # Exterior tip surface closest to ground
    mask_distal_101a: np.ndarray      # Exterior rear backing surface farthest from ground
    mask_connecting_100b: np.ndarray  # Exterior lateral flank and shoulder surfaces

    # Explicit exterior boundary faces for rigorous surface traction integration
    boundary_faces: List[ConductorBoundaryFace]

    # Relative permittivity map
    permittivity_map: np.ndarray
    mask_dielectric_region: np.ndarray

    # Prescribed Dirichlet potential (V)
    potential_bc: np.ndarray
    fixed_mask: np.ndarray

    # Geometry discretization fidelity tracking (target vs actual grid values)
    target_tip_width_m: float = 0.00127
    discretized_tip_width_m: float = 0.00127
    tip_width_discretization_ratio: float = 1.0
    target_gap_m: float = 0.00635
    discretized_gap_m: float = 0.00635
    gap_discretization_ratio: float = 1.0
    target_blade_height_m: float = 0.00635
    discretized_blade_height_m: float = 0.00635
    blade_height_discretization_ratio: float = 1.0

    @property
    def domain_size_x_m(self) -> float:
        return self.nx * self.dx

    @property
    def domain_size_y_m(self) -> float:
        return self.ny * self.dy


def build_exodus_2d_grid(params: Optional[ExodusPatentParameters] = None) -> ExodusGrid2D:
    """Construct the discretized 2D grid for the Exodus patent geometry.

    Supports both FIGS. 4–8 single-stage schematic (num_blades = 1) and
    FIG. 21 multi-blade test article (num_blades = 9).
    """
    if params is None:
        params = ExodusPatentParameters()

    dx = params.dx_m
    dy = params.dy_m

    margin_left_x = (
        params.enclosure_margin_left_x_m
        if params.enclosure_margin_left_x_m is not None
        else params.enclosure_margin_x_m
    )
    margin_right_x = (
        params.enclosure_margin_right_x_m
        if params.enclosure_margin_right_x_m is not None
        else params.enclosure_margin_x_m
    )
    margin_y = params.enclosure_margin_y_m

    # Discrete cell counts for structural features along X (no fencepost bias)
    n_margin_left = max(3, int(round(margin_left_x / dx)))
    n_margin_right = max(3, int(round(margin_right_x / dx)))
    n_ground_th = max(1, int(round(params.ground_plane_thickness_m / dx)))
    n_gap = max(2, int(round(params.gap_spacing_m / dx)))
    n_blade_p = max(2, int(round(params.blade_height_m / dx)))
    n_base_th = max(1, int(round(params.base_plate_thickness_m / dx)))

    num_blades = params.num_blades
    pitch = params.blade_pitch_m
    if num_blades <= 1:
        electrode_width_y = params.base_plate_width_m
    else:
        electrode_width_y = max(
            params.base_plate_width_m,
            (num_blades - 1) * pitch + params.blade_thickness_m + 0.004,
        )

    n_margin_y = max(3, int(round(margin_y / dy)))
    n_ground_y = max(2, int(round(params.ground_plane_width_m / dy)))
    n_base_y = max(2, int(round(electrode_width_y / dy)))

    nx = n_margin_left + n_ground_th + n_gap + n_blade_p + n_base_th + n_margin_right + 2
    ny = 2 * n_margin_y + max(n_ground_y, n_base_y) + 2

    x_coords = np.arange(nx, dtype=float) * dx
    y_coords = np.arange(ny, dtype=float) * dy

    # Feature index bounds along X (inclusive: [ix_start, ix_end] has exactly n cells)
    ix_ground_l = n_margin_left
    ix_ground_r = ix_ground_l + n_ground_th - 1

    ix_blade_tip = ix_ground_r + n_gap + 1
    ix_blade_base = ix_blade_tip + n_blade_p
    ix_blade_back = ix_blade_base + n_base_th - 1

    # Feature index bounds along Y (inclusive: [iy_min, iy_max] has exactly n_y cells)
    iy_center = ny // 2
    n_offset_y = int(round(params.lateral_offset_m / dy))

    iy_ground_min = max(2, iy_center - (n_ground_y // 2))
    iy_ground_max = min(ny - 3, iy_ground_min + n_ground_y - 1)

    iy_base_min = max(2, (iy_center + n_offset_y) - (n_base_y // 2))
    iy_base_max = min(ny - 3, iy_base_min + n_base_y - 1)

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
    mask_ground_102[iy_ground_min:iy_ground_max + 1, ix_ground_l:ix_ground_r + 1] = True

    # 3. First electrode 101: base plate + blade(s)
    mask_blade_101[iy_base_min:iy_base_max + 1, ix_blade_base:ix_blade_back + 1] = True
    # Exterior distal rear surface 101a: strictly 1-cell-thick right-most column of base plate
    mask_distal_101a[iy_base_min:iy_base_max + 1, ix_blade_back] = True
    # Exterior front shoulder of base plate (initially all of ix_blade_base; blade roots cleared below)
    mask_connecting_100b[iy_base_min:iy_base_max + 1, ix_blade_base] = True
    # Top and bottom edges of base plate
    mask_connecting_100b[iy_base_min, ix_blade_base:ix_blade_back + 1] = True
    mask_connecting_100b[iy_base_max, ix_blade_base:ix_blade_back + 1] = True

    # Blade(s)
    n_tip_y = max(1, int(round(params.blade_thickness_m / dy)))
    y_center_m = (iy_center + n_offset_y) * dy
    blade_y_ranges: List[Tuple[int, int]] = []

    if num_blades <= 1:
        b_min = max(iy_base_min, (iy_center + n_offset_y) - (n_tip_y // 2))
        b_max = min(iy_base_max, b_min + n_tip_y - 1)
        blade_y_ranges.append((b_min, b_max))
    else:
        y_start_m = y_center_m - ((num_blades - 1) * pitch / 2.0)
        for b in range(num_blades):
            by_m = y_start_m + b * pitch
            iy_b = int(round(by_m / dy))
            b_min = max(iy_base_min, iy_b - (n_tip_y // 2))
            b_max = min(iy_base_max, b_min + n_tip_y - 1)
            blade_y_ranges.append((b_min, b_max))

    for b_min, b_max in blade_y_ranges:
        # Full blade body
        mask_blade_101[b_min:b_max + 1, ix_blade_tip:ix_blade_base + 1] = True
        # Remove interior root from front shoulder mask
        if b_max > b_min + 1:
            mask_connecting_100b[b_min + 1:b_max, ix_blade_base] = False
        # Exterior lateral blade flanks 100b (strictly top and bottom rows of each blade)
        mask_connecting_100b[b_min, ix_blade_tip:ix_blade_base + 1] = True
        mask_connecting_100b[b_max, ix_blade_tip:ix_blade_base + 1] = True
        # Exterior proximal blade tip surface 100a (strictly 1-cell-thick left-most column of blade)
        mask_proximal_100a[b_min:b_max + 1, ix_blade_tip] = True

    # Disjointness enforcement
    mask_blade_101 = mask_blade_101 & (~mask_ground_102) & (~mask_enclosure_box)
    mask_ground_102 = mask_ground_102 & (~mask_enclosure_box)

    # 4. Build explicit boundary face structures with material-side sampling
    boundary_faces: List[ConductorBoundaryFace] = []

    # Face 100a: proximal blade tip(s) facing ground (outward normal = (-1, 0))
    tip_cond_ix = []
    tip_cond_iy = []
    tip_sample_ix = []
    tip_sample_iy = []
    for b_min, b_max in blade_y_ranges:
        for j in range(b_min, b_max + 1):
            tip_cond_iy.append(j)
            tip_cond_ix.append(ix_blade_tip)
            tip_sample_iy.append(j)
            tip_sample_ix.append(ix_blade_tip - 1)

    total_tip_width = len(tip_sample_iy) * dy
    boundary_faces.append(ConductorBoundaryFace(
        face_name="proximal_tip_100a",
        conductor_id="blade_101",
        outward_normal=(-1.0, 0.0),
        length_m=float(total_tip_width),
        conductor_ix=np.array(tip_cond_ix, dtype=int),
        conductor_iy=np.array(tip_cond_iy, dtype=int),
        sample_ix_ext=np.array(tip_sample_ix, dtype=int),
        sample_iy_ext=np.array(tip_sample_iy, dtype=int),
    ))

    # Face 101a: distal rear face of base plate (outward normal = (+1, 0))
    distal_cond_iy = np.arange(iy_base_min, iy_base_max + 1, dtype=int)
    distal_cond_ix = np.full_like(distal_cond_iy, ix_blade_back)
    distal_sample_iy = distal_cond_iy.copy()
    distal_sample_ix = np.full_like(distal_cond_iy, ix_blade_back + 1)

    distal_width = len(distal_sample_iy) * dy
    boundary_faces.append(ConductorBoundaryFace(
        face_name="distal_rear_101a",
        conductor_id="blade_101",
        outward_normal=(1.0, 0.0),
        length_m=float(distal_width),
        conductor_ix=distal_cond_ix,
        conductor_iy=distal_cond_iy,
        sample_ix_ext=distal_sample_ix,
        sample_iy_ext=distal_sample_iy,
    ))

    # Ground front face 102a facing blade (outward normal = (+1, 0))
    ground_cond_iy = np.arange(iy_ground_min, iy_ground_max + 1, dtype=int)
    ground_front_cond_ix = np.full_like(ground_cond_iy, ix_ground_r)
    ground_front_sample_ix = np.full_like(ground_cond_iy, ix_ground_r + 1)
    ground_width = len(ground_cond_iy) * dy

    boundary_faces.append(ConductorBoundaryFace(
        face_name="ground_front_102a",
        conductor_id="ground_102",
        outward_normal=(1.0, 0.0),
        length_m=float(ground_width),
        conductor_ix=ground_front_cond_ix,
        conductor_iy=ground_cond_iy.copy(),
        sample_ix_ext=ground_front_sample_ix,
        sample_iy_ext=ground_cond_iy.copy(),
    ))

    # Ground rear face 102b facing left enclosure wall (outward normal = (-1, 0))
    ground_rear_cond_ix = np.full_like(ground_cond_iy, ix_ground_l)
    ground_rear_sample_ix = np.full_like(ground_cond_iy, ix_ground_l - 1)

    boundary_faces.append(ConductorBoundaryFace(
        face_name="ground_rear_102b",
        conductor_id="ground_102",
        outward_normal=(-1.0, 0.0),
        length_m=float(ground_width),
        conductor_ix=ground_rear_cond_ix,
        conductor_iy=ground_cond_iy.copy(),
        sample_ix_ext=ground_rear_sample_ix,
        sample_iy_ext=ground_cond_iy.copy(),
    ))

    # 5. Permittivity map (dielectric potting encapsulates the inter-electrode cavity / assembly)
    permittivity_map = np.ones((ny, nx), dtype=float)
    mask_dielectric_region = np.zeros((ny, nx), dtype=bool)
    if abs(params.dielectric_relative_permittivity - 1.0) > 1e-12:
        iy_diel_min = min(iy_base_min, iy_ground_min)
        iy_diel_max = max(iy_base_max, iy_ground_max)
        ix_diel_start = ix_ground_l
        ix_diel_end = ix_blade_back
        mask_dielectric_region[iy_diel_min:iy_diel_max + 1, ix_diel_start:ix_diel_end + 1] = True
        permittivity_map[mask_dielectric_region] = params.dielectric_relative_permittivity

    # 6. Boundary conditions
    potential_bc = np.zeros((ny, nx), dtype=float)
    potential_bc[mask_blade_101] = params.applied_voltage_v
    potential_bc[mask_ground_102] = 0.0
    potential_bc[mask_enclosure_box] = 0.0

    fixed_mask = mask_blade_101 | mask_ground_102 | mask_enclosure_box

    # Discretization tracking
    target_tip_w = float(params.blade_thickness_m)
    actual_tip_w = float(total_tip_width)
    tip_ratio = float(actual_tip_w / target_tip_w) if target_tip_w > 0 else 1.0

    target_gap = float(params.gap_spacing_m)
    actual_gap = float(n_gap * dx)
    gap_ratio = float(actual_gap / target_gap) if target_gap > 0 else 1.0

    target_height = float(params.blade_height_m)
    actual_height = float(n_blade_p * dx)
    height_ratio = float(actual_height / target_height) if target_height > 0 else 1.0

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
        mask_dielectric_region=mask_dielectric_region,
        potential_bc=potential_bc,
        fixed_mask=fixed_mask,
        target_tip_width_m=target_tip_w,
        discretized_tip_width_m=actual_tip_w,
        tip_width_discretization_ratio=tip_ratio,
        target_gap_m=target_gap,
        discretized_gap_m=actual_gap,
        gap_discretization_ratio=gap_ratio,
        target_blade_height_m=target_height,
        discretized_blade_height_m=actual_height,
        blade_height_discretization_ratio=height_ratio,
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
    grid.mask_dielectric_region.fill(False)
    grid.permittivity_map.fill(1.0)

    nx = grid.nx
    ny = grid.ny
    dx = grid.dx
    dy = grid.dy

    # Exact mirror-symmetric positioning along y
    plate_w_cells = max(2, int(round(params.ground_plane_width_m / dy)))
    margin_y = max(3, (ny - plate_w_cells) // 2)
    iy_min = margin_y
    iy_max = (ny - 1) - margin_y

    # Exact mirror-symmetric positioning along x
    th_cells = max(1, int(round(params.base_plate_thickness_m / dx)))
    gap_cells = max(2, int(round(params.gap_spacing_m / dx)))
    margin_x = max(3, (nx - 2 * th_cells - gap_cells) // 2)

    ix_g_l = margin_x
    ix_g_r = ix_g_l + th_cells - 1

    ix_b_r = (nx - 1) - margin_x
    ix_b_l = ix_b_r - th_cells + 1

    grid.mask_ground_102[iy_min:iy_max + 1, ix_g_l:ix_g_r + 1] = True
    grid.mask_blade_101[iy_min:iy_max + 1, ix_b_l:ix_b_r + 1] = True
    grid.mask_proximal_100a[iy_min:iy_max + 1, ix_b_l] = True
    grid.mask_distal_101a[iy_min:iy_max + 1, ix_b_r] = True

    # Symmetrical excitation (+V/2 and -V/2) relative to grounded outer enclosure
    grid.potential_bc.fill(0.0)
    grid.potential_bc[grid.mask_blade_101] = params.applied_voltage_v / 2.0
    grid.potential_bc[grid.mask_ground_102] = -params.applied_voltage_v / 2.0
    grid.potential_bc[grid.mask_enclosure_box] = 0.0
    grid.fixed_mask = grid.mask_blade_101 | grid.mask_ground_102 | grid.mask_enclosure_box

    return grid


def build_inverted_180_grid(params: Optional[ExodusPatentParameters] = None) -> ExodusGrid2D:
    """Build a 180-degree spatially inverted apparatus grid (x -> Lx - x).

    Flips the apparatus orientation inside the chamber so the blade faces +x toward the
    ground plate on the right. A true physical force attached to the device must reverse
    sign (Fx -> -Fx) under 180-degree spatial inversion.
    """
    base_grid = build_exodus_2d_grid(params)
    nx = base_grid.nx

    inv_faces: List[ConductorBoundaryFace] = []
    for face in base_grid.boundary_faces:
        inv_faces.append(ConductorBoundaryFace(
            face_name=face.face_name,
            conductor_id=face.conductor_id,
            outward_normal=(-face.outward_normal[0], face.outward_normal[1]),
            length_m=face.length_m,
            conductor_ix=(nx - 1) - face.conductor_ix,
            conductor_iy=face.conductor_iy.copy(),
            sample_ix_ext=(nx - 1) - face.sample_ix_ext,
            sample_iy_ext=face.sample_iy_ext.copy(),
        ))

    return ExodusGrid2D(
        params=base_grid.params,
        nx=base_grid.nx,
        ny=base_grid.ny,
        dx=base_grid.dx,
        dy=base_grid.dy,
        x_coords_m=base_grid.x_coords_m.copy(),
        y_coords_m=base_grid.y_coords_m.copy(),
        mask_blade_101=np.fliplr(base_grid.mask_blade_101).copy(),
        mask_ground_102=np.fliplr(base_grid.mask_ground_102).copy(),
        mask_enclosure_box=np.fliplr(base_grid.mask_enclosure_box).copy(),
        mask_proximal_100a=np.fliplr(base_grid.mask_proximal_100a).copy(),
        mask_distal_101a=np.fliplr(base_grid.mask_distal_101a).copy(),
        mask_connecting_100b=np.fliplr(base_grid.mask_connecting_100b).copy(),
        boundary_faces=inv_faces,
        permittivity_map=np.fliplr(base_grid.permittivity_map).copy(),
        mask_dielectric_region=np.fliplr(base_grid.mask_dielectric_region).copy(),
        potential_bc=np.fliplr(base_grid.potential_bc).copy(),
        fixed_mask=np.fliplr(base_grid.fixed_mask).copy(),
        target_tip_width_m=base_grid.target_tip_width_m,
        discretized_tip_width_m=base_grid.discretized_tip_width_m,
        tip_width_discretization_ratio=base_grid.tip_width_discretization_ratio,
        target_gap_m=base_grid.target_gap_m,
        discretized_gap_m=base_grid.discretized_gap_m,
        gap_discretization_ratio=base_grid.gap_discretization_ratio,
        target_blade_height_m=base_grid.target_blade_height_m,
        discretized_blade_height_m=base_grid.discretized_blade_height_m,
        blade_height_discretization_ratio=base_grid.blade_height_discretization_ratio,
    )
