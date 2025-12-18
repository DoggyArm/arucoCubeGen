# 📦 ArUco Cube STL Generator

Generate a **hollow calibration cube** and **multicolor ArUco marker plates** entirely in Python — designed for **robust visual detection** at up to ~**1.5 m** using the **Intel RealSense D455 RGB camera**, and optimized for **Bambu Lab AMS** multi-color printing.

This project is intentionally **simple and hackable** — no GUI, no over-engineering, just:

> **Python → STL → slice → print**

This version includes:
- A **seam-hiding bezel** on each plate
- **Face-up, matte marker printing** (no bed gloss)
- **Timestamped output folders** for reproducible iteration
- A **self-documenting `run_info.txt`** saved with every STL batch
- Geometry tweaks for **large unsupported internal bridges**

---

## 🚀 Features

### 🧊 Cube Generator
- Hollow cube with:
  - **Outer edge: 150 mm**
  - Wall thickness: **3.2 mm** (configurable)
  - **Five recessed faces** (top, +X, −X, +Y, −Y)
  - Optional **open bottom** (rim retained for stiffness)
- Recess depth: **2.4 mm**, matching plate thickness
- Designed to be printed **support-free**
- Geometry includes:
  - Chamfered slot inner edges
  - Optional internal ribs / gussets to improve long bridges

### 🧩 ArUco Plate Generator
- **4×4 ArUco markers** (`DICT_4X4_50`, `borderBits = 1`)
- **2.4 mm thick plug plates**
- **0.8 mm raised black cells** for AMS two-color printing
- **Integrated top-face bezel (flange)**:
  - Overlaps cube slot opening
  - Hides seam and shadow lines
  - Improves detection stability
  - Allows **face-up printing** (matte marker surface)

### 🏷 Plate ID Text
- Optional **embossed ID text** in the white quiet zone
- Implemented with a **robust raster fallback**
- Designed to be slicer-safe (won’t disappear in preview)

---

## 🧠 Design Rationale (Intel RealSense D455)

### Camera assumptions
- RGB resolution: **1280 px horizontal**
- Horizontal FOV: **~86°**
- Marker grid: **6×6 cells**  
  (4×4 data + `borderBits = 1`)

### Pixels per degree
```
1280 px / 86° ≈ 14.9 px/degree
```

### Target pixels per cell
- ≥ 6 px/cell → borderline
- ≥ 8 px/cell → reliable (design target)
- ≥ 10 px/cell → very robust

---

## 📐 Marker Size Calculation (150 mm Cube)

### Target: 1.5 m detection distance, ≥8 px/cell

```
cells = 6
px_target = 8
marker_px ≈ 48 px
angular_width ≈ 48 / 14.9 ≈ 3.22°
physical_width ≈ 2 × 1.5 m × tan(3.22° / 2)
≈ 84 mm
```

➡️ **Minimum recommended marker width: ~84 mm**

### Mapping to the 150 mm cube
- Slot size:  
  ```
  150 × 0.85 = 127.5 mm
  ```
- Plate size (with clearance):  
  ```
  ≈ 127.1 mm
  ```
- Marker coverage:
  - `PLATE_MARGIN_FRACTION = 0.88`
  - Marker area ≈ **112 mm**
  - Cell size ≈ **18.7 mm**
  - Quiet zone ≈ **7.5 mm per side**

This comfortably exceeds the 8 px/cell target at 1.5 m and improves robustness at longer distances.

---

## ⚠️ Long Bridges & Bambu Studio Warning

When importing `cube_with_slots.stl` into **Bambu Studio**, you may see:

> **“Floating cantilever / unsupported overhang”**

### Why this happens
- The cube intentionally contains a **large internal roof bridge**
- There are **no generated supports by design**
- Bambu Studio flags this heuristically, even though modern printers (including the **P2S**) can print long bridges reliably

### This warning is expected
✔ The geometry is intentional  
✔ The part is printable without supports  
✔ The warning can be safely ignored

### Geometry tweaks applied to help bridging
- **Chamfered slot inner edges** to avoid starting extrusion in mid-air
- Optional **internal ribs / roof gussets** to:
  - Reduce effective bridge span
  - Stiffen the roof
  - Improve first bridge layer anchoring

### Recommended slicer setting
- **Bridge speed:** **15 mm/s** (reduced from default ~50 mm/s)

If you observe minor droop:
- Slightly lower nozzle temperature (−5 °C)
- Increase part cooling during bridges

---

## ▶️ Running the Generator

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m src.aruco_cube_gen
```

---

## 📦 Output Layout

Each run creates a **new timestamped folder**:

```
out_stls_YYYY-MM-DD_HH-MM-SS/
├── cube_with_slots.stl
├── plate_base.stl
├── plate_base_id0.stl
├── plate_marker_id0.stl
├── plate_combined_id0.stl
├── ...
└── run_info.txt
```

`run_info.txt` records:
- Cube dimensions
- Plate & bezel dimensions
- Marker size and dictionary
- Plate IDs
- Text settings

---

## 🧱 Assembly

1. Press-fit plates into cube recesses
2. Bezel hides seam and shadow lines
3. Optional tiny CA glue dot on **back corners only**
4. Use cube with the **open face down**

---

## 📜 License
MIT License

