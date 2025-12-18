import cv2
import numpy as np
import trimesh
from cv2 import aruco

from .config import Config


def _get_dictionary(cfg: Config):
    # Keep it simple for now
    return aruco.getPredefinedDictionary(aruco.DICT_4X4_50)


def generate_aruco_image(cfg: Config, marker_id: int) -> np.ndarray:
    """
    Generate a binary ArUco marker image (0/255).
    Works across OpenCV versions.
    """
    dictionary = _get_dictionary(cfg)

    if hasattr(aruco, "generateImageMarker"):
        img = aruco.generateImageMarker(
            dictionary, marker_id, cfg.aruco_image_size, borderBits=cfg.aruco_border_bits
        )
    elif hasattr(aruco, "drawMarker"):
        img = aruco.drawMarker(
            dictionary, marker_id, cfg.aruco_image_size, borderBits=cfg.aruco_border_bits
        )
    else:
        raise RuntimeError(
            "OpenCV ArUco API missing drawMarker/generateImageMarker. "
            "Install opencv-contrib-python."
        )

    return img


def create_marker_mesh_for_plate(
    cfg: Config,
    marker_id: int,
    plate_size: float,
    plate_thickness: float,
) -> trimesh.Trimesh:
    """
    Convert ArUco image into raised squares for black cells on top of the plate.
    """
    img = generate_aruco_image(cfg, marker_id)

    cells_per_side = cfg.aruco_marker_bits + 2 * cfg.aruco_border_bits
    marker_area = plate_size * cfg.plate_margin_fraction
    cell_size = marker_area / cells_per_side
    margin_mm = (plate_size - marker_area) / 2.0

    _, img_bin = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)

    meshes = []
    for row in range(cells_per_side):
        for col in range(cells_per_side):
            px = img_bin[
                int((row + 0.5) * cfg.aruco_image_size / cells_per_side),
                int((col + 0.5) * cfg.aruco_image_size / cells_per_side),
            ]
            if px == 0:
                x0 = margin_mm + col * cell_size
                y0 = margin_mm + (cells_per_side - 1 - row) * cell_size  # flip Y

                cx = x0 + cell_size / 2.0
                cy = y0 + cell_size / 2.0
                cz = plate_thickness + cfg.marker_height / 2.0

                cell = trimesh.creation.box(extents=(cell_size, cell_size, cfg.marker_height))
                cell.apply_translation([cx, cy, cz])
                meshes.append(cell)

    if not meshes:
        raise RuntimeError(f"No black cells found for marker ID {marker_id}.")

    return trimesh.util.concatenate(meshes)
