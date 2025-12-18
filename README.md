# 📦 ArUco Cube STL Generator

Generate a **hollow calibration cube** and **multicolor ArUco marker plates** entirely in Python — designed for **robust visual detection** at up to ~**1.5 m** using the **Intel RealSense D455 RGB camera**, and optimized for **Bambu Lab AMS** multi-color printing.

This version includes a **seam-hiding plate bezel** so the marker face can be printed **face-up and matte**, avoiding glossy bed-contact artifacts that degrade detection.

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
- Produces a **hollow cube** with:
  - Outer edge: **120 mm**
  - Wall thickness: **6 mm**
  - **Five recessed faces** (top, +X, −X, +Y, −Y)
  - Flat bottom for strong bed adhesion
- Recess depth: **3 mm**, matching plate thickness

### 🧩 ArUco Plate Generator
- Generates **4×4 ArUco markers** (`DICT_4X4_50`, `borderBits = 1`)
- **3 mm thick plug plate** with:
  - **Raised black cells (0.8 mm)** for AMS two-color printing
  - **Integrated top-face bezel (flange)** that overlaps the cube slot opening
    - Hides seam/shadow lines
    - Improves detector stability
    - Allows **face-up printing** (camera-visible surface stays matte)
- Marker layout tuned for:
  - ~**8 px/cell at 1.5 m**
  - Increased white “quiet zone” for reliable detection

---

## 🧠 Design Rationale (Intel RealSense D455)

This design is driven by **camera geometry**, not aesthetics. The goal is to guarantee enough image resolution per ArUco cell while maintaining a clean quiet zone and printable geometry.

### Camera assumptions (D455 RGB)
- Resolution: **1280 px horizontal**
- Horizontal FOV: **~86°**
- Marker dictionary: **DICT_4X4**, `borderBits = 1`
- Total marker grid: **6 × 6 cells**

### Pixels per degree
```
1280 px / 86° ≈ 14.9 px/degree
```

### Required pixels per ArUco cell
Empirically:
- ≥ **6 px/cell** → borderline
- ≥ **8 px/cell** → reliable
- ≥ **10 px/cell** → very robust

This design targets **~8 px/cell at the maximum distance**.

### Marker size calculation @ 1.5 m
Let:
- Desired pixels per cell = 8
- Cells per marker = 6
- Total marker pixels ≈ 48 px

Angular width of marker:
```
48 px / 14.9 px/° ≈ 3.22°
```

Physical marker width:
```
width = 2 × d × tan(θ / 2)
      = 2 × 1.5 m × tan(3.22° / 2)
      ≈ 0.084 m ≈ 84 mm
```

➡️ **Minimum recommended marker width: ~84 mm**

### Mapping to the existing cube
- Cube edge: **120 mm**
- Slot fraction: **0.8**
- Slot size: **96 mm**
- Plate size (with clearance): **95.6 mm**

Marker coverage:
```
PLATE_MARGIN_FRACTION = 0.88
Marker area ≈ 84.1 mm
Cell size ≈ 14.0 mm
White quiet zone ≈ 5.7 mm per side (~0.4 cell)
```

### Why the bezel matters
ArUco detection is sensitive to **false edges** near the black border:
- Plate/cube seams
- Shadow lines
- Texture discontinuities

The **top-face bezel**:
- Overlaps the slot opening by ~0.8 mm
- Visually removes the seam from the camera’s perspective
- Improves quad detection stability without shrinking the marker

Critically, the bezel is placed so the marker face can be printed **face-up**, preserving a matte surface.

---

## 🔁 If You Change Camera or Distance (Cheat Table)

Use this table to quickly re-size the **marker area** if you change camera, resolution, or maximum viewing distance.
Assumes a **6×6 ArUco grid** (4×4 + borderBits=1).

| Max Distance | Target px/cell | Total px (marker) | Recommended Marker Width |
|-------------|----------------|-------------------|--------------------------|
| 1.0 m       | 8 px           | 48 px             | ~56 mm                   |
| 1.0 m       | 10 px          | 60 px             | ~70 mm                   |
| 1.5 m       | 8 px           | 48 px             | ~84 mm                   |
| 1.5 m       | 10 px          | 60 px             | ~106 mm                  |
| 2.0 m       | 8 px           | 48 px             | ~113 mm                  |
| 2.0 m       | 10 px          | 60 px             | ~141 mm                  |

**How to use this:**
1. Pick your **maximum distance**
2. Choose **8 px/cell** (compact) or **10 px/cell** (robust)
3. Make sure your **marker area (black border to black border)** is at least the listed width
4. Add ≥ **0.4–0.5 cell** of white margin per side for a quiet zone

If your camera:
- has **lower resolution** → increase marker size
- has **narrower FOV** → you can reduce marker size slightly
- uses **wider lenses / motion blur** → prefer 10 px/cell

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

## ⚙️ Configuration (inside `aruco_cube_stls.py`)

```python
# Cube / slot
CUBE_EDGE = 120.0
WALL_THICKNESS = 6.0
SLOT_FRACTION = 0.8
SLOT_DEPTH = 3.0
CLEARANCE = 0.2

# Plate / marker layout
PLATE_MARGIN_FRACTION = 0.88
ARUCO_MARKER_BITS = 4
ARUCO_BORDER_BITS = 1
ARUCO_IMAGE_SIZE = 200
MARKER_HEIGHT = 0.8

# Seam-hiding bezel
BEZEL_OVERHANG = 0.8
BEZEL_THICKNESS = 0.8

PLATE_IDS = [0, 1, 2, 3, 4]
```

---

## 🖨 Printing Notes (Bambu P2S)

- Print plates **face-up**
- Filament: **PLA Matte (white)**
- Layer height: **0.12–0.16 mm**
- Ironing: **OFF**
- Supports: **OFF**

---

## 📜 License
MIT License
