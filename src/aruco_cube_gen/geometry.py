"""
geometry.py

Mesh construction for:
- Hollow cube with recessed slots (requires trimesh boolean backend)
- Slot-fit plate base with bezel + optional embossed ID text

This iteration:
- Slots are tapered (miter/draft) on ALL four side edges (printing-friendly)
- Plates are tapered to match (print new plates if you changed taper)
- Roof thickener (+cfg.roof_extra_thickness_mm) adds material from inside
- Shallow attic roof reduces long bridging and stiffens roof
- IMPORTANT FIX: attic/slab solids are trimmed with a TOP-SLOT keepout volume
  so the top slot surface stays planar/flat and isn't "re-added" by unions.

All dimensions are in millimeters.
"""

from __future__ import annotations

import numpy as np
import trimesh

from .config import Config
from .text3d import make_text_mesh


# -------------------------
# Basic helpers
# -------------------------

def make_box(extents, center) -> trimesh.Trimesh:
    box = trimesh.creation.box(extents=extents)
    box.apply_translation(np.asarray(center) - box.center_mass)
    return box


def _bool_difference(a: trimesh.Trimesh, b: trimesh.Trimesh, what: str) -> trimesh.Trimesh:
    try:
        return a.difference(b)
    except Exception as e:
        raise RuntimeError(
            f"Boolean difference failed while {what}.\n"
            "You likely need a trimesh boolean backend (e.g., OpenSCAD).\n"
            f"Original error: {e}"
        )


def _bool_union(a: trimesh.Trimesh, b: trimesh.Trimesh, what: str) -> trimesh.Trimesh:
    try:
        return a.union([b])
    except Exception as e:
        raise RuntimeError(
            f"Boolean union failed while {what}.\n"
            "You likely need a trimesh boolean backend (e.g., OpenSCAD).\n"
            f"Original error: {e}"
        )


def _sanitize(mesh: trimesh.Trimesh, name: str) -> trimesh.Trimesh:
    """
    Try to make a mesh more boolean-friendly.
    This does NOT guarantee is_volume=True, but helps with custom meshes.
    """
    m = mesh.copy()

    try:
        m.remove_duplicate_faces()
    except Exception:
        pass
    try:
        m.remove_degenerate_faces()
    except Exception:
        pass
    try:
        m.merge_vertices()
    except Exception:
        pass
    try:
        m.fix_normals()
    except Exception:
        pass
    try:
        m.fill_holes()
    except Exception:
        pass

    try:
        m.process(validate=False)
    except Exception:
        pass

    return m


# -------------------------
# Tapered prism (frustum) generator
# -------------------------

def make_tapered_prism(
    depth: float,
    size_open_a: float,
    size_open_b: float,
    taper_mm: float,
    axis: str,
    open_positive: bool = True,
) -> trimesh.Trimesh:
    """
    Create a tapered rectangular prism (frustum) along `axis`.

    Opening face:
      size_open_a x size_open_b

    Inner face:
      (size_open_a - 2*taper_mm) x (size_open_b - 2*taper_mm)

    For a true 45° miter: taper_mm == depth.

    axis: 'x' (depth along x), 'y', 'z'
    open_positive: opening face is on +axis side if True, else on -axis side

    Returns mesh centered at origin.
    """
    d = float(depth)
    a0 = float(size_open_a)
    b0 = float(size_open_b)
    t = float(taper_mm)

    # Prevent inverted/degenerate shapes
    a1 = max(0.8, a0 - 2.0 * t)
    b1 = max(0.8, b0 - 2.0 * t)

    hi = +d / 2.0
    lo = -d / 2.0
    if not open_positive:
        hi, lo = lo, hi

    A0 = a0 / 2.0
    B0 = b0 / 2.0
    A1 = a1 / 2.0
    B1 = b1 / 2.0

    if axis == "x":
        verts = np.array([
            [hi, +A0, +B0],
            [hi, -A0, +B0],
            [hi, -A0, -B0],
            [hi, +A0, -B0],
            [lo, +A1, +B1],
            [lo, -A1, +B1],
            [lo, -A1, -B1],
            [lo, +A1, -B1],
        ], dtype=float)
    elif axis == "y":
        verts = np.array([
            [+A0, hi, +B0],
            [-A0, hi, +B0],
            [-A0, hi, -B0],
            [+A0, hi, -B0],
            [+A1, lo, +B1],
            [-A1, lo, +B1],
            [-A1, lo, -B1],
            [+A1, lo, -B1],
        ], dtype=float)
    elif axis == "z":
        verts = np.array([
            [+A0, +B0, hi],
            [-A0, +B0, hi],
            [-A0, -B0, hi],
            [+A0, -B0, hi],
            [+A1, +B1, lo],
            [-A1, +B1, lo],
            [-A1, -B1, lo],
            [+A1, -B1, lo],
        ], dtype=float)
    else:
        raise ValueError("axis must be 'x', 'y', or 'z'")

    faces = np.array([
        # Opening face
        [0, 1, 2], [0, 2, 3],

        # Inner face (reverse winding)
        [4, 6, 5], [4, 7, 6],

        # Side faces
        [0, 4, 5], [0, 5, 1],
        [1, 5, 6], [1, 6, 2],
        [2, 6, 7], [2, 7, 3],
        [3, 7, 4], [3, 4, 0],
    ], dtype=int)

    m = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    return _sanitize(m, name=f"tapered_prism_{axis}")


