"""
Mesh utilities shared across generators.

Includes:
- portable trimesh cleanup (works across older/newer trimesh versions)
- polygon triangulation helper (filters triangles outside polygon)
- simple square ring helper

We intentionally avoid external meshing/boolean engines to stay "pure Python".
"""
from __future__ import annotations

from typing import List, Tuple

import numpy as np
import trimesh
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import triangulate


def cleanup_mesh_portable(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """
    Cleanup compatible across older/newer trimesh versions.
    """
    # Remove degenerate faces
    try:
        if hasattr(mesh, "remove_degenerate_faces"):
            mesh.remove_degenerate_faces()
    except Exception:
        pass

    # Remove duplicate faces (order-insensitive)
    try:
        f = mesh.faces
        f_sorted = np.sort(f, axis=1)
        _, unique_idx = np.unique(f_sorted, axis=0, return_index=True)
        mask = np.zeros(len(f), dtype=bool)
        mask[unique_idx] = True
        if hasattr(mesh, "update_faces"):
            mesh.update_faces(mask)
        else:
            mesh.faces = mesh.faces[mask]
    except Exception:
        pass

    # Merge vertices
    try:
        if hasattr(mesh, "merge_vertices"):
            mesh.merge_vertices()
    except Exception:
        pass

    # Remove unreferenced vertices
    try:
        if hasattr(mesh, "remove_unreferenced_vertices"):
            mesh.remove_unreferenced_vertices()
    except Exception:
        pass

    # Validate
    try:
        mesh.process(validate=True)
    except Exception:
        pass

    # Finalize
    try:
        mesh.process(validate=True)
    except Exception:
        pass

    # Clear cached computed properties to avoid export mismatch
    try:
        if hasattr(mesh, "_cache"):
            mesh._cache.clear()
    except Exception:
        pass

    return mesh



def triangulate_polygon(poly: Polygon | MultiPolygon) -> List[Polygon]:
    """
    Shapely triangulate returns triangles covering polygon's bounding region.
    We keep only triangles whose representative point is inside poly.
    """
    tris = triangulate(poly)
    out = []
    for t in tris:
        if poly.contains(t.representative_point()):
            out.append(t)
    return out


def square_ring(size: float) -> List[Tuple[float, float]]:
    """
    Closed ring coords for a square centered at origin.
    """
    h = size / 2.0
    return [(-h, -h), (h, -h), (h, h), (-h, h), (-h, -h)]
