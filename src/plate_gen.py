"""
Universal plate (identical for all faces) with:
- 45° mitered perimeter (loft between outside outline and inside inset outline)
- studs on INSIDE face along all 4 edges (male)
- optional anti-elephant-foot relief on OUTSIDE perimeter
- optional reinforcement bosses at stud roots

Z convention (IMPORTANT):
- OUTSIDE face (ArUco side): z = 0
- INSIDE face:              z = thickness_mm
Studs protrude from the inside face to z > thickness_mm (into cube interior).

Printing recommendation:
- print OUTSIDE face down on the build plate for best marker flatness
- studs will print upward (no supports)
"""

from __future__ import annotations
from typing import List, Tuple, Iterable

import numpy as np
import trimesh
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import unary_union

from .mesh_utils import cleanup_mesh_portable, triangulate_polygon, square_ring


def circle_poly(x: float, y: float, d: float, resolution: int = 48) -> Polygon:
    return Point(x, y).buffer(d / 2.0, resolution=resolution)


def edge_feature_centers(
    size_mm: float,
    edge_offset_mm: float,
    count_per_edge: int,
    end_margin_mm: float,
) -> List[Tuple[float, float]]:
    """
    Symmetric feature centers along all 4 edges.
    edge_offset_mm is distance from the outer edge toward the center.
    """
    if count_per_edge < 2:
        raise ValueError("count_per_edge must be >= 2")

    h = size_mm / 2.0
    o = edge_offset_mm
    m = end_margin_mm

    lo = -h + m
    hi = +h - m
    if hi <= lo:
        raise ValueError("end_margin_mm too large")

    ts = np.linspace(lo, hi, count_per_edge).tolist()

    pts = []
    # N edge (y = +h - o)
    for x in ts:
        pts.append((x, +h - o))
    # S edge (y = -h + o)
    for x in ts:
        pts.append((x, -h + o))
    # E edge (x = +h - o)
    for y in ts:
        pts.append((+h - o, y))
    # W edge (x = -h + o)
    for y in ts:
        pts.append((-h + o, y))

    # Deduplicate
    uniq, seen = [], set()
    for (x, y) in pts:
        key = (round(x, 4), round(y, 4))
        if key not in seen:
            seen.add(key)
            uniq.append((x, y))
    return uniq


def _add_tri(verts, faces, tri2d: Polygon, z: float, flip: bool) -> None:
    coords = np.array(tri2d.exterior.coords)[:-1]
    i0 = len(verts)
    for p in coords:
        verts.append([float(p[0]), float(p[1]), float(z)])
    if flip:
        faces.append([i0, i0 + 2, i0 + 1])
    else:
        faces.append([i0, i0 + 1, i0 + 2])


def _connect_rings(verts, faces, ring_a, z_a, ring_b, z_b, outward: bool = True) -> None:
    assert len(ring_a) == len(ring_b)
    for i in range(len(ring_a) - 1):
        ax0, ay0 = ring_a[i]
        ax1, ay1 = ring_a[i + 1]
        bx0, by0 = ring_b[i]
        bx1, by1 = ring_b[i + 1]

        base = len(verts)
        verts.extend([
            [ax0, ay0, z_a],
            [ax1, ay1, z_a],
            [bx1, by1, z_b],
            [bx0, by0, z_b],
        ])
        if outward:
            faces.append([base, base + 1, base + 2])
            faces.append([base, base + 2, base + 3])
        else:
            faces.append([base, base + 2, base + 1])
            faces.append([base, base + 3, base + 2])


def extrude_polygon_prismatic(poly: Polygon | MultiPolygon, height: float) -> trimesh.Trimesh:
    """
    Straight extrusion along +Z for polygons (supports holes).
    Uses shapely triangulate (no earcut dependency).
    """
    if poly.is_empty:
        return trimesh.Trimesh()

    tris = triangulate_polygon(poly)
    verts, faces = [], []

    for t in tris:
        _add_tri(verts, faces, t, 0.0, flip=True)
        _add_tri(verts, faces, t, height, flip=False)

    def walls(coords: Iterable[Tuple[float, float]]):
        coords = list(coords)
        for i in range(len(coords) - 1):
            x0, y0 = coords[i]
            x1, y1 = coords[i + 1]
            b = len(verts)
            verts.extend([
                [x0, y0, 0.0],
                [x1, y1, 0.0],
                [x1, y1, height],
                [x0, y0, height],
            ])
            faces.append([b, b + 1, b + 2])
            faces.append([b, b + 2, b + 3])

    def process(p: Polygon):
        walls(p.exterior.coords)
        for r in p.interiors:
            walls(r.coords)

    if isinstance(poly, Polygon):
        process(poly)
    else:
        for p in poly.geoms:
            process(p)

    m = trimesh.Trimesh(
        vertices=np.array(verts, dtype=float),
        faces=np.array(faces, dtype=int),
        process=False,
    )
    return cleanup_mesh_portable(m)


