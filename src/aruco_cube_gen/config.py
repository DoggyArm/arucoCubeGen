from dataclasses import dataclass, field
from typing import Optional, List


@dataclass(frozen=True)
class Config:
    # -------------------------
    # Cube / slot parameters
    # -------------------------
    cube_edge: float = 150.0
    wall_thickness: float = 3.2

    slot_fraction: float = 0.85
    slot_depth: float = 2.4

    open_bottom: bool = True
    bottom_rim_width: float = 6.0

    # -------------------------
    # Roof reinforcement (ADD material)
    # -------------------------
    roof_extra_thickness_mm: float = 1.0

    attic_drop_mm: float = 3.0
    attic_margin_mm: float = 0.5

    # Prevent attic/slab from touching slot cavities
    attic_keepout_margin_mm: float = 1.0

    # -------------------------
    # Slot taper (print-friendly)
    # -------------------------
    # True 45° miter by default (taper == slot_depth)
    slot_miter_mm: float = 2.4

    # -------------------------
    # Plate parameters
    # -------------------------
    clearance: float = 0.2
    plate_margin_fraction: float = 0.88
    aruco_marker_bits: int = 4
    aruco_border_bits: int = 1
    aruco_image_size: int = 200
    marker_height: float = 0.8

    # -------------------------
    # Bezel (flange)
    # -------------------------
    bezel_overhang: float = 0.8
    bezel_thickness: float = 0.8

    # -------------------------
    # Bezel text
    # -------------------------
    bezel_text_enabled: bool = True
    bezel_text_prefix: str = "ID "
    bezel_text_height_mm: float = 3.0
    bezel_text_depth_mm: float = 1.2
    bezel_text_font: Optional[str] = None

    # -------------------------
    # IDs
    # -------------------------
    plate_ids: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])

    # -------------------------
    # ArUco dictionary
    # -------------------------
    aruco_dict_name: str = "DICT_4X4_50"
