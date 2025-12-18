"""
geometry.py

Mesh construction for:
- Hollow cube with recessed slots (requires trimesh boolean backend)
- Slot-fit plate base with bezel + optional embossed ID text (no booleans needed)

All dimensions are in millimeters.
"""

from __future__ import annotations

import numpy as np
import trimesh

from .config import Config
from .text3d import make_text_mesh


def make_box(extents, center) -> trimesh.Trimesh:
    """
    Create a trimesh box (axis-aligned) with given extents and center.

    extents: (x_size, y_size, z_size)
    center : (cx, cy, cz)
    """
    box = trimesh.creation.box(extents=extents)
    box.apply_translation(np.asarray(center) - box.center_mass)
    return box


def create_cube_with_slots(cfg: Config) -> trimesh.Trimesh:
    """
    Create a hollow cube with 5 recessed slots (top, +X, -X, +Y, -Y).
    Bottom face is solid so it can sit on the build plate.

    NOTE:
    This uses boolean operations (difference). You need a boolean backend
    (commonly OpenSCAD) for this to work reliably.
    """
    ce = cfg.cube_edge
    wt = cfg.wall_thickness

    # Outer + inner cubes are centered at origin
    outer = trimesh.creation.box(extents=(ce, ce, ce))
    inner = trimesh.creation.box(extents=(ce - 2 * wt, ce - 2 * wt, ce - 2 * wt))

    try:
        shell = outer.difference(inner)
    except Exception as e:
        raise RuntimeError(
            "Boolean difference failed while hollowing cube.\n"
            "You likely need a trimesh boolean backend (e.g., OpenSCAD).\n"
            f"Original error: {e}"
        )

    slot_size = ce * cfg.slot_fraction
    d = cfg.slot_depth

    # Slots (centered around origin, cut into faces)
    top_slot = make_box((slot_size, slot_size, d), [0.0, 0.0, ce / 2 - d / 2])
    posx_slot = make_box((d, slot_size, slot_size), [ce / 2 - d / 2, 0.0, 0.0])
    negx_slot = make_box((d, slot_size, slot_size), [-ce / 2 + d / 2, 0.0, 0.0])
    posy_slot = make_box((slot_size, d, slot_size), [0.0, ce / 2 - d / 2, 0.0])
    negy_slot = make_box((slot_size, d, slot_size), [0.0, -ce / 2 + d / 2, 0.0])

    slots_union = trimesh.util.concatenate([top_slot, posx_slot, negx_slot, posy_slot, negy_slot])

    try:
        shell_with_slots = shell.difference(slots_union)
    except Exception as e:
        raise RuntimeError(
            "Boolean difference failed while cutting slots.\n"
            "You likely need a trimesh boolean backend (e.g., OpenSCAD).\n"
            f"Original error: {e}"
        )

    # Move cube so that bottom rests on z = 0 (nice for printing)
    min_z = shell_with_slots.bounds[0][2]
    shell_with_slots.apply_translation([0.0, 0.0, -min_z])

    return shell_with_slots


def create_plate_base(cfg: Config, text: str | None):
    """
    Create a single plate base that fits into the recessed slot.
    Adds a top bezel (flange) to hide the seam.

    Text:
    - placed in bottom quiet-zone band
    - EMBOSSED (concatenated) so it works without boolean backends

    Returns: (base_mesh, plate_size, plate_thickness)
    """
    slot_size = cfg.cube_edge * cfg.slot_fraction
    plate_size = slot_size - 2 * cfg.clearance
    plate_thickness = cfg.slot_depth

    # Main plug that fits into the slot (origin in lower-left corner)
    plate = trimesh.creation.box(extents=(plate_size, plate_size, plate_thickness))
    plate.apply_translation([plate_size / 2, plate_size / 2, plate_thickness / 2])

    # Bezel flange (sits on cube face)
    bezel_outer = slot_size + 2.0 * cfg.bezel_overhang
    bezel_t = min(cfg.bezel_thickness, plate_thickness)

    bezel = trimesh.creation.box(extents=(bezel_outer, bezel_outer, bezel_t))
    bezel.apply_translation([plate_size / 2, plate_size / 2, plate_thickness - bezel_t / 2])

    base = trimesh.util.concatenate([plate, bezel])

    # Optional embossed ID text in bottom quiet band
    if text and cfg.bezel_text_enabled:
        try:
            # Quiet zone band thickness
            marker_area = plate_size * cfg.plate_margin_fraction
            margin_mm = (plate_size - marker_area) / 2.0

            # Fit text into band with some breathing room
            target_h = min(cfg.bezel_text_height_mm, max(2.0, margin_mm - 1.0))

            depth = max(0.8, cfg.bezel_text_depth_mm)

            # Create text (start large-ish then scale to target height)
            txt = make_text_mesh(
                text=text,
                font=cfg.bezel_text_font,
                font_size=10.0,
                depth=depth,
                target_height_mm=target_h,
            )

            # Scale in XY to match target height (Y size)
            b = txt.bounds
            txt_h = b[1][1] - b[0][1]
            s = target_h / max(txt_h, 1e-6)
            txt.apply_scale([s, s, 1.0])

            # Clamp width to keep edges clean
            b = txt.bounds
            txt_w = b[1][0] - b[0][0]
            max_w = plate_size - 2.0  # ~1mm margin each side
            if txt_w > max_w:
                s2 = max_w / max(txt_w, 1e-6)
                txt.apply_scale([s2, s2, 1.0])

            # Center text in bottom band
            b = txt.bounds
            bx = (b[0][0] + b[1][0]) / 2.0
            by = (b[0][1] + b[1][1]) / 2.0
            bz = (b[0][2] + b[1][2]) / 2.0

            cx = plate_size / 2.0
            cy = margin_mm / 2.0
            EMBED_MM = 0.5  # small overlap so slicers don't delete the text
            cz = plate_thickness + depth / 2.0 - EMBED_MM

            txt.apply_translation([cx - bx, cy - by, cz - bz])

            # Add embossed text geometry
            base = trimesh.util.concatenate([base, txt])

        except Exception as e:
            print("TEXT EMBOSS FAILED:", e)

    return base, plate_size, plate_thickness
