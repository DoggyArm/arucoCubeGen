import numpy as np
import trimesh
import cv2
from cv2 import aruco


# =========================
# Parameters
# =========================

# Cube / slot parameters
CUBE_EDGE = 120.0          # mm, outer edge of cube
WALL_THICKNESS = 6.0       # mm  <-- as requested
SLOT_FRACTION = 0.8        # slot size as fraction of cube edge
SLOT_DEPTH = 3.0           # mm recess depth (also plate thickness)

# Plate parameters
CLEARANCE = 0.2            # mm clearance per side for plate in slot
PLATE_MARGIN_FRACTION = 0.9  # fraction of plate width used by ArUco area
ARUCO_MARKER_BITS = 4      # 4x4 aruco markers
ARUCO_BORDER_BITS = 1      # border cells around marker bits
ARUCO_IMAGE_SIZE = 200     # pixels for marker generation
MARKER_HEIGHT = 0.8        # mm height of raised "black" squares

# IDs for plates
PLATE_IDS = [0, 1, 2, 3, 4]  # adjust as you like


# =========================
# Geometry helpers
# =========================

def make_box(extents, center):
    """
    Create a trimesh box with given extents and center.
    extents: (x_size, y_size, z_size)
    center: (cx, cy, cz)
    """
    box = trimesh.creation.box(extents=extents)
    box.apply_translation(center - box.center_mass)
    return box


# =========================
# Cube with recessed slots
# =========================

def create_cube_with_slots(
    cube_edge=CUBE_EDGE,
    wall_thickness=WALL_THICKNESS,
    slot_fraction=SLOT_FRACTION,
    slot_depth=SLOT_DEPTH
):
    """
    Create a hollow cube with 5 recessed slots (top, +X, -X, +Y, -Y).
    Bottom face is flat and solid as a print surface.
    Returns a trimesh.Trimesh object.
    """
    # Outer and inner cube (centered at origin)
    outer = trimesh.creation.box(extents=(cube_edge, cube_edge, cube_edge))
    inner = trimesh.creation.box(
        extents=(
            cube_edge - 2 * wall_thickness,
            cube_edge - 2 * wall_thickness,
            cube_edge - 2 * wall_thickness,
        )
    )

    # Hollow shell
    shell = outer.difference(inner)  # requires OpenSCAD or another boolean backend

    # Slot sizes
    slot_size = cube_edge * slot_fraction

    # Top slot (+Z)
    top_slot = make_box(
        extents=(slot_size, slot_size, slot_depth),
        center=np.array([0.0, 0.0, cube_edge / 2 - slot_depth / 2])
    )

    # +X slot
    posx_slot = make_box(
        extents=(slot_depth, slot_size, slot_size),
        center=np.array([cube_edge / 2 - slot_depth / 2, 0.0, 0.0])
    )

    # -X slot
    negx_slot = make_box(
        extents=(slot_depth, slot_size, slot_size),
        center=np.array([-cube_edge / 2 + slot_depth / 2, 0.0, 0.0])
    )

    # +Y slot
    posy_slot = make_box(
        extents=(slot_size, slot_depth, slot_size),
        center=np.array([0.0, cube_edge / 2 - slot_depth / 2, 0.0])
    )

    # -Y slot
    negy_slot = make_box(
        extents=(slot_size, slot_depth, slot_size),
        center=np.array([0.0, -cube_edge / 2 + slot_depth / 2, 0.0])
    )

    slots_union = trimesh.util.concatenate([top_slot, posx_slot, negx_slot, posy_slot, negy_slot])

    shell_with_slots = shell.difference(slots_union)

    # Move cube so that bottom is at z = 0 (nice for printing)
    min_z = shell_with_slots.bounds[0][2]
    shell_with_slots.apply_translation([0.0, 0.0, -min_z])

    return shell_with_slots


# =========================
# Plate base
# =========================

def create_plate_base(
    cube_edge=CUBE_EDGE,
    slot_fraction=SLOT_FRACTION,
    clearance=CLEARANCE,
    slot_depth=SLOT_DEPTH
):
    """
    Create a single plate base that fits into the recessed slot.
    Origin at (0,0,0), top at z = plate_thickness.
    """
    slot_size = cube_edge * slot_fraction
    plate_size = slot_size - 2 * clearance
    plate_thickness = slot_depth  # same as recess depth

    plate = trimesh.creation.box(extents=(plate_size, plate_size, plate_thickness))
    # Shift so bottom is at z = 0, x/y from 0..plate_size
    plate.apply_translation(np.array([plate_size / 2, plate_size / 2, plate_thickness / 2]))

    return plate, plate_size, plate_thickness


# =========================
# ArUco marker to raised cells
# =========================