# -------------------------
# Internal roof thickener + attic (ADD material)
# with TOP SLOT KEEPOUT FIX
# -------------------------

def add_roof_thickener_and_attic(shell: trimesh.Trimesh, cfg: Config) -> trimesh.Trimesh:
    """
    Adds material to the INSIDE of the cube:
    - roof thickener slab (+cfg.roof_extra_thickness_mm)
    - attic slopes along all 4 interior walls

    FIX: trims those additive solids with a top-slot keepout volume so the
    slot cavity stays planar and doesn't get "re-added" by unions.
    """
    ce = cfg.cube_edge
    wt = cfg.wall_thickness
    inner_span = ce - 2 * wt
    if inner_span <= 0:
        return shell

    roof_inner_z = ce / 2 - wt

    extra_t = float(getattr(cfg, "roof_extra_thickness_mm", 0.0))
    attic_drop = float(getattr(cfg, "attic_drop_mm", 0.0))
    attic_margin = float(getattr(cfg, "attic_margin_mm", 0.5))

    out = shell

    # --- Top slot keepout (protect slot cavity from attic/slab unions) ---
    slot_size = ce * cfg.slot_fraction
    d = cfg.slot_depth
    keepout_margin = float(getattr(cfg, "attic_keepout_margin_mm", 1.0))
    keepout_xy = slot_size + 2.0 * keepout_margin

    keepout = make_box(
        extents=(keepout_xy, keepout_xy, d + 0.6),
        center=[0.0, 0.0, ce / 2 - d / 2],
    )
    keepout = _sanitize(keepout, "top_slot_keepout")

    # 1) Roof thickener
    if extra_t > 1e-6:
        slab = make_box(
            extents=(inner_span, inner_span, extra_t),
            center=[0.0, 0.0, roof_inner_z - extra_t / 2],
        )
        slab = _sanitize(slab, "roof_thickener_slab")
        slab = _bool_difference(slab, keepout, what="trimming roof slab away from top slot")
        out = _bool_union(out, slab, what="adding roof thickener slab")

    # 2) Attic slopes
    if attic_drop > 1e-6:
        run = inner_span / 2.0 + attic_margin
        run = max(1.0, min(run, inner_span))
        theta = np.arctan2(attic_drop, run)

        def ramp_y(sign: int) -> trimesh.Trimesh:
            r = trimesh.creation.box(extents=(inner_span, run, attic_drop))
            ang = -theta if sign > 0 else +theta
            r.apply_transform(trimesh.transformations.rotation_matrix(ang, [1, 0, 0]))
            y = sign * (inner_span / 2 - run / 2)
            z = roof_inner_z - attic_drop / 2
            r.apply_translation([0.0, y, z])
            return _sanitize(r, f"attic_ramp_y_{sign}")

        def ramp_x(sign: int) -> trimesh.Trimesh:
            r = trimesh.creation.box(extents=(run, inner_span, attic_drop))
            ang = +theta if sign > 0 else -theta
            r.apply_transform(trimesh.transformations.rotation_matrix(ang, [0, 1, 0]))
            x = sign * (inner_span / 2 - run / 2)
            z = roof_inner_z - attic_drop / 2
            r.apply_translation([x, 0.0, z])
            return _sanitize(r, f"attic_ramp_x_{sign}")

        for solid in [ramp_y(+1), ramp_y(-1), ramp_x(+1), ramp_x(-1)]:
            solid = _bool_difference(solid, keepout, what="trimming attic slope away from top slot")
            out = _bool_union(out, solid, what="adding attic slope")

    return out


# -------------------------
# Cube
# -------------------------

