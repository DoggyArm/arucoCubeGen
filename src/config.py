"""
Configuration for the screwless, gender-flipped system:

- Plates have studs (male) along all edges on the INSIDE face.
- Edge blocks have blind sockets (female) on two perpendicular faces.
- Plates remain truly interchangeable.

Units: mm
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class PlateConfig:
    size_mm: float = 120.0
    thickness_mm: float = 5.0

    # 45° miter: inset equals thickness
    miter_enabled: bool = True

    # Anti-elephant-foot relief on OUTSIDE perimeter (helps when printing outside face down)
    relief_enabled: bool = True
    relief_inset_mm: float = 0.25
    relief_height_mm: float = 0.30

    # Stud rows along each edge (same for all 4 edges)
    studs_per_edge: int = 5
    stud_end_margin_mm: float = 25.0   # keep away from corners

    # Stud centerline distance from the outer edge, towards the plate center.
    # Must match EdgeBlockConfig.socket_offset_mm.
    stud_edge_offset_mm: float = 12.0

    # Stud geometry (PLA fit)
    stud_d_mm: float = 3.15
    stud_len_mm: float = 2.7
    stud_tip_chamfer_mm: float = 0.6

    # Reinforcement "donut" around stud root (inside face) to prevent snapping
    stud_boss_outer_d_mm: float = 8.0
    stud_boss_height_mm: float = 2.0


@dataclass(frozen=True)
class MarkerConfig:
    aruco_dict: str = "DICT_4X4_50"
    modules: int = 4
    border_bits: int = 1

    marker_size_mm: float = 70.0

    # With outside face printed down, these are "inlay depth" into the plate, not outward protrusion.
    inlay_depth_mm: float = 0.6
    center: bool = True


@dataclass(frozen=True)
class EdgeBlockConfig:
    """
    A cuboid edge block with two perpendicular faces that each have a row of blind sockets.
    This block joins two plates at 90°.

    Block local coordinates:
      - block occupies x in [0..block_size], y in [0..block_size], z in [0..length]
      - sockets open on:
          face X0 (x=0) drilling +X
          face Y0 (y=0) drilling +Y
      - socket centerline offset from those faces is socket_offset_mm along the other axis.

    You use the SAME STL for vertical and horizontal edges by rotating it in the slicer.
    """
    block_size_mm: float = 18.0      # thickness in X and Y
    length_mm: float = 120.0         # match plate size

    # Socket placement must match plate studs:
    sockets_per_edge: int = 5
    socket_end_margin_mm: float = 14.0
    socket_offset_mm: float = 12.0   # MUST equal PlateConfig.stud_edge_offset_mm

    # Blind socket geometry (PLA interference)
    socket_d_mm: float = 3.05
    socket_depth_mm: float = 3.0

    # Small lead-in chamfer at socket mouth (nice to have)
    socket_mouth_chamfer_mm: float = 0.4


# Face IDs for 5 visible faces (open bottom)
DEFAULT_FACE_IDS: Dict[str, int] = {
    "TOP": 0,
    "SIDE1": 1,
    "SIDE2": 2,
    "SIDE3": 3,
    "SIDE4": 4,
}