def _stud_mesh(d: float, length: float, tip_chamfer: float) -> trimesh.Trimesh:
    """
    Stud axis is +Z.
    Cylinder + small cone tip, stacked using actual mesh bounds (no floating parts).
    """
    r = d / 2.0
    tip_h = max(0.0, min(tip_chamfer, length * 0.8))
    cyl_h = max(0.0, length - tip_h)

    parts = []

    def z0_align(m: trimesh.Trimesh) -> trimesh.Trimesh:
        # shift so min z is 0
        minz = float(m.bounds[0][2])
        m.apply_translation([0.0, 0.0, -minz])
        return m

    if cyl_h > 0:
        cyl = trimesh.creation.cylinder(radius=r, height=cyl_h, sections=48)
        cyl = z0_align(cyl)
        parts.append(cyl)

    if tip_h > 0:
        cone = trimesh.creation.cone(radius=r, height=tip_h, sections=48)
        cone = z0_align(cone)
        # stack cone on top of cylinder
        cone.apply_translation([0.0, 0.0, cyl_h])
        parts.append(cone)

    return trimesh.util.concatenate(parts) if parts else trimesh.Trimesh()



def generate_universal_plate_white(
    size_mm: float,
    thickness_mm: float,
    miter_enabled: bool,
    # studs
    studs_per_edge: int,
    stud_end_margin_mm: float,
    stud_edge_offset_mm: float,
    stud_d_mm: float,
    stud_len_mm: float,
    stud_tip_chamfer_mm: float,
    # stud bosses
    stud_boss_outer_d_mm: float,
    stud_boss_height_mm: float,
    # relief
    relief_enabled: bool = True,
    relief_inset_mm: float = 0.25,
    relief_height_mm: float = 0.30,
) -> trimesh.Trimesh:
    """
    OUTSIDE face at z=0, INSIDE face at z=thickness_mm.
    """
    outside_size = size_mm
    inside_size = (size_mm - 2.0 * thickness_mm) if miter_enabled else size_mm
    if inside_size <= 0:
        raise ValueError("Thickness too large vs size for 45° miter loft.")

    # optional perimeter relief near outside face to absorb elephant-foot
    use_relief = (
        relief_enabled
        and relief_inset_mm > 0
        and relief_height_mm > 0
        and relief_height_mm < thickness_mm
        and (outside_size - 2.0 * relief_inset_mm) > 0
    )

    # plate surfaces (solid, no holes)
    outside_poly = Polygon(square_ring(outside_size)).buffer(0)
    inside_poly = Polygon(square_ring(inside_size)).buffer(0)

    outside_tris = triangulate_polygon(outside_poly)
    inside_tris = triangulate_polygon(inside_poly)

    verts, faces = [], []
    z_out = 0.0
    z_in = float(thickness_mm)

    # outside face (z=0) faces downward
    for t in outside_tris:
        _add_tri(verts, faces, t, z_out, flip=True)

    # inside face (z=thickness) faces upward
    for t in inside_tris:
        _add_tri(verts, faces, t, z_in, flip=False)

    # perimeter loft walls
    outside_ring = square_ring(outside_size)
    inside_ring = square_ring(inside_size)

    if use_relief:
        relief_size = outside_size - 2.0 * relief_inset_mm
        relief_ring = square_ring(relief_size)
        z_relief = z_out + relief_height_mm
        _connect_rings(verts, faces, outside_ring, z_out, relief_ring, z_relief, outward=True)
        _connect_rings(verts, faces, relief_ring, z_relief, inside_ring, z_in, outward=True)
    else:
        _connect_rings(verts, faces, outside_ring, z_out, inside_ring, z_in, outward=True)

    plate = trimesh.Trimesh(
        vertices=np.array(verts, dtype=float),
        faces=np.array(faces, dtype=int),
        process=False,
    )
    plate = cleanup_mesh_portable(plate)

    # studs and optional bosses at stud roots (inside face)
    centers = edge_feature_centers(
        size_mm=size_mm,
        edge_offset_mm=stud_edge_offset_mm,
        count_per_edge=studs_per_edge,
        end_margin_mm=stud_end_margin_mm,
    )

    stud_parts = []
    boss_parts = []

    for (x, y) in centers:
        s = _stud_mesh(stud_d_mm, stud_len_mm, stud_tip_chamfer_mm)
        # stud base starts at inside face (z=thickness)
        s.apply_translation([x, y, z_in])
        stud_parts.append(s)

        if stud_boss_outer_d_mm > stud_d_mm and stud_boss_height_mm > 0:
            outer = circle_poly(x, y, stud_boss_outer_d_mm)
            inner = circle_poly(x, y, stud_d_mm)
            annulus = outer.difference(inner).buffer(0)
            b = extrude_polygon_prismatic(annulus, stud_boss_height_mm)
            b.apply_translation([0, 0, z_in])  # sit on inside face
            boss_parts.append(b)

    if stud_parts or boss_parts:
        plate = trimesh.util.concatenate([plate] + boss_parts + stud_parts)
        plate = cleanup_mesh_portable(plate)

    return plate