def create_cube_with_slots(cfg: Config) -> trimesh.Trimesh:
    ce = cfg.cube_edge
    wt = cfg.wall_thickness

    outer = trimesh.creation.box(extents=(ce, ce, ce))
    inner = trimesh.creation.box(extents=(ce - 2 * wt, ce - 2 * wt, ce - 2 * wt))
    shell = _bool_difference(outer, inner, what="hollowing cube")

    slot_size = ce * cfg.slot_fraction
    d = cfg.slot_depth

    taper = float(getattr(cfg, "slot_miter_mm", d))
    taper = max(0.0, min(taper, d))

    # --- Slot cutters (tapered), SEQUENTIAL differences ---
    top_slot = make_tapered_prism(d, slot_size, slot_size, taper, axis="z", open_positive=True)
    top_slot.apply_translation([0.0, 0.0, ce / 2 - d / 2])
    shell = _bool_difference(shell, top_slot, what="cutting top tapered slot")

    posx_slot = make_tapered_prism(d, slot_size, slot_size, taper, axis="x", open_positive=True)
    posx_slot.apply_translation([ce / 2 - d / 2, 0.0, 0.0])
    shell = _bool_difference(shell, posx_slot, what="cutting +X tapered slot")

    negx_slot = make_tapered_prism(d, slot_size, slot_size, taper, axis="x", open_positive=False)
    negx_slot.apply_translation([-ce / 2 + d / 2, 0.0, 0.0])
    shell = _bool_difference(shell, negx_slot, what="cutting -X tapered slot")

    posy_slot = make_tapered_prism(d, slot_size, slot_size, taper, axis="y", open_positive=True)
    posy_slot.apply_translation([0.0, ce / 2 - d / 2, 0.0])
    shell = _bool_difference(shell, posy_slot, what="cutting +Y tapered slot")

    negy_slot = make_tapered_prism(d, slot_size, slot_size, taper, axis="y", open_positive=False)
    negy_slot.apply_translation([0.0, -ce / 2 + d / 2, 0.0])
    shell = _bool_difference(shell, negy_slot, what="cutting -Y tapered slot")

    # Optional: open bottom, leaving a rim
    if getattr(cfg, "open_bottom", False):
        rim_w = cfg.bottom_rim_width if getattr(cfg, "bottom_rim_width", 0.0) > 0 else wt
        inner_xy = ce - 2 * rim_w
        if inner_xy <= 0:
            raise ValueError(f"bottom_rim_width too large ({rim_w}); must be < {ce/2}")

        floor_t = wt
        cut = make_box(
            extents=(inner_xy, inner_xy, floor_t + 0.4),
            center=[0.0, 0.0, -ce / 2 + (floor_t + 0.4) / 2],
        )
        cut = _sanitize(cut, "bottom_open_cut")
        shell = _bool_difference(shell, cut, what="opening bottom interior panel")

    # Add roof thickener + attic roof (ADD material)
    shell = add_roof_thickener_and_attic(shell, cfg)

    # Cleanup helps slicers
    try:
        shell.process(validate=True)
    except Exception:
        shell.process(validate=False)

    # Move cube so bottom rests on z=0
    min_z = shell.bounds[0][2]
    shell.apply_translation([0.0, 0.0, -min_z])

    return shell


# -------------------------
# Plate base (matching taper)
# -------------------------

def create_plate_base(cfg: Config, text: str | None):
    """
    Plate plug is tapered to match the slot.

    Slot:
      opening = slot_size
      inner   = slot_size - 2*taper

    Plate plug:
      opening = slot_size - 2*clearance
      inner   = (slot_size - 2*taper) - 2*clearance

    This keeps the same clearance at the opening and at full depth.
    """
    slot_size = cfg.cube_edge * cfg.slot_fraction
    d = cfg.slot_depth

    taper = float(getattr(cfg, "slot_miter_mm", d))
    taper = max(0.0, min(taper, d))

    plate_open = slot_size - 2.0 * cfg.clearance
    plate_inner = max(1.0, (slot_size - 2.0 * taper) - 2.0 * cfg.clearance)

    # Convert that into an actual taper for the plate plug geometry
    plate_taper = (plate_open - plate_inner) / 2.0

    plug = make_tapered_prism(
        depth=d,
        size_open_a=plate_open,
        size_open_b=plate_open,
        taper_mm=plate_taper,
        axis="z",
        open_positive=True,
    )

    # Translate so plug occupies x,y >= 0 and z>=0 (lower-left origin)
    b = plug.bounds
    plug.apply_translation([-b[0][0], -b[0][1], -b[0][2]])

    plate_size = plate_open
    plate_thickness = d

    # Bezel flange (sits on cube face)
    bezel_outer = slot_size + 2.0 * cfg.bezel_overhang
    bezel_t = min(cfg.bezel_thickness, plate_thickness)

    bezel = trimesh.creation.box(extents=(bezel_outer, bezel_outer, bezel_t))
    bezel.apply_translation([plate_size / 2, plate_size / 2, plate_thickness - bezel_t / 2])

    base = trimesh.util.concatenate([plug, bezel])

    # Optional embossed ID text in bottom quiet band
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

            # Scale to target height
            tb = txt.bounds
            txt_h = tb[1][1] - tb[0][1]
            s = target_h / max(txt_h, 1e-6)
            txt.apply_scale([s, s, 1.0])

            # Clamp width
            tb = txt.bounds
            txt_w = tb[1][0] - tb[0][0]
            max_w = plate_size - 2.0
            if txt_w > max_w:
                s2 = max_w / max(txt_w, 1e-6)
                txt.apply_scale([s2, s2, 1.0])

            # Center in bottom band
            tb = txt.bounds
            bx = (tb[0][0] + tb[1][0]) / 2.0
            by = (tb[0][1] + tb[1][1]) / 2.0
            bz = (tb[0][2] + tb[1][2]) / 2.0

            cx = plate_size / 2.0
            cy = margin_mm / 2.0
            EMBED_MM = 0.5
            cz = plate_thickness + depth / 2.0 - EMBED_MM

            txt.apply_translation([cx - bx, cy - by, cz - bz])
            base = trimesh.util.concatenate([base, txt])

        except Exception as e:
            print("TEXT EMBOSS FAILED:", e)

    return base, plate_size, plate_thickness
