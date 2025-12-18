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

def make_chamfered_slot_cutter(extents, chamfer_mm: float, open_axis: str) -> trimesh.Trimesh:
    """
    Create a slot cutter with a 45° chamfer around the perimeter of the OPENING face.

    extents: (sx, sy, sz) for the cutter box, centered at origin.
    open_axis: 'x', 'y', or 'z' meaning the opening face is on the +axis side.
              (For openings on -axis, create with +axis then rotate 180° in caller.)
    chamfer_mm: size of chamfer (mm). Typical 0.6–1.2mm.

    Returns: Trimesh centered at origin.
    """
    sx, sy, sz = extents
    if chamfer_mm <= 1e-6:
        return trimesh.creation.box(extents=extents)

    ch = float(chamfer_mm)
    base = trimesh.creation.box(extents=extents)

    def _rot(axis, angle_rad):
        return trimesh.transformations.rotation_matrix(angle=angle_rad, direction=axis)

    wedges = []

    if open_axis == "z":
        # Opening on +Z face, chamfer around perimeter in XY plane.
        # Wedges along +Y and -Y edges (run along X)
        w1 = trimesh.creation.box(extents=(sx, ch, ch))
        w1.apply_transform(_rot([1, 0, 0], np.pi / 4))
        w1.apply_translation([0, +sy / 2 - ch / 2, +sz / 2 - ch / 2])
        wedges.append(w1)

        w2 = trimesh.creation.box(extents=(sx, ch, ch))
        w2.apply_transform(_rot([1, 0, 0], -np.pi / 4))
        w2.apply_translation([0, -sy / 2 + ch / 2, +sz / 2 - ch / 2])
        wedges.append(w2)

        # Wedges along +X and -X edges (run along Y)
        w3 = trimesh.creation.box(extents=(ch, sy, ch))
        w3.apply_transform(_rot([0, 1, 0], -np.pi / 4))
        w3.apply_translation([+sx / 2 - ch / 2, 0, +sz / 2 - ch / 2])
        wedges.append(w3)

        w4 = trimesh.creation.box(extents=(ch, sy, ch))
        w4.apply_transform(_rot([0, 1, 0], np.pi / 4))
        w4.apply_translation([-sx / 2 + ch / 2, 0, +sz / 2 - ch / 2])
        wedges.append(w4)

    elif open_axis == "x":
        # Opening on +X face, chamfer around perimeter in YZ plane.
        # Wedges along +Y/-Y edges (run along Z)
        w1 = trimesh.creation.box(extents=(ch, ch, sz))
        w1.apply_transform(_rot([0, 0, 1], -np.pi / 4))
        w1.apply_translation([+sx / 2 - ch / 2, +sy / 2 - ch / 2, 0])
        wedges.append(w1)

        w2 = trimesh.creation.box(extents=(ch, ch, sz))
        w2.apply_transform(_rot([0, 0, 1], np.pi / 4))
        w2.apply_translation([+sx / 2 - ch / 2, -sy / 2 + ch / 2, 0])
        wedges.append(w2)

        # Wedges along +Z/-Z edges (run along Y)
        w3 = trimesh.creation.box(extents=(ch, sy, ch))
        w3.apply_transform(_rot([0, 1, 0], np.pi / 4))
        w3.apply_translation([+sx / 2 - ch / 2, 0, +sz / 2 - ch / 2])
        wedges.append(w3)

        w4 = trimesh.creation.box(extents=(ch, sy, ch))
        w4.apply_transform(_rot([0, 1, 0], -np.pi / 4))
        w4.apply_translation([+sx / 2 - ch / 2, 0, -sz / 2 + ch / 2])
        wedges.append(w4)

    elif open_axis == "y":
        # Opening on +Y face, chamfer around perimeter in XZ plane.
        # Wedges along +X/-X edges (run along Z)
        w1 = trimesh.creation.box(extents=(ch, ch, sz))
        w1.apply_transform(_rot([0, 0, 1], np.pi / 4))
        w1.apply_translation([+sx / 2 - ch / 2, +sy / 2 - ch / 2, 0])
        wedges.append(w1)

        w2 = trimesh.creation.box(extents=(ch, ch, sz))
        w2.apply_transform(_rot([0, 0, 1], -np.pi / 4))
        w2.apply_translation([-sx / 2 + ch / 2, +sy / 2 - ch / 2, 0])
        wedges.append(w2)

        # Wedges along +Z/-Z edges (run along X)
        w3 = trimesh.creation.box(extents=(sx, ch, ch))
        w3.apply_transform(_rot([1, 0, 0], -np.pi / 4))
        w3.apply_translation([0, +sy / 2 - ch / 2, +sz / 2 - ch / 2])
        wedges.append(w3)

        w4 = trimesh.creation.box(extents=(sx, ch, ch))
        w4.apply_transform(_rot([1, 0, 0], np.pi / 4))
        w4.apply_translation([0, +sy / 2 - ch / 2, -sz / 2 + ch / 2])
        wedges.append(w4)

    else:
        raise ValueError("open_axis must be one of: 'x', 'y', 'z'")

    return trimesh.util.concatenate([base] + wedges)


