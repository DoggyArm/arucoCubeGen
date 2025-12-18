import os
import trimesh

from .config import Config
from .geometry import create_cube_with_slots, create_plate_base
from .aruco_marker import create_marker_mesh_for_plate
from .io_utils import make_output_dir, write_run_info

def generate_all(cfg: Config) -> str:
    out_dir = make_output_dir("out_stls")
    print(f"Saving STL outputs to: {out_dir}")

    # Cube
    cube = create_cube_with_slots(cfg)
    cube.export(os.path.join(out_dir, "cube_with_slots.stl"))

    # Plate template (also gives us plate_size)
    plate_template, plate_size, plate_thickness = create_plate_base(cfg, text=None)
    plate_template.export(os.path.join(out_dir, "plate_base.stl"))

    # Run metadata
    write_run_info(out_dir, cfg, plate_size, plate_thickness)

    # Per-ID exports
    for mid in cfg.plate_ids:
        label = f"{cfg.bezel_text_prefix}{mid}" if cfg.bezel_text_enabled else None

        base, _, _ = create_plate_base(cfg, text=label)
        base.export(os.path.join(out_dir, f"plate_base_id{mid}.stl"))

        marker = create_marker_mesh_for_plate(cfg, mid, plate_size, plate_thickness)
        marker.export(os.path.join(out_dir, f"plate_marker_id{mid}.stl"))

        combined = trimesh.util.concatenate([base, marker])
        combined.export(os.path.join(out_dir, f"plate_combined_id{mid}.stl"))

    return out_dir
