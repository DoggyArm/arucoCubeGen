#!/usr/bin/env python3
import os
import argparse
import numpy as np
import trimesh
import cv2


def clean_mesh(m: trimesh.Trimesh) -> trimesh.Trimesh:
    """
    Tries to do the equivalent of:
      merge_vertices + remove_duplicate_faces + remove_degenerate_faces
    but works across older trimesh versions too.
    """
    # merge vertices (available broadly)
    try:
        m.merge_vertices()
    except Exception:
        pass

    # remove duplicate faces (compat)
    try:
        m.remove_duplicate_faces()
    except Exception:
        try:
            # older trimesh way
            m.update_faces(m.unique_faces())
        except Exception:
            pass

    # remove degenerate faces (compat)
    try:
        m.remove_degenerate_faces()
    except Exception:
        try:
            # drop faces with near-zero area
            ok = m.area_faces > 1e-12
            m.update_faces(ok)
        except Exception:
            pass

    # final cleanup
    try:
        m.remove_unreferenced_vertices()
    except Exception:
        pass

    return m


# -----------------------------
# ArUco helpers
# -----------------------------
def get_aruco_dict(dict_name: str):
    # Common choices: DICT_4X4_50, DICT_4X4_100, DICT_5X5_50, etc.
    if not hasattr(cv2.aruco, dict_name):
        raise ValueError(f"Unknown ArUco dictionary: {dict_name}")
    return cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, dict_name))


def aruco_to_cell_grid(dictionary, marker_id: int, grid_n: int, pixels: int = 600) -> np.ndarray:
    """
    Generate an ArUco marker image, then downsample it into a grid_n x grid_n boolean grid:
    True => black cell, False => white cell.

    NOTE:
    - For DICT_4X4_* markers, the logical grid is typically 6x6 (4 bits + 1-cell border on each side).
    - For DICT_5X5_* => 7x7, etc.
    If you aren't sure, start with:
      4x4 -> grid_n=6
      5x5 -> grid_n=7
      6x6 -> grid_n=8
      7x7 -> grid_n=9
    """
    img = cv2.aruco.generateImageMarker(dictionary, marker_id, pixels)
    # img is 0 (black) / 255 (white)
    img = img.astype(np.uint8)

    # Downsample by averaging blocks into grid cells
    h, w = img.shape
    cell_h = h // grid_n
    cell_w = w // grid_n

    grid = np.zeros((grid_n, grid_n), dtype=bool)
    for r in range(grid_n):
        for c in range(grid_n):
            block = img[r * cell_h:(r + 1) * cell_h, c * cell_w:(c + 1) * cell_w]
            mean = float(block.mean())
            # mean near 0 => black
            grid[r, c] = (mean < 128.0)
    return grid


# -----------------------------
# Geometry helpers
# -----------------------------
def make_box(extents, center):
    mesh = trimesh.creation.box(extents=extents)
    mesh.apply_translation(center)
    return mesh


def face_frame(normal: np.ndarray):
    """
    Build a right-handed orthonormal frame (u, v, n) for a given face normal.
    u and v span the face plane.
    """
    n = normal / np.linalg.norm(normal)
    # pick an arbitrary vector not parallel to n
    a = np.array([0.0, 0.0, 1.0])
    if abs(np.dot(a, n)) > 0.95:
        a = np.array([0.0, 1.0, 0.0])
    u = np.cross(a, n)
    u = u / np.linalg.norm(u)
    v = np.cross(n, u)
    v = v / np.linalg.norm(v)
    return u, v, n


def build_open_top_hollow_cube(outer_L: float, wall_t: float) -> trimesh.Trimesh:
    """
    Build a hollow cube with top face missing using 5 wall boxes (no booleans).
    Outer dimensions: outer_L x outer_L x outer_L
    Wall thickness: wall_t
    """
    L = float(outer_L)
    t = float(wall_t)
    half = L / 2.0

    parts = []

    # Bottom wall (z-)
    parts.append(make_box(
        extents=[L, L, t],
        center=[0.0, 0.0, -(half - t / 2.0)]
    ))

    # Side walls
    # +X
    parts.append(make_box(
        extents=[t, L, L],
        center=[+(half - t / 2.0), 0.0, 0.0]
    ))
    # -X
    parts.append(make_box(
        extents=[t, L, L],
        center=[-(half - t / 2.0), 0.0, 0.0]
    ))
    # +Y
    parts.append(make_box(
        extents=[L, t, L],
        center=[0.0, +(half - t / 2.0), 0.0]
    ))
    # -Y
    parts.append(make_box(
        extents=[L, t, L],
        center=[0.0, -(half - t / 2.0), 0.0]
    ))

    cube = trimesh.util.concatenate(parts)
    cube = clean_mesh(cube)
    return cube