def rotate_180(mesh: trimesh.Trimesh, axis: str) -> trimesh.Trimesh:
    """
    Rotate a mesh 180° about a principal axis through the origin.
    axis: 'x', 'y', or 'z'
    """
    if axis == "x":
        R = trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0])
    elif axis == "y":
        R = trimesh.transformations.rotation_matrix(np.pi, [0, 1, 0])
    elif axis == "z":
        R = trimesh.transformations.rotation_matrix(np.pi, [0, 0, 1])
    else:
        raise ValueError("axis must be 'x', 'y', or 'z'")
    m = mesh.copy()
    m.apply_transform(R)
    return m


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

    # Chamfer to avoid "printing in air" on slot inner edges
    CHAMFER_MM = 0.8  # 0.6–1.2 typical; 0.8 is a good default for 0.4 nozzle

    # Top slot (+Z opening)
    top_slot = make_chamfered_slot_cutter((slot_size, slot_size, d), CHAMFER_MM, open_axis="z")
    top_slot.apply_translation([0.0, 0.0, ce / 2 - d / 2])

    # +X slot (opening faces +X)
    posx_slot = make_chamfered_slot_cutter((d, slot_size, slot_size), CHAMFER_MM, open_axis="x")
    posx_slot.apply_translation([ce / 2 - d / 2, 0.0, 0.0])

    # -X slot (opening faces -X) -> make +X then rotate 180° about Y
    negx_slot = make_chamfered_slot_cutter((d, slot_size, slot_size), CHAMFER_MM, open_axis="x")
    negx_slot = rotate_180(negx_slot, axis="y")
    negx_slot.apply_translation([-ce / 2 + d / 2, 0.0, 0.0])

    # +Y slot (opening faces +Y)
    posy_slot = make_chamfered_slot_cutter((slot_size, d, slot_size), CHAMFER_MM, open_axis="y")
    posy_slot.apply_translation([0.0, ce / 2 - d / 2, 0.0])

    # -Y slot (opening faces -Y) -> make +Y then rotate 180° about X
    negy_slot = make_chamfered_slot_cutter((slot_size, d, slot_size), CHAMFER_MM, open_axis="y")
    negy_slot = rotate_180(negy_slot, axis="x")
    negy_slot.apply_translation([0.0, -ce / 2 + d / 2, 0.0])


    slots_union = trimesh.util.concatenate([top_slot, posx_slot, negx_slot, posy_slot, negy_slot])

    try:
        shell_with_slots = shell.difference(slots_union)
    except Exception as e:
        raise RuntimeError(
            "Boolean difference failed while cutting slots.\n"
            "You likely need a trimesh boolean backend (e.g., OpenSCAD).\n"
            f"Original error: {e}"
        )
    
    # Optional: open bottom to save filament/time, keep perimeter rim for stiffness
    if getattr(cfg, "open_bottom", False):
        rim_w = cfg.wall_thickness if getattr(cfg, "bottom_rim_width", 0.0) <= 0 else cfg.bottom_rim_width

        # Remove only the interior bottom panel (leave a rim around edges).
        # Outer cube is centered at origin, so bottom is at z = -ce/2.
        # The "floor" thickness of the shell is approximately wall_thickness.
        floor_t = cfg.wall_thickness
        inner_xy = ce - 2 * rim_w
        if inner_xy <= 0:
            raise ValueError(f"bottom_rim_width too large ({rim_w}); must be < {ce/2}")

        cut = make_box(
            extents=(ce - 2 * rim_w, ce - 2 * rim_w, floor_t + 0.2),  # +0.2 for robust boolean overlap
            center=[0.0, 0.0, -ce / 2 + (floor_t + 0.2) / 2],
        )

        shell_with_slots = shell_with_slots.difference(cut)

        # Optional: internal ribs near roof to avoid huge bridging + stiffen cube
    if getattr(cfg, "roof_ribs", False):
        rib_t = cfg.wall_thickness if getattr(cfg, "roof_rib_thickness", 0.0) <= 0 else cfg.roof_rib_thickness
        rib_h = float(getattr(cfg, "roof_rib_height", 12.0))

        # Inner clear span (between inner walls)
        inner_span = ce - 2 * wt

        # Underside of the (non-recessed) roof in centered coordinates
        roof_inner_z = ce / 2 - wt

        # Make ribs touch/overlap the roof slightly so slicers don't drop/decouple them
        OVERLAP_MM = 0.3
        rib_top_z = roof_inner_z + OVERLAP_MM
        rib_center_z = rib_top_z - rib_h / 2

        rib_x = make_box(
            extents=(inner_span, rib_t, rib_h),
            center=[0.0, 0.0, rib_center_z],
        )
        rib_y = make_box(
            extents=(rib_t, inner_span, rib_h),
            center=[0.0, 0.0, rib_center_z],
        )

        # Concatenate is enough (they intersect the shell slightly); no boolean union needed
        shell_with_slots = trimesh.util.concatenate([shell_with_slots, rib_x, rib_y])


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
