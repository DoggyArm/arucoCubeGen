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
- A **printing-friendly “attic roof”** to reduce long internal bridging
- **Mitered (tapered) slot edges** to avoid 90° “start in air” overhangs

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

#### 🧱 Printing-friendly internal geometry
To make the cube printable without supports (and with cleaner bridging), the cube includes:

**1) Roof thickener (inside-only)**
- Adds material *from the inside* at the roof to stiffen the large internal span
- Controlled by: `roof_extra_thickness_mm`
- Does **not** change the cube’s external dimensions

**2) “Attic roof” (internal slopes)**
- Adds shallow internal slopes along the inside walls up to the roof underside
- Reduces the *effective* bridge distance and improves first bridge-layer anchoring
- Controlled by:
  - `attic_drop_mm` (vertical drop at the walls)
  - `attic_margin_mm` (overlap safety margin)

---

### 🧩 Slot System (Plates + Cube)
The plate system is designed for **repeatable press-fit assembly** and better printability.

#### 🔻 Mitered (tapered) slot edges
The cube’s recessed slots are **tapered** so the slot has a wider opening and a slightly smaller inner face.

**Why it helps**
- Avoids sharp internal 90° ceilings where extrusion would otherwise “start in air”
- Improves print reliability on the slot roof edges
- Makes insertion smoother and reduces edge scraping

**Key parameters**
- `slot_depth` — depth of the recess
- `slot_miter_mm` — taper amount (for a true 45° draft, set equal to `slot_depth`)

> ⚠️ If you change taper settings, you must reprint plates so their plug taper matches.

#### 🛡 Attic keepout (important)
The attic and roof thickener **add material** on the inside of the cube. A keepout region is applied around the **top slot cavity** to prevent boolean overlap.

- Controlled by: `attic_keepout_margin_mm`
- Ensures the **top slot surface stays planar and flat**

---

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
- Designed to be slicer-safe

---

## 🧠 Design Rationale (Intel RealSense D455)

### Camera assumptions
- RGB resolution: **1280 px horizontal**
- Horizontal FOV: **~86°**
- Marker grid: **6×6 cells** (4×4 data + border)

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

Target: **1.5 m detection distance**, ≥ **8 px/cell**

```
marker_px ≈ 48 px
angular_width ≈ 3.22°
physical_width ≈ 84 mm
```

➡️ **Minimum recommended marker width: ~84 mm**

Mapped to cube geometry:
- Slot size: `150 × 0.85 = 127.5 mm`
- Plate size: `≈ 127.1 mm`
- Marker area: `≈ 112 mm`
- Cell size: `≈ 18.7 mm`

---

## ⚠️ Bambu Studio Bridge Warning

Bambu Studio may report **unsupported overhangs** due to the large internal roof bridge.

✔ Geometry is intentional
✔ Designed for support-free printing
✔ Warning can be safely ignored

**Recommended slicer tweaks**:
- Bridge speed: **15 mm/s**
- Slightly lower nozzle temperature if needed
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

Each run creates a timestamped folder:

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

---

## 🧱 Assembly

1. Press-fit plates into cube recesses
2. Bezel hides seam and shadow lines
3. Optional tiny CA glue dot on **back corners only**
4. Use cube with the **open face down**

---

## 📜 License
MIT License

