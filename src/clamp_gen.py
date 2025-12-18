"""
Edge block generator using OPEN SLOT receivers (no booleans).

Plates have studs.
Edge blocks have C-shaped slot receivers.

Pure Python:
- no trimesh booleans
- no earcut / triangle / manifold3d
- slicer-safe

Coordinate system:
- Block occupies:
    x:[0..B], y:[0..B], z:[0..L]
- L-profile:
    X-leg: x:[0..B], y:[0..T]
    Y-leg: x:[0..T], y:[0..B]
- Slots:
    * X-slots open on face x=0, run along +X
    * Y-slots open on face y=0, run along +Y
"""

from __future__ import annotations
from typing import List, Tuple
import numpy as np
import trimesh

from .mesh_utils import cleanup_mesh_portable


# ---------------- utility ----------------

def linspace_positions(length: float, count: int, margin: float) -> List[float]:
    if count < 2:
        raise ValueError("count must be >= 2")
    lo = margin
    hi = length - margin
    if hi <= lo:
        raise ValueError("margin too large")
    return np.linspace(lo, hi, count).tolist()


def add_quad(V, F, a, b, c, d, outward=True):
    i = len(V)
    V.extend([a, b, c, d])
    if outward:
        F.append([i, i+1, i+2])
        F.append([i, i+2, i+3])
    else:
        F.append([i, i+2, i+1])
        F.append([i, i+3, i+2])


# ---------------- slot geometry ----------------

def slot_profile_2d(
    radius: float,
    opening_width: float,
    sections: int = 32
) -> List[Tuple[float, float]]:
    """
    Returns a CLOSED 2D polyline for a C-shaped slot profile,
    centered at origin, opening to +X.

    The opening is flat; the back is circular.
    """
    theta = np.linspace(-np.pi/2, np.pi/2, sections)
    arc = [( -radius*np.cos(t), radius*np.sin(t)) for t in theta]

    half_open = opening_width / 2.0
    poly = []
    poly.append((0.0, -half_open))
    poly.extend(arc)
    poly.append((0.0, +half_open))
    poly.append((0.0, -half_open))
    return poly


def extrude_slot_along_x(
    verts, faces,
    profile_2d,
    x0: float,
    x1: float,
    y_offset: float,
    z_offset: float
):
    """
    Extrude a 2D slot profile along X from x0..x1.
    profile_2d is in (x,y) but here treated as (y,z).
    """
    n = len(profile_2d) - 1
    for i in range(n):
        (y0, z0) = profile_2d[i]
        (y1, z1) = profile_2d[i+1]

        add_quad(
            verts, faces,
            [x0, y_offset + y0, z_offset + z0],
            [x0, y_offset + y1, z_offset + z1],
            [x1, y_offset + y1, z_offset + z1],
            [x1, y_offset + y0, z_offset + z0],
            outward=False
        )


def extrude_slot_along_y(
    verts, faces,
    profile_2d,
    y0: float,
    y1: float,
    x_offset: float,
    z_offset: float
):
    n = len(profile_2d) - 1
    for i in range(n):
        (x0, z0) = profile_2d[i]
        (x1, z1) = profile_2d[i+1]

        add_quad(
            verts, faces,
            [x_offset + x0, y0, z_offset + z0],
            [x_offset + x1, y0, z_offset + z1],
            [x_offset + x1, y1, z_offset + z1],
            [x_offset + x0, y1, z_offset + z0],
            outward=False
        )


# ---------------- main generator ----------------

def generate_edge_block_slots(
    block_size_mm: float,
    leg_thickness_mm: float,
    length_mm: float,
    sockets_per_edge: int,
    socket_end_margin_mm: float,
    socket_offset_mm: float,
    stud_d_mm: float,
    slot_opening_clearance_mm: float = 0.6,
    sections: int = 32,
) -> trimesh.Trimesh:
    """
    L-shaped edge block with OPEN SLOT receivers.
    """
    B = float(block_size_mm)
    T = float(leg_thickness_mm)
    L = float(length_mm)
    r = stud_d_mm / 2.0

    V, F = [], []

    # ---- L-body as two overlapping boxes ----
    def box(x0, x1, y0, y1, z0, z1):
        # bottom z0
        add_quad(V, F, [x0,y0,z0],[x1,y0,z0],[x1,y1,z0],[x0,y1,z0], outward=False)
        # top z1
        add_quad(V, F, [x0,y0,z1],[x0,y1,z1],[x1,y1,z1],[x1,y0,z1], outward=True)
        # x1
        add_quad(V, F, [x1,y0,z0],[x1,y0,z1],[x1,y1,z1],[x1,y1,z0], outward=True)

        # x0  (REMOVE THIS FACE to keep slot mouth open on x=0)
        # add_quad(V,F,[x0,y0,z0],[x0,y1,z0],[x0,y1,z1],[x0,y0,z1], outward=False)

        # y1
        add_quad(V, F, [x0,y1,z0],[x1,y1,z0],[x1,y1,z1],[x0,y1,z1], outward=True)

        # y0  (REMOVE THIS FACE to keep slot mouth open on y=0)
        # add_quad(V,F,[x0,y0,z0],[x0,y0,z1],[x1,y0,z1],[x1,y0,z0], outward=False)


    box(0,B,0,T,0,L)
    box(0,T,0,B,0,L)

    # ---- slots ----
    z_positions = linspace_positions(L, sockets_per_edge, socket_end_margin_mm)

    slot_profile = slot_profile_2d(
        radius=r,
        opening_width=stud_d_mm + slot_opening_clearance_mm,
        sections=sections
    )

    for zc in z_positions:
        # X-slots (open on x=0)
        extrude_slot_along_x(
            V, F,
            slot_profile,
            x0=0.0,
            x1=T,
            y_offset=socket_offset_mm,
            z_offset=zc
        )

        # Y-slots (open on y=0)
        extrude_slot_along_y(
            V, F,
            slot_profile,
            y0=0.0,
            y1=T,
            x_offset=socket_offset_mm,
            z_offset=zc
        )

    mesh = trimesh.Trimesh(
        vertices=np.array(V, dtype=float),
        faces=np.array(F, dtype=int),
        process=False
    )
    return cleanup_mesh_portable(mesh)