def build_marker_tiles_on_face(
    grid_black: np.ndarray,
    marker_size_mm: float,
    tile_thickness_mm: float,
    face_center: np.ndarray,
    face_normal: np.ndarray,
    inset_mm: float = 0.0,
):
    """
    Create black tile boxes for each black cell of the marker grid.
    Tiles are raised outward by tile_thickness_mm and "sit" on the face.
    inset_mm lets you shrink the marker slightly to leave a quiet margin around it.
    """
    grid_n = grid_black.shape[0]
    u, v, n = face_frame(face_normal)

    usable = marker_size_mm - 2.0 * inset_mm
    if usable <= 0:
        raise ValueError("inset_mm too large for marker_size_mm")

    cell = usable / grid_n
    tiles = []

    # Marker plane origin (top-left corner in (u,v) coords)
    # We'll place marker centered at face_center, spanning [-usable/2, +usable/2] in u and v.
    origin = face_center - u * (usable / 2.0) + v * (usable / 2.0)

    for r in range(grid_n):
        for c in range(grid_n):
            if not grid_black[r, c]:
                continue

            # center of this cell in world coordinates
            # move right with +u, move down with -v
            cell_center = (
                origin
                + u * (c * cell + cell / 2.0)
                - v * (r * cell + cell / 2.0)
            )

            EMBED_MM = 0.4
            tile_center = cell_center + n * (tile_thickness_mm / 2.0 - EMBED_MM)




            # create an axis-aligned box, then rotate into face frame
            tile = trimesh.creation.box(extents=[cell, cell, tile_thickness_mm])

            # Build transform that maps tile local axes to (u, v, n)
            # Local x->u, local y->v, local z->n
            R = np.eye(4)
            R[:3, :3] = np.column_stack([u, v, n])
            tile.apply_transform(R)

            # Then translate into place
            tile.apply_translation(tile_center)

            tiles.append(tile)

    if not tiles:
        return None

    marker_mesh = trimesh.util.concatenate(tiles)
    marker_mesh = clean_mesh(marker_mesh)
    markers = clean_mesh(marker_mesh)
    return marker_mesh


def build_markers_for_cube(
    outer_L: float,
    marker_size_mm: float,
    tile_thickness_mm: float,
    dict_name: str,
    ids_by_face: dict,
    grid_n: int,
    inset_mm: float,
):
    """
    Place markers on 5 faces (no top):
      -Z bottom
      +X right
      -X left
      +Y front
      -Y back
    """
    L = float(outer_L)
    half = L / 2.0

    dictionary = get_aruco_dict(dict_name)

    faces = {
        "-Z": (np.array([0.0, 0.0, -1.0]), np.array([0.0, 0.0, -half])),
        "+X": (np.array([+1.0, 0.0, 0.0]), np.array([+half, 0.0, 0.0])),
        "-X": (np.array([-1.0, 0.0, 0.0]), np.array([-half, 0.0, 0.0])),
        "+Y": (np.array([0.0, +1.0, 0.0]), np.array([0.0, +half, 0.0])),
        "-Y": (np.array([0.0, -1.0, 0.0]), np.array([0.0, -half, 0.0])),
    }

    all_parts = []
    for face_key, (n, center) in faces.items():
        marker_id = ids_by_face.get(face_key, None)
        if marker_id is None:
            continue

        grid_black = aruco_to_cell_grid(dictionary, marker_id, grid_n=grid_n, pixels=800)

        m = build_marker_tiles_on_face(
            grid_black=grid_black,
            marker_size_mm=marker_size_mm,
            tile_thickness_mm=tile_thickness_mm,
            face_center=center,
            face_normal=n,
            inset_mm=inset_mm,
        )
        if m is not None:
            all_parts.append(m)

    if not all_parts:
        return None

    marker_mesh = trimesh.util.concatenate(all_parts)
    marker_mesh = clean_mesh(marker_mesh)
    marker_mesh = clean_mesh(marker_mesh)
    return marker_mesh


# -----------------------------
# Main
# -----------------------------
def parse_face_ids(s: str):
    """
    Parse like: "-Z:0,+X:1,-X:2,+Y:3,-Y:4"
    """
    out = {}
    if not s.strip():
        return out
    for token in s.split(","):
        k, v = token.split(":")
        out[k.strip()] = int(v.strip())
    return out


def main():
    ap = argparse.ArgumentParser(description="Generate an open-top hollow cube + separate ArUco marker tiles (AMS 2-color).")
    ap.add_argument("--out", default="out_test_cube", help="Output directory")
    ap.add_argument("--outer", type=float, default=60.0, help="Outer cube size (mm)")
    ap.add_argument("--wall", type=float, default=3.0, help="Wall thickness (mm)")
    ap.add_argument("--marker", type=float, default=40.0, help="Marker size (mm) on each face")
    ap.add_argument("--tile", type=float, default=0.6, help="Black tile thickness (mm), raised outward")
    ap.add_argument("--inset", type=float, default=0.5, help="Shrink marker by this margin (mm) to leave a quiet white border")
    ap.add_argument("--dict", default="DICT_4X4_50", help="ArUco dictionary name")
    ap.add_argument("--grid", type=int, default=6, help="Cell grid size: 4x4 dict -> 6, 5x5 -> 7, 6x6 -> 8, 7x7 -> 9")
    ap.add_argument("--ids", default="-Z:0,+X:1,-X:2,+Y:3,-Y:4", help='Face IDs like "-Z:0,+X:1,-X:2,+Y:3,-Y:4"')
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)

    ids_by_face = parse_face_ids(args.ids)

    cube_white = build_open_top_hollow_cube(args.outer, args.wall)
    markers_black = build_markers_for_cube(
        outer_L=args.outer,
        marker_size_mm=args.marker,
        tile_thickness_mm=args.tile,
        dict_name=args.dict,
        ids_by_face=ids_by_face,
        grid_n=args.grid,
        inset_mm=args.inset,
    )

    white_path = os.path.join(args.out, "cube_white.stl")
    cube_white.export(white_path)
    print("Wrote:", white_path)

    if markers_black is not None:
        black_path = os.path.join(args.out, "markers_black.stl")
        markers_black.export(black_path)
        print("Wrote:", black_path)

        # Optional combined STL for quick preview (not for AMS coloring)
        combined = trimesh.util.concatenate([cube_white, markers_black])
        combined_path = os.path.join(args.out, "combined_preview.stl")
        combined.export(combined_path)
        print("Wrote:", combined_path)
    else:
        print("No markers generated (check --ids).")


if __name__ == "__main__":
    main()
