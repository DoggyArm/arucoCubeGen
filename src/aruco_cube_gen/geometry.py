"""
geometry.py

Mesh construction for:
- Hollow cube with recessed slots (requires trimesh boolean backend)
- Slot-fit plate base with bezel + optional embossed ID text (no booleans needed)

All dimensions are in millimeters.
"""

from __future__ import annotations

from typing import Iterable, List

import numpy as np
import trimesh

from .config import Config
from .text3d import make_text_mesh


# =============================================================================
# Low-level helpers
# =============================================================================

def make_box(extents, center) -> trimesh.Trimesh:
    """
    Create an axis-aligned box with given extents and center.

    extents: (x_size, y_size, z_size)
    center : (cx, cy, cz)
    """
    box = trimesh.creation.box(extents=extents)
    box.apply_translation(np.asarray(center) - box.center_mass)
    return box


def rotate_180(mesh: trimesh.Trimesh, axis: str) -> trimesh.Trimesh:
    """
    Rotate a mesh 180° around a principal axis through the origin.

    axis: 'x', 'y', or 'z'
    """
    axis = axis.lower()
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


def union_all(solids: Iterable[trimesh.Trimesh], what: str = "solids") -> trimesh.Trimesh:
    """
    Union a list of solids with pairwise accumulation.
    More stable than unioning a large list at once on some backends.
    """
    solids = list(solids)
    if not solids:
        raise ValueError(f"union_all: no solids provided for {what}")

    cur = solids[0]
    for s in solids[1:]:
        try:
            cur = cur.union([s])
        except Exception as e:
            raise RuntimeError(
                f"Boolean union failed while combining {what}.\n"
                "You likely need a trimesh boolean backend (e.g., OpenSCAD).\n"
                f"Original error: {e}"
            )
    return cur


# =============================================================================
# Slot cutter with chamfer on opening lip
# =============================================================================

def make_chamfered_slot_cutter(extents, chamfer_mm: float, open_axis: str) -> trimesh.Trimesh:
    """
    Create a slot cutter with a 45° chamfer around the perimeter of the OPENING face.

    extents: (sx, sy, sz) for the cutter box, centered at origin.
    open_axis: 'x', 'y', or 'z' meaning the opening face is on the +axis side.
               (For openings on -axis, create with +axis then rotate 180° in caller.)
    chamfer_mm: chamfer size in mm.

    Returns: a single cutter solid, centered at origin.
    """
    sx, sy, sz = extents
    ch = float(chamfer_mm)
    open_axis = open_axis.lower()

    if ch <= 1e-6:
        return trimesh.creation.box(extents=extents)

    base = trimesh.creation.box(extents=extents)

    def _rot(axis, angle_rad):
        return trimesh.transformations.rotation_matrix(angle=angle_rad, direction=axis)

    wedges: List[trimesh.Trimesh] = []

    if open_axis == "z":
        # Opening on +Z face (XY perimeter chamfer)
        w1 = trimesh.creation.box(extents=(sx, ch, ch))
        w1.apply_transform(_rot([1, 0, 0], np.pi / 4))
        w1.apply_translation([0, +sy / 2 - ch / 2, +sz / 2 - ch / 2])
        wedges.append(w1)

        w2 = trimesh.creation.box(extents=(sx, ch, ch))
        w2.apply_transform(_rot([1, 0, 0], -np.pi / 4))
        w2.apply_translation([0, -sy / 2 + ch / 2, +sz / 2 - ch / 2])
        wedges.append(w2)

        w3 = trimesh.creation.box(extents=(ch, sy, ch))
        w3.apply_transform(_rot([0, 1, 0], -np.pi / 4))
        w3.apply_translation([+sx / 2 - ch / 2, 0, +sz / 2 - ch / 2])
        wedges.append(w3)

        w4 = trimesh.creation.box(extents=(ch, sy, ch))
        w4.apply_transform(_rot([0, 1, 0], np.pi / 4))
        w4.apply_translation([-sx / 2 + ch / 2, 0, +sz / 2 - ch / 2])
        wedges.append(w4)

    elif open_axis == "x":
        # Opening on +X face (YZ perimeter chamfer)
        w1 = trimesh.creation.box(extents=(ch, ch, sz))
        w1.apply_transform(_rot([0, 0, 1], -np.pi / 4))
        w1.apply_translation([+sx / 2 - ch / 2, +sy / 2 - ch / 2, 0])
        wedges.append(w1)

        w2 = trimesh.creation.box(extents=(ch, ch, sz))
        w2.apply_transform(_rot([0, 0, 1], np.pi / 4))
        w2.apply_translation([+sx / 2 - ch / 2, -sy / 2 + ch / 2, 0])
        wedges.append(w2)

        w3 = trimesh.creation.box(extents=(ch, sy, ch))
        w3.apply_transform(_rot([0, 1, 0], np.pi / 4))
        w3.apply_translation([+sx / 2 - ch / 2, 0, +sz / 2 - ch / 2])
        wedges.append(w3)

        w4 = trimesh.creation.box(extents=(ch, sy, ch))
        w4.apply_transform(_rot([0, 1, 0], -np.pi / 4))
        w4.apply_translation([+sx / 2 - ch / 2, 0, -sz / 2 + ch / 2])
        wedges.append(w4)

    elif open_axis == "y":
        # Opening on +Y face (XZ perimeter chamfer)
        w1 = trimesh.creation.box(extents=(ch, ch, sz))
        w1.apply_transform(_rot([0, 0, 1], np.pi / 4))
        w1.apply_translation([+sx / 2 - ch / 2, +sy / 2 - ch / 2, 0])
        wedges.append(w1)

        w2 = trimesh.creation.box(extents=(ch, ch, sz))
        w2.apply_transform(_rot([0, 0, 1], -np.pi / 4))
        w2.apply_translation([-sx / 2 + ch / 2, +sy / 2 - ch / 2, 0])
        wedges.append(w2)

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

    # Build one solid cutter (more robust for boolean difference than concatenate)
    return union_all([base] + wedges, what="chamfered slot cutter")


