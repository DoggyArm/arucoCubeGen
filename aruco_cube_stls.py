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
PLATE_MARGIN_FRACTION = 0.88  # fraction of plate width used by ArUco area
ARUCO_MARKER_BITS = 4      # 4x4 aruco markers
ARUCO_BORDER_BITS = 1      # border cells around marker bits
ARUCO_IMAGE_SIZE = 200     # pixels for marker generation
MARKER_HEIGHT = 0.8        # mm height of raised "black" squares

# Bezel (seam-hiding flange) parameters
BEZEL_OVERHANG = 0.8       # mm how much the bezel overlaps beyond the slot opening on each side
BEZEL_THICKNESS = 0.8      # mm thickness of the bezel (kept within plate thickness, not adding height)

# Bezel ID text parameters
BEZEL_TEXT_ENABLED = True
BEZEL_TEXT_PREFIX = "ID "  # set to "" if you only want the number
BEZEL_TEXT_HEIGHT_MM = 3.0 # target text height
BEZEL_TEXT_DEPTH_MM = 0.5  # engraved depth; fallback emboss uses same value as height
BEZEL_TEXT_FONT = None     # None = trimesh default; or set path/name if needed

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
    slot_depth=SLOT_DEPTH,
    marker_margin_fraction=PLATE_MARGIN_FRACTION,
    marker_bits=ARUCO_MARKER_BITS,
    border_bits=ARUCO_BORDER_BITS,
    bezel_overhang=BEZEL_OVERHANG,
    bezel_thickness=BEZEL_THICKNESS,
    text=None
):
    """
    Create a single plate base that fits into the recessed slot.
    Adds a thin top-face bezel (flange) that overlaps the slot seam.
    Optionally engraves text into the bezel/quiet-zone area.
    Origin at (0,0,0), top at z = plate_thickness.
    """
    slot_size = cube_edge * slot_fraction
    plate_size = slot_size - 2 * clearance
    plate_thickness = slot_depth  # same as recess depth

    # --- Main plug that fits into the slot ---
    plate = trimesh.creation.box(extents=(plate_size, plate_size, plate_thickness))
    plate.apply_translation(np.array([plate_size / 2, plate_size / 2, plate_thickness / 2]))

    # --- Bezel flange that sits on the cube face and hides the seam ---
    bezel_outer = slot_size + 2.0 * bezel_overhang
    bezel_t = min(bezel_thickness, plate_thickness)

    bezel = trimesh.creation.box(extents=(bezel_outer, bezel_outer, bezel_t))
    bezel_center = np.array([
        plate_size / 2,
        plate_size / 2,
        plate_thickness - bezel_t / 2
    ])
    bezel.apply_translation(bezel_center)

    base = trimesh.util.concatenate([plate, bezel])

    # --- Optional engraved text (placed in the quiet-zone band) ---
    if text and BEZEL_TEXT_ENABLED:
        try:
            # Compute the white band height available (quiet zone band)
            cells_per_side = marker_bits + 2 * border_bits
            marker_area = plate_size * marker_margin_fraction
            margin_mm = (plate_size - marker_area) / 2.0  # white band thickness per side

            # Choose a text height that fits in the band
            usable_band = max(0.0, margin_mm - 1.0)  # leave ~1mm breathing room
            target_h = min(BEZEL_TEXT_HEIGHT_MM, usable_band)
            target_h = max(1.5, target_h)  # don't go too tiny

            # Create text mesh (extruded)
            # NOTE: trimesh.creation.text signature supports (text, font=..., depth=..., font_size=...)
            txt = trimesh.creation.text(
                text=text,
                font=BEZEL_TEXT_FONT,
                depth=BEZEL_TEXT_DEPTH_MM,
                font_size=10  # temporary; we scale below to target_h
            )

            # Scale text in XY so its Y-size becomes target_h
            bounds = txt.bounds
            txt_h = bounds[1][1] - bounds[0][1]
            if txt_h <= 1e-6:
                raise RuntimeError("Text mesh height too small.")

            s = target_h / txt_h
            txt.apply_scale([s, s, 1.0])

            # Recompute bounds after scaling
            b = txt.bounds
            txt_w = b[1][0] - b[0][0]
            txt_h2 = b[1][1] - b[0][1]

            # Place it centered in the bottom quiet-zone band (below the marker area)
            # Band spans y in [0, margin_mm]; center text in that region
            cx = plate_size / 2.0
            cy = margin_mm / 2.0

            # Ensure it doesn't exceed plate edges; if it does, scale down
            max_w = plate_size - 2.0  # keep ~1mm edge margin each side
            if txt_w > max_w:
                s2 = max_w / txt_w
                txt.apply_scale([s2, s2, 1.0])
                b = txt.bounds
                txt_w = b[1][0] - b[0][0]
                txt_h2 = b[1][1] - b[0][1]

            # Move text so its center is at (cx, cy)
            # Text mesh is centered around its own origin inconsistently; shift by its bounds center.
            bx = (b[0][0] + b[1][0]) / 2.0
            by = (b[0][1] + b[1][1]) / 2.0
            bz = (b[0][2] + b[1][2]) / 2.0

            # Put the text cutter *into* the top surface
            cz = plate_thickness - BEZEL_TEXT_DEPTH_MM / 2.0

            txt.apply_translation([cx - bx, cy - by, cz - bz])

            # Engrave (boolean difference)
            base = base.difference(txt)

        except Exception as e:
            # Fallback: shallow emboss on top (no boolean backend / text op issues)
            try:
                txt = trimesh.creation.text(
                    text=text,
                    font=BEZEL_TEXT_FONT,
                    depth=BEZEL_TEXT_DEPTH_MM,
                    font_size=10
                )
                b = txt.bounds
                txt_h = b[1][1] - b[0][1]
                s = max(1.5, min(BEZEL_TEXT_HEIGHT_MM, 3.0)) / max(txt_h, 1e-6)
                txt.apply_scale([s, s, 1.0])
                b = txt.bounds
                bx = (b[0][0] + b[1][0]) / 2.0
                by = (b[0][1] + b[1][1]) / 2.0
                bz = (b[0][2] + b[1][2]) / 2.0

                # Place embossed text slightly above top surface
                txt.apply_translation([
                    plate_size / 2.0 - bx,
                    (plate_size * (1.0 - marker_margin_fraction) / 2.0) / 2.0 - by,
                    plate_thickness + BEZEL_TEXT_DEPTH_MM / 2.0 - bz
                ])
                base = trimesh.util.concatenate([base, txt])
            except:
                pass

    return base, plate_size, plate_thickness



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
        img = aruco.generateImageMarker(dictionary, marker_id, image_size, borderBits=border_bits)

    # Older OpenCV (<=4.6)
    elif hasattr(aruco, "drawMarker"):
        img = aruco.drawMarker(dictionary, marker_id, image_size, borderBits=border_bits)

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

    # 2) Plate base template (no text) for reference
    print("Creating plate base template...")
    plate_base_template, plate_size, plate_thickness = create_plate_base(text=None)
    plate_base_template.export("plate_base.stl")
    print("Saved: plate_base.stl")

    # 3) For each ID, create per-ID base (with text), marker mesh, and combined export
    for marker_id in PLATE_IDS:
        print(f"Creating ArUco plate for ID {marker_id}...")

        # Per-ID base with engraved/embossed text in bezel
        plate_text = f"{BEZEL_TEXT_PREFIX}{marker_id}" if BEZEL_TEXT_ENABLED else None
        plate_base_mesh, _, _ = create_plate_base(text=plate_text)

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

        # Combined export (base + marker)
        combined = trimesh.util.concatenate([plate_base_mesh, marker_mesh])
        combined_filename = f"plate_combined_id{marker_id}.stl"
        combined.export(combined_filename)

        print(f"Saved: {base_filename}, {marker_filename}, {combined_filename}")



if __name__ == "__main__":
    main()

