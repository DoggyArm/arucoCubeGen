# 📦 ArUco Cube STL Generator

Generate a **hollow calibration cube** and **multicolor ArUco marker plates** entirely in Python — designed for **robust visual detection** at up to ~**1.5 m** using the **Intel RealSense D455 RGB camera**, and optimized for **Bambu Lab AMS** multi-color printing.

This project is intentionally **simple and hackable** — no GUI, no over-engineering, just:

> **Python → STL → slice → print**

---

## 🚀 What This Version Is Optimized For

This iteration focuses on **print reliability first**, especially for large hollow geometry and mating parts:

- **No internal roof panel**
- **No long internal bridges**
- **No sudden floating cantilevers**
- **No decorative overhangs**
- **Predictable, slicer-friendly layer progression**

All geometry changes are driven by **actual slicer layer analysis**, not heuristics.

---

## 🧊 Cube Generator

### Core Geometry
- Hollow cube with:
  - **Outer edge: 150 mm**
  - **Wall thickness: 3.2 mm**
  - **Five recessed faces**  
    (top, +X, −X, +Y, −Y)
  - **Open bottom** (rim retained for stiffness and access)
- Recess depth: **2.4 mm**, matching plate thickness
- Designed for **upright printing** (open bottom on the bed)

---

## 🔺 Open Top Design (Important)

### ❌ What was removed
- Flat internal roof
- Attic roofs / corbels
- Internal bridge tricks

These approaches caused **unavoidable slicer artifacts** and **sudden unsupported extrusion paths**.

### ✅ What replaces it
The top face is now **structurally identical to the side faces**, with one key difference:

> **The flat slot floor inside the top recess is removed.**

The top is therefore **open**, but still fully functional.

---

## 🧱 Slot Seating Strategy (Cube)

All faces — including the top — use the **same slot geometry**:

- Same **slot size**
- Same **slot depth**
- Same **45° mitered (tapered) slot walls**

There are **no flat ledges** anywhere in the slot system.

### Why this works
- Plates seat on the **mitered walls only**
- Contact is self-centering and mechanically stable
- Flat ledges are not required for alignment or retention

---

## 🛠 Internal 45° Perimeter Support Ramp (Cube)

To avoid sudden **floating cantilevers**, the cube includes a **continuous internal perimeter ramp**:

- Starts **below** the top slot floor
- Runs from the **inner vertical walls**
- Gradually slopes upward at **45°**
- Meets the **inner edge of the top slot floor**

This ensures:
- Each layer is supported by the one below
- No abrupt geometry appears mid-print
- No slicer-induced “start printing in air” behavior

The ramp:
- **Adds material only**
- **Does not modify anything above the slot floor**
- Exists purely to improve printability

---

## 🧩 ArUco Plate Generator

### Plate Geometry (Updated)
Plates are now **pure mitered plugs**:

- **No bezel / flange**
- **No horizontal overhangs**
- **No decorative geometry**

Each plate:
- Matches the cube slot **exactly**
- Seats **only on the 45° mitered walls**
- Sits flush inside the recess

This mirrors the cube design philosophy and eliminates all plate-side cantilevers.

---

### Marker Geometry
- **4×4 ArUco markers** (`DICT_4X4_50`, `borderBits = 1`)
- **2.4 mm thick plug**
- **0.8 mm raised black cells** for AMS two-color printing

---

### Plate ID Text (Revised)
- Optional ID text is placed **directly on the plug face**
- Slightly embedded to avoid coplanar faces
- Constrained to the **quiet zone**
- Fully supported on every layer

No text geometry prints in mid-air.

---

## 🧠 Design Rationale (Intel RealSense D455)

- RGB resolution: **1280 px**
- Horizontal FOV: **~86°**
- Marker grid: **6×6 cells** (4×4 data + border)
- Target: ≥ **8 px per cell** at **1.5 m**

Slot and marker sizing exceed this threshold with margin.

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

Each run creates a timestamped directory:

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

1. Press-fit plates into the recesses
2. Plates sit flush on the mitered walls
3. Optional tiny CA glue dot on **back corners only**
4. Use cube with the **open face down**

---

## 🧭 Design Evolution & Lessons Learned

This project went through several geometry iterations driven by **actual slicer layer inspection**, not theory.

### 1. Flat internal roofs and bridges (rejected)
- Long bridges *sometimes* print, but slicers introduce:
  - unpredictable anchoring
  - bridge ordering artifacts
  - sudden unsupported paths

**Lesson:** slicer heuristics are not guarantees.

---

### 2. Attic roofs, corbels, stepped supports (rejected)
- Reduced bridge span but:
  - caused geometry “pop-in” at specific layers
  - still produced floating cantilevers at corners

**Lesson:** partial support is worse than continuous support.

---

### 3. Miter-only seating (kept)
- Slots made identical on all faces
- Flat ledges removed
- Both cube and plates seat on **45° mitered walls only**

**Lesson:** flat ledges are unnecessary and harmful for print reliability.

---

### 4. Continuous 45° perimeter ramp (final)
- Added **material only below the top slot floor**
- Ramp grows inward gradually, layer by layer
- No layer introduces a new unsupported perimeter

**Lesson:**  
> If a feature appears suddenly at one layer, it will fail.  
> If it grows gradually, slicers behave predictably.

---

### Final Principle
> **Design for layer continuity, not static geometry.**

Every successful feature in this model:
- either grows gradually layer-to-layer  
- or is fully supported by the layer below  

This principle eliminated all “floating cantilever” failures.

---

## 📜 License
MIT License