# =============================================================================
# Cube
# =============================================================================

def _add_roof_ribs(shell: trimesh.Trimesh, cfg: Config, ce: float, wt: float) -> trimesh.Trimesh:
    """Optional: internal ribs under roof to reduce bridging and add stiffness."""
    if not getattr(cfg, "roof_ribs", False):
        return shell

    rib_t = cfg.wall_thickness if getattr(cfg, "roof_rib_thickness", 0.0) <= 0 else cfg.roof_rib_thickness
    rib_h = float(getattr(cfg, "roof_rib_height", 12.0))

    inner_span = ce - 2 * wt
    roof_inner_z = ce / 2 - wt

    overlap = 1.0
    rib_top_z = roof_inner_z + overlap
    rib_center_z = rib_top_z - rib_h / 2

    rib_x = make_box((inner_span, rib_t, rib_h), center=[0.0, 0.0, rib_center_z])
    rib_y = make_box((rib_t, inner_span, rib_h), center=[0.0, 0.0, rib_center_z])

    return shell.union([rib_x, rib_y])


def _add_roof_gussets(shell: trimesh.Trimesh, cfg: Config, ce: float, wt: float) -> trimesh.Trimesh:
    """
    Optional: ADD material at 45° along inside wall/roof junction.
    This reduces "starts in air" on the roof underside and stiffens the cube.

    cfg.roof_gusset_mm: typical 8–15mm for a 150mm cube.
    """
    rg = float(getattr(cfg, "roof_gusset_mm", 0.0))
    if rg <= 1e-6:
        return shell

    inner_span = ce - 2 * wt
    roof_inner_z = ce / 2 - wt

    def _gusset_along_x(sign: int) -> trimesh.Trimesh:
        w = trimesh.creation.box(extents=(inner_span, rg, rg))
        ang = +np.pi / 4 if sign > 0 else -np.pi / 4
        w.apply_transform(trimesh.transformations.rotation_matrix(ang, [1, 0, 0]))
        y = sign * (inner_span / 2 - rg / 2)
        z = roof_inner_z - rg / 2
        w.apply_translation([0.0, y, z])
        return w

    def _gusset_along_y(sign: int) -> trimesh.Trimesh:
        w = trimesh.creation.box(extents=(rg, inner_span, rg))
        ang = -np.pi / 4 if sign > 0 else +np.pi / 4
        w.apply_transform(trimesh.transformations.rotation_matrix(ang, [0, 1, 0]))
        x = sign * (inner_span / 2 - rg / 2)
        z = roof_inner_z - rg / 2
        w.apply_translation([x, 0.0, z])
        return w

    g0 = _gusset_along_x(+1)
    g1 = _gusset_along_x(-1)
    g2 = _gusset_along_y(+1)
    g3 = _gusset_along_y(-1)

    return shell.union([g0, g1, g2, g3])


def _open_bottom(shell: trimesh.Trimesh, cfg: Config, ce: float) -> trimesh.Trimesh:
    """Optional: open bottom interior panel, leave a rim for stiffness."""
    if not getattr(cfg, "open_bottom", False):
        return shell

    rim_w = cfg.wall_thickness if getattr(cfg, "bottom_rim_width", 0.0) <= 0 else cfg.bottom_rim_width
    floor_t = cfg.wall_thickness

    inner_xy = ce - 2 * rim_w
    if inner_xy <= 0:
        raise ValueError(f"bottom_rim_width too large ({rim_w}); must be < {ce/2}")

    cut = make_box(
        extents=(inner_xy, inner_xy, floor_t + 0.4),
        center=[0.0, 0.0, -ce / 2 + (floor_t + 0.4) / 2],
    )
    return shell.difference(cut)


