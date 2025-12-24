from dataclasses import dataclass, field
from typing import Optional, List


@dataclass(frozen=True)
class Config:
    # -------------------------
    # Cube / walls
    # -------------------------
    cube_edge: float = 150.0
    wall_thickness: float = 3.2

    # Open bottom for access
    open_bottom: bool = True
    bottom_rim_width: float = 6.0

    # -------------------------
    # Slots (all faces)
    # -------------------------
    # Square slot opening = cube_edge * slot_fraction
    slot_fraction: float = 0.85
    slot_depth: float = 2.4

    # Taper on slot walls. For ~45° taper, set == slot_depth.
    # Set 0.0 for straight slots.
    slot_miter_mm: float = 2.4

    # -------------------------
    # Top behavior (the “recipe”)
    # -------------------------
    # Make TOP slot identical to side-wall slot geometry (same miter/taper),
    # BUT remove ONLY the flat slot floor inside the mitered edge so the top becomes open.
    # The plate still seats on the mitered walls.
    top_open_remove_floor: bool = True
    # Safety margin on the through-opening (keeps sloped walls intact)
    top_open_inner_margin_mm: float = 0.0  # try 0.0; bump to 0.2 if slicer shows artifacts

    # Additive-only support ramp BELOW the top slot floor (does not change anything above).
    # Creates a continuous 45° perimeter ramp from inner walls up to the inner edge of the slot-floor opening.
    top_support_ramps_enabled: bool = True
    top_ramp_start_inset_mm: float = 0.4  # thickness of the first ramp \"step\" at the start height

    # -------------------------
    # Plate parameters
    # -------------------------
    clearance: float = 0.2
    plate_margin_fraction: float = 0.88

    # ArUco
    aruco_marker_bits: int = 4
    aruco_border_bits: int = 1
    aruco_image_size: int = 200
    marker_height: float = 0.8

    # Bezel (flange)
    bezel_overhang: float = 0.8
    bezel_thickness: float = 0.8

    # Optional bezel text
    bezel_text_enabled: bool = True
    bezel_text_prefix: str = "ID "
    bezel_text_height_mm: float = 3.0
    bezel_text_depth_mm: float = 1.2
    bezel_text_font: Optional[str] = None

    # IDs
    plate_ids: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])

    # ArUco dictionary
    aruco_dict_name: str = "DICT_4X4_50"
