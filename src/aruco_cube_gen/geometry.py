"""
geometry.py

Cube:
- Hollow cube shell with 5 face slots (top, ±X, ±Y)
- Slots are tapered/mitered via slot_miter_mm (same on all faces)
- TOP follows the recipe:
  1) Build top slot exactly like a side-wall slot (same cutter)
  2) Remove only the flat slot floor inside the mitered edge, creating an opening into the cube
     while keeping the mitered/tapered walls as the seating surface.
  This avoids "printing in air" because the seating surface is a continuous slope.

Plates:
- create_plate_base kept intact: plug + bezel base, tapered to match slot taper, optional ID text.

All dimensions are in millimeters.
"""

from __future__ import annotations

import numpy as np
import trimesh

from .config import Config
from .text3d import make_text_mesh


# -------------------------
# Helpers
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
# Tapered prism (frustum)
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
    Returns mesh centered at origin.
    """
    d = float(depth)
    a0 = float(size_open_a)
    b0 = float(size_open_b)
    t = float(taper_mm)

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
# Cube
# -------------------------

def create_cube_with_slots(cfg: Config) -> trimesh.Trimesh:
    ce = float(cfg.cube_edge)
    wt = float(cfg.wall_thickness)

    outer = trimesh.creation.box(extents=(ce, ce, ce))
    inner = trimesh.creation.box(extents=(ce - 2.0 * wt, ce - 2.0 * wt, ce - 2.0 * wt))
    shell = _bool_difference(outer, inner, what="hollowing cube")

    slot_size = ce * float(cfg.slot_fraction)
    d = float(cfg.slot_depth)

    taper = float(getattr(cfg, "slot_miter_mm", 0.0))
    taper = max(0.0, min(taper, d))

    # --- Slots (tapered), SEQUENTIAL differences ---

    # Top slot: identical cutter to side wall slot geometry
    top_slot = make_tapered_prism(d, slot_size, slot_size, taper, axis="z", open_positive=True)
    top_slot.apply_translation([0.0, 0.0, ce / 2.0 - d / 2.0])
    shell = _bool_difference(shell, top_slot, what="cutting top slot")

    # Recipe step: remove ONLY the flat slot floor inside the mitered edge (make top open)
    if getattr(cfg, "top_open_remove_floor", False):
        inner_open = slot_size - 2.0 * taper
        inner_open = max(1.0, inner_open - 2.0 * float(getattr(cfg, "top_open_inner_margin_mm", 0.0)))

        # We cut from the slot floor plane downward into the cube interior.
        z_floor = ce / 2.0 - d
        height = (z_floor - (-ce / 2.0 + wt)) + 0.8  # reach into interior
        height = max(1.0, min(height, ce))

        z_center = (-ce / 2.0 + wt + z_floor) / 2.0

        thru = make_box(
            extents=(inner_open, inner_open, height),
            center=[0.0, 0.0, z_center],
        )
        thru = _sanitize(thru, "top_open_through_cut")
        shell = _bool_difference(shell, thru, what="opening top by removing slot floor only")
        # Additive-only: continuous perimeter ramp below the slot floor (no changes above)
        shell = _add_top_support_ramp_perimeter(shell, cfg)

    # +X slot
    posx_slot = make_tapered_prism(d, slot_size, slot_size, taper, axis="x", open_positive=True)
    posx_slot.apply_translation([ce / 2.0 - d / 2.0, 0.0, 0.0])
    shell = _bool_difference(shell, posx_slot, what="cutting +X slot")

    # -X slot
    negx_slot = make_tapered_prism(d, slot_size, slot_size, taper, axis="x", open_positive=False)
    negx_slot.apply_translation([-ce / 2.0 + d / 2.0, 0.0, 0.0])
    shell = _bool_difference(shell, negx_slot, what="cutting -X slot")

    # +Y slot
    posy_slot = make_tapered_prism(d, slot_size, slot_size, taper, axis="y", open_positive=True)
    posy_slot.apply_translation([0.0, ce / 2.0 - d / 2.0, 0.0])
    shell = _bool_difference(shell, posy_slot, what="cutting +Y slot")

    # -Y slot
    negy_slot = make_tapered_prism(d, slot_size, slot_size, taper, axis="y", open_positive=False)
    negy_slot.apply_translation([0.0, -ce / 2.0 + d / 2.0, 0.0])
    shell = _bool_difference(shell, negy_slot, what="cutting -Y slot")

    # Open bottom, leaving a rim
    if getattr(cfg, "open_bottom", False):
        rim_w = float(getattr(cfg, "bottom_rim_width", wt))
        rim_w = rim_w if rim_w > 0 else wt
        inner_xy = ce - 2.0 * rim_w
        if inner_xy <= 0:
            raise ValueError(f"bottom_rim_width too large ({rim_w}); must be < {ce/2}")

        cut = make_box(
            extents=(inner_xy, inner_xy, wt + 0.6),
            center=[0.0, 0.0, -ce / 2.0 + (wt + 0.6) / 2.0],
        )
        cut = _sanitize(cut, "bottom_open_cut")
        shell = _bool_difference(shell, cut, what="opening bottom interior panel")

    # Cleanup helps slicers
    try:
        shell.process(validate=True)
    except Exception:
        shell.process(validate=False)

    # Move cube so bottom rests on z=0
    shell.apply_translation([0.0, 0.0, -shell.bounds[0][2]])
    return shell


# -------------------------
# Additive support ramp BELOW top slot floor (continuous perimeter, no changes above)
# -------------------------

def _add_top_support_ramp_perimeter(shell: trimesh.Trimesh, cfg: Config) -> trimesh.Trimesh:
    """
    ADD (union) a single continuous 45° perimeter ramp *below* the top slot floor.

    Requirement (per your recipe):
      - Do not change anything above the slot floor plane (z_floor).
      - Only add material at z <= z_floor.
      - Ramp starts lower, and each higher layer extends inward, reaching the inner edge of the
        slot-floor opening exactly at z_floor (i.e., a gradual 45° ramp, not a sudden ledge).

    Geometry:
      z_floor = cube_edge/2 - slot_depth
      inner_open = slot_size - 2*slot_miter_mm  (innermost opening at the slot floor)
      inner_span = cube_edge - 2*wall_thickness (between inner walls)
      dist = (inner_span - inner_open)/2

    For a 45° ramp:
      ramp_height = dist
      z_start = z_floor - dist

    We construct:
      outer_block: (inner_span x inner_span x ramp_height)
      inner_frustum_cut: bottom opening slightly smaller than inner_span (by start_inset),
                         top opening equals inner_open
      ramp = outer_block - inner_frustum_cut

    This produces a continuous sloped inner surface around the whole perimeter (no corner islands),
    eliminating the sudden “floating cantilever” onset.
    """
    if not getattr(cfg, "top_support_ramps_enabled", True):
        return shell

    ce = float(cfg.cube_edge)
    wt = float(cfg.wall_thickness)
    d = float(cfg.slot_depth)

    slot_size = ce * float(cfg.slot_fraction)
    taper = float(getattr(cfg, "slot_miter_mm", 0.0))
    taper = max(0.0, min(taper, d))

    inner_open = slot_size - 2.0 * taper
    inner_span = ce - 2.0 * wt
    if inner_open <= 1.0 or inner_span <= 1.0:
        return shell

    dist = (inner_span - inner_open) / 2.0
    if dist <= 0.8:
        return shell

    # Slot floor plane
    z_floor = ce / 2.0 - d

    ramp_h = dist  # 45°: rise == run
    z_center = z_floor - ramp_h / 2.0

    start_inset = float(getattr(cfg, "top_ramp_start_inset_mm", 0.4))
    start_inset = max(0.2, min(start_inset, dist * 0.8))

    # Outer block fills full interior span for the ramp height
    outer_block = make_box(
        extents=(inner_span, inner_span, ramp_h),
        center=[0.0, 0.0, z_center],
    )
    outer_block = _sanitize(outer_block, "top_ramp_outer_block")

    # Inner frustum cut: bottom opening close to inner_span, top opening == inner_open
    bottom_open = max(1.0, inner_span - 2.0 * start_inset)
    top_open = max(1.0, inner_open)

    # taper needed so that (bottom_open - 2*taper_needed) == top_open
    taper_needed = max(0.0, (bottom_open - top_open) / 2.0)

    inner_cut = make_tapered_prism(
        depth=ramp_h,
        size_open_a=bottom_open,
        size_open_b=bottom_open,
        taper_mm=taper_needed,
        axis="z",
        open_positive=False,  # opening on -Z (bottom), smaller at +Z (top)
    )
    inner_cut.apply_translation([0.0, 0.0, z_center])
    inner_cut = _sanitize(inner_cut, "top_ramp_inner_frustum_cut")

    ramp_ring = _bool_difference(outer_block, inner_cut, what="creating top perimeter ramp ring")
    ramp_ring = _sanitize(ramp_ring, "top_perimeter_ramp_ring")

    # Union only (additive)
    return _bool_union(shell, ramp_ring, what="adding top perimeter ramp ring")


# -------------------------
# Plate base (UNCHANGED)
# -------------------------

def create_plate_base(cfg: Config, text: str | None):
    """
    Plate plug is tapered to match the slot.
    """
    slot_size = float(cfg.cube_edge) * float(cfg.slot_fraction)
    d = float(cfg.slot_depth)

    taper = float(getattr(cfg, "slot_miter_mm", 0.0))
    taper = max(0.0, min(taper, d))

    plate_open = slot_size - 2.0 * float(cfg.clearance)
    plate_inner = max(1.0, (slot_size - 2.0 * taper) - 2.0 * float(cfg.clearance))

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
    bezel_outer = slot_size + 2.0 * float(cfg.bezel_overhang)
    bezel_t = min(float(cfg.bezel_thickness), plate_thickness)

    bezel = trimesh.creation.box(extents=(bezel_outer, bezel_outer, bezel_t))
    bezel.apply_translation([plate_size / 2.0, plate_size / 2.0, plate_thickness - bezel_t / 2.0])

    base = trimesh.util.concatenate([plug, bezel])

    # Optional embossed ID text in bottom quiet band
    if text and getattr(cfg, "bezel_text_enabled", False):
        try:
            marker_area = plate_size * float(cfg.plate_margin_fraction)
            margin_mm = (plate_size - marker_area) / 2.0

            target_h = min(float(cfg.bezel_text_height_mm), max(2.0, margin_mm - 1.0))
            depth = max(0.8, float(cfg.bezel_text_depth_mm))

            txt = make_text_mesh(
                text=text,
                font=getattr(cfg, "bezel_text_font", None),
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