def create_cube_with_slots(cfg: Config) -> trimesh.Trimesh:
    """
    Create a hollow cube with 5 recessed slots (top, +X, -X, +Y, -Y).
    Bottom is solid by default; can be opened with cfg.open_bottom.

    Requires a boolean backend (OpenSCAD recommended).
    """
    ce = cfg.cube_edge
    wt = cfg.wall_thickness

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

    # Slot opening chamfer to avoid “printing in air” on the lip
    chamfer_mm = float(getattr(cfg, "slot_chamfer_mm", 0.6))

    top_slot = make_chamfered_slot_cutter((slot_size, slot_size, d), chamfer_mm, open_axis="z")
    top_slot.apply_translation([0.0, 0.0, ce / 2 - d / 2])

    posx_slot = make_chamfered_slot_cutter((d, slot_size, slot_size), chamfer_mm, open_axis="x")
    posx_slot.apply_translation([ce / 2 - d / 2, 0.0, 0.0])

    negx_slot = make_chamfered_slot_cutter((d, slot_size, slot_size), chamfer_mm, open_axis="x")
    negx_slot = rotate_180(negx_slot, axis="y")
    negx_slot.apply_translation([-ce / 2 + d / 2, 0.0, 0.0])

    posy_slot = make_chamfered_slot_cutter((slot_size, d, slot_size), chamfer_mm, open_axis="y")
    posy_slot.apply_translation([0.0, ce / 2 - d / 2, 0.0])

    negy_slot = make_chamfered_slot_cutter((slot_size, d, slot_size), chamfer_mm, open_axis="y")
    negy_slot = rotate_180(negy_slot, axis="x")
    negy_slot.apply_translation([0.0, -ce / 2 + d / 2, 0.0])

    slots_union = union_all([top_slot, posx_slot, negx_slot, posy_slot, negy_slot], what="slot cutters")

    try:
        shell = shell.difference(slots_union)
    except Exception as e:
        raise RuntimeError(
            "Boolean difference failed while cutting slots.\n"
            "You likely need a trimesh boolean backend (e.g., OpenSCAD).\n"
            f"Original error: {e}"
        )

    # Optional features
    shell = _open_bottom(shell, cfg, ce)
    shell = _add_roof_ribs(shell, cfg, ce, wt)
    shell = _add_roof_gussets(shell, cfg, ce, wt)

    # Validate only after all boolean ops
    shell.process(validate=True)

    # Move so bottom rests at z=0
    min_z = shell.bounds[0][2]
    shell.apply_translation([0.0, 0.0, -min_z])

    # Debug: ensure single connected component
    parts = shell.split(only_watertight=False)
    print("Cube parts:", len(parts))

    return shell


# =============================================================================
# Plate base
# =============================================================================

def create_plate_base(cfg: Config, text: str | None):
    """
    Plate that fits the slot + bezel. Text is EMBOSSED (no booleans).

    Returns (mesh, plate_size, plate_thickness).
    """
    slot_size = cfg.cube_edge * cfg.slot_fraction
    plate_size = slot_size - 2 * cfg.clearance
    plate_thickness = cfg.slot_depth

    # Main plug
    plate = trimesh.creation.box(extents=(plate_size, plate_size, plate_thickness))
    plate.apply_translation([plate_size / 2, plate_size / 2, plate_thickness / 2])

    # Bezel flange
    bezel_outer = slot_size + 2.0 * cfg.bezel_overhang
    bezel_t = min(cfg.bezel_thickness, plate_thickness)

    bezel = trimesh.creation.box(extents=(bezel_outer, bezel_outer, bezel_t))
    bezel.apply_translation([plate_size / 2, plate_size / 2, plate_thickness - bezel_t / 2])

    base = trimesh.util.concatenate([plate, bezel])

    if text and cfg.bezel_text_enabled:
        try:
            marker_area = plate_size * cfg.plate_margin_fraction
            margin_mm = (plate_size - marker_area) / 2.0

            target_h = min(cfg.bezel_text_height_mm, max(2.0, margin_mm - 1.0))
            depth = max(0.8, cfg.bezel_text_depth_mm)

            txt = make_text_mesh(
                text=text,
                font=cfg.bezel_text_font,
                font_size=10.0,
                depth=depth,
                target_height_mm=target_h,
            )

            # Scale to target height (Y size)
            b = txt.bounds
            txt_h = b[1][1] - b[0][1]
            s = target_h / max(txt_h, 1e-6)
            txt.apply_scale([s, s, 1.0])

            # Clamp width
            b = txt.bounds
            txt_w = b[1][0] - b[0][0]
            max_w = plate_size - 2.0
            if txt_w > max_w:
                s2 = max_w / max(txt_w, 1e-6)
                txt.apply_scale([s2, s2, 1.0])

            # Center in bottom band
            b = txt.bounds
            bx = (b[0][0] + b[1][0]) / 2.0
            by = (b[0][1] + b[1][1]) / 2.0
            bz = (b[0][2] + b[1][2]) / 2.0

            cx = plate_size / 2.0
            cy = margin_mm / 2.0
            embed_mm = float(getattr(cfg, "bezel_text_embed_mm", 0.5))
            cz = plate_thickness + depth / 2.0 - embed_mm

            txt.apply_translation([cx - bx, cy - by, cz - bz])
            base = trimesh.util.concatenate([base, txt])

        except Exception as e:
            print("TEXT EMBOSS FAILED:", e)

    return base, plate_size, plate_thickness
