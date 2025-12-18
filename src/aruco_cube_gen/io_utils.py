import os
from datetime import datetime
from typing import Tuple

from .config import Config

def make_output_dir(prefix: str = "out_stls") -> str:
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_dir = f"{prefix}_{ts}"
    os.makedirs(out_dir, exist_ok=False)
    return out_dir

def write_run_info(out_dir: str, cfg: Config, plate_size: float, plate_thickness: float) -> str:
    path = os.path.join(out_dir, "run_info.txt")
    with open(path, "w") as f:
        f.write("ArUco Cube Generator – Run Info\n")
        f.write("=" * 40 + "\n\n")

        f.write("Cube geometry:\n")
        f.write(f"  Cube edge           : {cfg.cube_edge} mm\n")
        f.write(f"  Wall thickness      : {cfg.wall_thickness} mm\n")
        f.write(f"  Slot fraction       : {cfg.slot_fraction}\n")
        f.write(f"  Slot depth          : {cfg.slot_depth} mm\n\n")

        f.write("Plate geometry:\n")
        f.write(f"  Plate size          : {plate_size:.3f} mm\n")
        f.write(f"  Plate thickness     : {plate_thickness:.3f} mm\n")
        f.write(f"  Clearance           : {cfg.clearance} mm per side\n")
        f.write(f"  Marker margin frac  : {cfg.plate_margin_fraction}\n")
        f.write(f"  Bezel overhang      : {cfg.bezel_overhang} mm\n")
        f.write(f"  Bezel thickness     : {cfg.bezel_thickness} mm\n\n")

        f.write("ArUco marker:\n")
        f.write(f"  Dictionary          : {cfg.aruco_dict_name}\n")
        f.write(f"  Marker bits         : {cfg.aruco_marker_bits} x {cfg.aruco_marker_bits}\n")
        f.write(f"  Border bits         : {cfg.aruco_border_bits}\n")
        f.write(f"  Image size          : {cfg.aruco_image_size} px\n")
        f.write(f"  Raised cell height  : {cfg.marker_height} mm\n\n")

        f.write("Bezel ID text:\n")
        f.write(f"  Enabled             : {cfg.bezel_text_enabled}\n")
        f.write(f"  Prefix              : '{cfg.bezel_text_prefix}'\n")
        f.write(f"  Text height         : {cfg.bezel_text_height_mm} mm\n")
        f.write(f"  Text depth          : {cfg.bezel_text_depth_mm} mm\n")
        f.write(f"  Font                : {cfg.bezel_text_font}\n\n")

        f.write("Generated plate IDs:\n")
        for mid in cfg.plate_ids:
            f.write(f"  - {mid}\n")

    return path
