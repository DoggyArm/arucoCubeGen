"""
text3d.py

Text mesh generation with a robust fallback:
1) Try trimesh.path.creation.text (if present)
2) Fallback: rasterize via OpenCV putText and extrude pixels into boxes (run-length optimized)
"""

from __future__ import annotations

import numpy as np
import trimesh


def _make_text_mesh_trimesh_path(text: str, font, font_size: float, depth: float) -> trimesh.Trimesh:
    # Some trimesh versions have this, some don't.
    from trimesh.path.creation import text as path_text  # noqa: F401

    p = path_text(text=text, font=font, font_size=font_size)
    m = p.extrude(height=depth)
    m.process(validate=True)
    return m


def _make_text_mesh_raster(
    text: str,
    target_height_mm: float,
    depth_mm: float,
    *,
    desired_px_height: int = 64,
    thickness: int = 2,
) -> trimesh.Trimesh:
    """
    Rasterize with OpenCV Hershey font (always available) then extrude "ink" pixels.
    Uses run-length encoding per row to reduce box count.

    Returns a mesh with origin at (0,0,0) lower-left; Z is [0, depth_mm].
    """
    import cv2

    # Start with a rough scale, compute actual text size, then rescale to desired_px_height
    font_face = cv2.FONT_HERSHEY_SIMPLEX
    scale0 = 1.0
    (w0, h0), baseline0 = cv2.getTextSize(text, font_face, scale0, thickness)
    if h0 <= 0 or w0 <= 0:
        raise RuntimeError("cv2.getTextSize returned invalid size for text rendering")

    scale = desired_px_height / float(h0)

    (w, h), baseline = cv2.getTextSize(text, font_face, scale, thickness)

    pad = 8
    img_h = h + baseline + 2 * pad
    img_w = w + 2 * pad

    img = np.zeros((img_h, img_w), dtype=np.uint8)

    org = (pad, pad + h)  # baseline anchor
    cv2.putText(img, text, org, font_face, scale, color=255, thickness=thickness, lineType=cv2.LINE_AA)

    # Binarize
    _, bw = cv2.threshold(img, 32, 255, cv2.THRESH_BINARY)

    # Pixel size in mm based on desired height
    px_mm = target_height_mm / float(desired_px_height)

    # Build boxes for contiguous runs in each row
    boxes = []
    rows, cols = bw.shape

    for r in range(rows):
        row = bw[r, :]
        c = 0
        while c < cols:
            if row[c] == 0:
                c += 1
                continue

            # start run
            c0 = c
            while c < cols and row[c] != 0:
                c += 1
            c1 = c  # exclusive

            run_len = c1 - c0
            if run_len <= 0:
                continue

            # Box extents (x, y, z)
            ex = run_len * px_mm
            ey = px_mm
            ez = depth_mm

            # Center of the run in XY.
            # Flip Y so text isn't upside down: r=0 at top should become high Y.
            cx = (c0 + run_len / 2.0) * px_mm
            cy = (rows - 1 - r + 0.5) * px_mm
            cz = ez / 2.0

            box = trimesh.creation.box(extents=(ex, ey, ez))
            box.apply_translation([cx, cy, cz])
            boxes.append(box)

    if not boxes:
        raise RuntimeError("Raster text produced no ink pixels (unexpected).")

    m = trimesh.util.concatenate(boxes)
    m.process(validate=False)
    return m


def make_text_mesh(text: str, font, font_size: float, depth: float, *, target_height_mm: float | None = None) -> trimesh.Trimesh:
    """
    Public API used by geometry.py.

    If trimesh path text exists -> use it (smooth outlines).
    Otherwise -> OpenCV raster fallback (always works).

    Note: when using raster fallback, `target_height_mm` should be provided for scaling.
    """
    # Attempt trimesh path method
    try:
        return _make_text_mesh_trimesh_path(text=text, font=font, font_size=font_size, depth=depth)
    except Exception:
        pass

    # Fallback needs target height
    if target_height_mm is None:
        # reasonable default if caller doesn't provide it
        target_height_mm = max(2.0, float(font_size))

    return _make_text_mesh_raster(
        text=text,
        target_height_mm=float(target_height_mm),
        depth_mm=float(depth),
    )
