# 📦 ArUco Cube STL Generator

Generate a **hollow calibration cube** and **multicolor ArUco marker plates** entirely in Python — designed for **robust visual detection** at up to ~**1.5 m** using the **Intel RealSense D455 RGB camera**, and optimized for **Bambu Lab AMS** multi-color printing.

This version includes a **seam-hiding plate bezel** so the marker face can be printed **face-up and matte**, avoiding glossy bed-contact artifacts that degrade detection reliability.

---

## 🖼 Preview

> Renders shown are representative. Final appearance depends on slicer and filament.

<table>
  <tr>
    <td align="center">
      <strong>Hollow Cube with Recessed Faces</strong><br/>
      <img src="images/cube_render.png" alt="ArUco cube render" width="320"/>
    </td>
    <td align="center">
      <strong>ArUco Plate with Seam-Hiding Bezel</strong><br/>
      <img src="images/plate_render.png" alt="ArUco plate render" width="320"/>
    </td>
  </tr>
</table>

---

## 🚀 Features

### 🧊 Cube Generator
- Hollow cube with:
  - Outer edge: **120 mm**
  - Wall thickness: **6 mm**
  - **Five recessed faces** (top, +X, −X, +Y, −Y)
  - Flat bottom for strong bed adhesion
- Recess depth: **3 mm**, matching plate thickness

### 🧩 ArUco Plate Generator
- **4×4 ArUco markers** (`DICT_4X4_50`, `borderBits = 1`)
- **3 mm thick plug plates**
- **0.8 mm raised black cells** for AMS two-color printing
- **Integrated top-face bezel (flange)**:
  - Overlaps cube slot opening
  - Hides seam and shadow lines
  - Improves detection stability
  - Allows **face-up printing** (matte marker surface)
- Layout tuned for:
  - ~**8 px/cell at 1.5 m**
  - Increased white “quiet zone”

---

## 🧠 Design Rationale (Intel RealSense D455)

### Camera assumptions
- RGB resolution: **1280 px horizontal**
- Horizontal FOV: **~86°**
- Marker grid: **6×6 cells** (4×4 data + borderBits=1)

### Pixels per degree
```
1280 px / 86° ≈ 14.9 px/degree
```

### Target pixels per cell
- ≥ 6 px/cell → borderline
- ≥ 8 px/cell → reliable (design target)
- ≥ 10 px/cell → very robust

### Marker size @ 1.5 m
```
cells = 6
px_target = 8
marker_px ≈ 48 px
angular_width ≈ 48 / 14.9 ≈ 3.22°
physical_width ≈ 2 × 1.5 m × tan(3.22° / 2) ≈ 84 mm
```

➡️ **Minimum recommended marker width: ~84 mm**

### Mapping to the 120 mm cube
- Slot size: 120 × 0.8 = **96 mm**
- Plate size (with clearance): **95.6 mm**
- Marker coverage:
  - `PLATE_MARGIN_FRACTION = 0.88`
  - Marker area ≈ **84.1 mm**
  - Cell size ≈ **14.0 mm**
  - Quiet zone ≈ **5.7 mm per side** (~0.4 cell)

### Why the bezel matters
ArUco detection is sensitive to false edges near the black border:
- Plate/cube seams
- Shadow lines
- Texture discontinuities

The bezel overlaps the slot opening and visually removes these edges while keeping the marker size unchanged.

---

## 🔁 If You Change Camera or Distance (Cheat Table)

Assumes **6×6 ArUco grid** and ~86° HFOV.

| Max Distance | Target px/cell | Marker Width |
|-------------|----------------|--------------|
| 1.0 m | 8 px | ~56 mm |
| 1.0 m | 10 px | ~70 mm |
| 1.5 m | 8 px | ~84 mm |
| 1.5 m | 10 px | ~106 mm |
| 2.0 m | 8 px | ~113 mm |
| 2.0 m | 10 px | ~141 mm |

**Rule of thumb**
- Lower resolution → increase marker size
- Narrower FOV → smaller markers acceptable
- Motion blur / wide lenses → prefer 10 px/cell

---

## 📂 Project Structure

```
.
├── aruco_cube_stls.py
├── README.md
└── output/
    ├── cube_with_slots.stl
    ├── plate_base.stl
    ├── plate_base_id0.stl
    ├── plate_marker_id0.stl
    ├── plate_combined_id0.stl
    └── …
```

---

## ▶️ Running the Generator

```bash
python aruco_cube_stls.py
```

---

## 🖨 Printing & AMS Workflow (Bambu Studio)

### Cube (single color)
1. Import `cube_with_slots.stl`
2. Supports: **OFF**
3. Infill: **0–10%** (walls provide strength)
4. Print orientation: flat bottom on bed

### Plates (two colors via AMS)
For each marker ID:

1. Import:
   - `plate_base_idX.stl` → assign **white (PLA matte recommended)**
   - `plate_marker_idX.stl` → assign **black**
2. If not aligned:
   - Right-click → **Align → Center (XYZ)**
3. Print orientation:
   - **Face-up** (marker visible side up)
4. Supports: **OFF**
5. Ironing: **OFF**

### Recommended plate print settings
- Layer height: **0.12–0.16 mm**
- Filament: **PLA Matte (white)**
- No fuzzy skin on marker cells
- Normal PLA for black is fine

---

## 🧱 Assembly

1. Press-fit plates into cube recesses (0.2 mm clearance)
2. Bezel overlaps slot opening, hiding the seam
3. Optional:
   - Small drop of CA glue on the **back corners only**
4. Orient cube so open face is down when in use

---

## 🔧 Troubleshooting

### Missing ArUco functions
```bash
pip uninstall -y opencv-python opencv-python-headless
pip install opencv-contrib-python
```

### Boolean operation failures
```bash
pip install "trimesh[easy]"
```

---

## 📜 License
MIT License