def generate_aruco_image(marker_id, bits=ARUCO_MARKER_BITS, border_bits=ARUCO_BORDER_BITS, image_size=ARUCO_IMAGE_SIZE):
    """
    Generate a binary ArUco marker image (0/255).
    Supports both older drawMarker() and newer generateImageMarker() APIs.
    """
    dictionary = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)

    # Newer OpenCV (>=4.7, some builds of 4.10)
    if hasattr(aruco, "generateImageMarker"):
        img = aruco.generateImageMarker(dictionary, marker_id, image_size)

    # Older OpenCV (<=4.6)
    elif hasattr(aruco, "drawMarker"):
        img = aruco.drawMarker(dictionary, marker_id, image_size)

    else:
        raise RuntimeError(
            "Your OpenCV-ArUco build has no drawMarker() or generateImageMarker(). "
            "Install with: pip install opencv-contrib-python==4.10.0.84"
        )

    return img



def create_aruco_marker_mesh_for_plate(
    marker_id,
    plate_size,
    plate_thickness,
    marker_bits=ARUCO_MARKER_BITS,
    border_bits=ARUCO_BORDER_BITS,
    marker_height=MARKER_HEIGHT,
    margin_fraction=PLATE_MARGIN_FRACTION,
    image_size=ARUCO_IMAGE_SIZE
):
    """
    Given a plate size and thickness, create a mesh consisting of raised
    squares ("black" cells) representing an ArUco marker for a given ID.
    The marker is centered on the plate with some margin.
    """
    # Generate marker image
    img = generate_aruco_image(marker_id, bits=marker_bits, border_bits=border_bits, image_size=image_size)

    # Total cells per side = marker bits + 2*border bits
    cells_per_side = marker_bits + 2 * border_bits

    # Physical area used on plate
    marker_area = plate_size * margin_fraction
    cell_size_mm = marker_area / cells_per_side
    margin_mm = (plate_size - marker_area) / 2.0

    # Threshold image to be safe
    _, img_bin = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)

    cell_meshes = []

    for row in range(cells_per_side):
        for col in range(cells_per_side):
            pixel_val = img_bin[
                int((row + 0.5) * image_size / cells_per_side),
                int((col + 0.5) * image_size / cells_per_side)
            ]
            # ArUco black cells are 0; we want to extrude those
            if pixel_val == 0:
                # Convert (row, col) to plate coordinates (x=0..plate_size, y=0..plate_size).
                x0 = margin_mm + col * cell_size_mm
                # Flip row so row 0 is top of marker (higher y)
                y0 = margin_mm + (cells_per_side - 1 - row) * cell_size_mm

                # Center of this cell
                cx = x0 + cell_size_mm / 2.0
                cy = y0 + cell_size_mm / 2.0
                cz = plate_thickness + marker_height / 2.0  # on top of plate

                cell_box = trimesh.creation.box(
                    extents=(cell_size_mm, cell_size_mm, marker_height)
                )
                cell_box.apply_translation(np.array([cx, cy, cz]))
                cell_meshes.append(cell_box)

    if not cell_meshes:
        raise RuntimeError(f"No black cells found for marker ID {marker_id} – something is wrong.")

    marker_mesh = trimesh.util.concatenate(cell_meshes)
    return marker_mesh


# =========================
# Main: generate STLs
# =========================

def main():
    # 1) Cube with slots
    print("Creating cube with slots...")
    cube_mesh = create_cube_with_slots()
    cube_mesh.export("cube_with_slots.stl")
    print("Saved: cube_with_slots.stl")

    # 2) Plate base (reusable for all IDs)
    print("Creating plate base template...")
    plate_base_mesh, plate_size, plate_thickness = create_plate_base()
    plate_base_mesh.export("plate_base.stl")
    print("Saved: plate_base.stl")

    # 3) For each ID, create marker mesh (and, optionally, base+marker union)
    for marker_id in PLATE_IDS:
        print(f"Creating ArUco plate for ID {marker_id}...")

        # Base is same geometry; export per-ID if you like
        base_filename = f"plate_base_id{marker_id}.stl"
        plate_base_mesh.export(base_filename)

        # Marker mesh (raised black squares)
        marker_mesh = create_aruco_marker_mesh_for_plate(
            marker_id=marker_id,
            plate_size=plate_size,
            plate_thickness=plate_thickness
        )
        marker_filename = f"plate_marker_id{marker_id}.stl"
        marker_mesh.export(marker_filename)

        # Optional: union of base + markers into a single mesh
        combined = trimesh.util.concatenate([plate_base_mesh, marker_mesh])
        combined_filename = f"plate_combined_id{marker_id}.stl"
        combined.export(combined_filename)

        print(f"Saved: {base_filename}, {marker_filename}, {combined_filename}")


if __name__ == "__main__":
    main()

