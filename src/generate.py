"""
Main entry point to generate STLs for the drop-in, screwless ArUco cube
using STUDS ON PLATES + EDGE BLOCKS WITH SLOT RECEIVERS.

Run:
  python -m src.generate

Outputs:
  out_dropin_edgeblocks_slots/
    plate_white.stl
    plate_black_0.stl ... plate_black_4.stl
    edge_block_slots.stl
"""

from __future__ import annotations

import os
import trimesh

from .config import PlateConfig, MarkerConfig, EdgeBlockConfig, DEFAULT_FACE_IDS
from .plate_gen import generate_universal_plate_white
from .aruco_gen import aruco_module_grid
from .mesh_utils import cleanup_mesh_portable
from .clamp_gen import generate_edge_block_slots


def export_stl(mesh: trimesh.Trimesh, path: str) -> None:
    if mesh.is_empty:
        return
    mesh.export(path)


def build_black_tiles_inlay_mesh(
    marker_id: int,
    plate_thickness_mm: float,
    aruco_dict: str,
    modules: int,
    border_bits: int,
    marker_size_mm: float,
    inlay_depth_mm: float,
    center: bool = True,
) -> trimesh.Trimesh:
    """
    Black tiles mesh meant to be printed as the *first* material when printing outside-face-down.

    Convention in plate_gen for this design:
      OUTSIDE face is at z=0
      plate goes up to z=plate_thickness_mm

    So to make an inlay that is flush on the outside:
      tiles occupy z in [0 .. inlay_depth_mm]
    """
    grid = aruco_module_grid(
        marker_id=marker_id,
        aruco_dict_name=aruco_dict,
        modules=modules,
        border_bits=border_bits,
        pixels=600,
    )
    n = grid.shape[0]
    module_mm = marker_size_mm / n

    cx, cy = (0.0, 0.0) if center else (0.0, 0.0)

    boxes = []
    for r in range(n):
        for c in range(n):
            if grid[r, c] == 0:
                continue

            x = (c - (n / 2) + 0.5) * module_mm + cx
            y = ((n / 2) - r - 0.5) * module_mm + cy

            tile = trimesh.creation.box(extents=[module_mm, module_mm, inlay_depth_mm])
            tile.apply_translation([x, y, inlay_depth_mm / 2.0])
            boxes.append(tile)

    if not boxes:
        return trimesh.Trimesh()

    mesh = trimesh.util.concatenate(boxes)
    return cleanup_mesh_portable(mesh)


def main(out_dir: str = "./out_dropin_edgeblocks_slots") -> None:
    plate_cfg = PlateConfig()
    marker_cfg = MarkerConfig()
    block_cfg = EdgeBlockConfig()

    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    # 1) Universal plate (white) with studs
    plate_white = generate_universal_plate_white(
        size_mm=plate_cfg.size_mm,
        thickness_mm=plate_cfg.thickness_mm,
        miter_enabled=plate_cfg.miter_enabled,
        studs_per_edge=plate_cfg.studs_per_edge,
        stud_end_margin_mm=plate_cfg.stud_end_margin_mm,
        stud_edge_offset_mm=plate_cfg.stud_edge_offset_mm,
        stud_d_mm=plate_cfg.stud_d_mm,
        stud_len_mm=plate_cfg.stud_len_mm,
        stud_tip_chamfer_mm=plate_cfg.stud_tip_chamfer_mm,
        stud_boss_outer_d_mm=plate_cfg.stud_boss_outer_d_mm,
        stud_boss_height_mm=plate_cfg.stud_boss_height_mm,
        relief_enabled=plate_cfg.relief_enabled,
        relief_inset_mm=plate_cfg.relief_inset_mm,
        relief_height_mm=plate_cfg.relief_height_mm,
    )
    export_stl(plate_white, os.path.join(out_dir, "plate_white.stl"))
    print("Wrote:", os.path.join(out_dir, "plate_white.stl"))

    # 2) Black tiles per face id (inlay for outside-face-down printing)
    for name, mid in DEFAULT_FACE_IDS.items():
        black = build_black_tiles_inlay_mesh(
            marker_id=mid,
            plate_thickness_mm=plate_cfg.thickness_mm,
            aruco_dict=marker_cfg.aruco_dict,
            modules=marker_cfg.modules,
            border_bits=marker_cfg.border_bits,
            marker_size_mm=marker_cfg.marker_size_mm,
            inlay_depth_mm=marker_cfg.inlay_depth_mm,
            center=marker_cfg.center,
        )
        fn = f"plate_black_{mid}.stl"
        export_stl(black, os.path.join(out_dir, fn))
        print("Wrote:", os.path.join(out_dir, fn), f"({name})")

    # 3) Edge block with slot receivers (print 8)
    edge_block = generate_edge_block_slots(
        block_size_mm=block_cfg.block_size_mm,
        leg_thickness_mm=6.0,  # simple default; can move to config if you want
        length_mm=block_cfg.length_mm,
        sockets_per_edge=block_cfg.sockets_per_edge,
        socket_end_margin_mm=block_cfg.socket_end_margin_mm,
        socket_offset_mm=block_cfg.socket_offset_mm,
        stud_d_mm=plate_cfg.stud_d_mm,
        slot_opening_clearance_mm=0.6,
        sections=32,
    )
    export_stl(edge_block, os.path.join(out_dir, "edge_block_slots.stl"))
    print("Wrote:", os.path.join(out_dir, "edge_block_slots.stl"))

    print("\nPrinting/assembly notes:")
    print("- Print plate_white face-down (outside/marker side on build plate).")
    print("- Import plate_white + one plate_black_<id> in Bambu Studio and assign colors.")
    print("- Print 5 plates + 8 edge blocks.")
    print("- If fit is too tight: reduce PlateConfig.stud_d_mm by 0.05.")
    print("- If fit is too loose: reduce slot_opening_clearance_mm (0.6 -> 0.4).")


if __name__ == "__main__":
    main()
