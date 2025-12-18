"""
ArUco marker utilities.

We generate a black/white module grid using OpenCV's aruco module,
then the generator script turns the black modules into raised tiles.

Why a grid?
- It allows constructing the marker as geometry (tiles) instead of bitmap embossing.
- Tile geometry is perfect for multi-material printing: black STL + white STL.
"""
from __future__ import annotations

import numpy as np
import cv2


def get_aruco_dictionary(name: str):
    """
    Resolve OpenCV predefined ArUco dictionary by name.

    Examples:
      - DICT_4X4_50
      - DICT_5X5_100
      - DICT_6X6_250
    """
    if not hasattr(cv2.aruco, name):
        raise ValueError(
            f"Unknown cv2.aruco dictionary '{name}'. "
            f"Example: DICT_4X4_50, DICT_5X5_100, DICT_6X6_250"
        )
    return cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, name))


def aruco_module_grid(
    marker_id: int,
    aruco_dict_name: str,
    modules: int,
    border_bits: int,
    pixels: int = 600,
) -> np.ndarray:
    """
    Return an NxN grid (uint8 0/1) where 1 indicates a black module.

    N = modules + 2*border_bits

    Implementation:
      - Render marker to an image (pixels x pixels)
      - Binarize
      - Sample each module cell by averaging its area
    """
    ar_dict = get_aruco_dictionary(aruco_dict_name)
    n = modules + 2 * border_bits

    img = np.zeros((pixels, pixels), dtype=np.uint8)
    cv2.aruco.generateImageMarker(ar_dict, marker_id, pixels, img, border_bits)

    bw = (img < 128).astype(np.uint8)  # black=1

    step = pixels // n
    grid = np.zeros((n, n), dtype=np.uint8)
    for r in range(n):
        for c in range(n):
            patch = bw[r * step:(r + 1) * step, c * step:(c + 1) * step]
            grid[r, c] = 1 if patch.mean() > 0.5 else 0
    return grid
