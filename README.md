# 📦 ArUco Cube STL Generator

Generate a **hollow calibration cube** and **multicolor ArUco marker plates** entirely in Python — designed for **robust visual detection** at up to ~**1.5 m** using the **Intel RealSense D455 RGB camera**, and optimized for **Bambu Lab AMS** multi-color printing.

This project is intentionally **simple and hackable** — no GUI, no over-engineering, just:

> **Python → STL → slice → print**

---

## 🚀 What This Version Is Optimized For

This iteration focuses on **print reliability first**, especially for large hollow geometry:

- **No internal roof panel**
- **No long internal bridges**
- **No sudden floating cantilevers**
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
- No flat internal roof
- No attic roof
- No internal bridge tricks

These approaches caused **unavoidable slicer artifacts** and **sudden unsupported extrusion paths**.

### ✅ What replaces it
The top face is now **structurally identical to the side faces**, with one key difference:

> **The flat slot floor inside the top recess is removed.**

The top is therefore **open**, but still fully functional.

---

## 🧱 Top Slot Seating Strategy

The top face works exactly like the side faces:

- Same **slot size**
- Same **slot depth**
- Same **45° mitered (tapered) slot walls**

### Plate seating
- The ArUco plate **does NOT sit on a flat ledge**
- It seats **entirely on the 45° mitered walls**
- This is mechanically stable and print-robust

---

## 🛠 Internal 45° Perimeter Support Ramp

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

## 🧩 Slot System

- All slots use **tapered (mitered) walls**
- Eliminates 90° internal overhangs
- Improves slot quality on vertical faces

> ⚠️ Changing slot taper requires reprinting plates.

---

## 🧩 ArUco Plate Generator

- **4×4 ArUco markers** (`DICT_4X4_50`, `borderBits = 1`)
- **2.4 mm thick plug**
- **0.8 mm raised black cells** for AMS two-color printing
- **Integrated bezel (flange)**:
  - Overlaps the slot opening
  - Hides seam and shadow lines
  - Improves visual contrast
  - Allows **face-up printing** (matte surface)

### Optional Plate ID Text
- Embossed ID in the white quiet zone
- Slicer-safe geometry

---

## 🧠 Design Rationale (Intel RealSense D455)

- RGB resolution: **1280 px**
- Horizontal FOV: **~86°**
- Target: ≥ **8 px per marker cell** at **1.5 m**

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
2. Bezel hides seam and shadow lines
3. Optional tiny CA glue dot on **back corners only**
4. Use cube with the **open face down**

---

## 🧭 Design Evolution & Lessons Learned

This project went through several geometry iterations driven by **actual slicer layer inspection**, not theory.

### 1. Flat internal roof + bridge tricks (rejected)
- Long internal bridges *can* print, but slicers introduce:
  - inconsistent anchoring
  - unpredictable bridge ordering
  - sudden unsupported paths
- Result: visually acceptable in previews, unreliable in real prints.

**Lesson:** slicer heuristics are not guarantees.

---

### 2. Attic roofs, corbels, stepped supports (rejected)
- Slopes and corbels reduced bridge length, but:
  - introduced asymmetry between faces
  - caused sudden geometry “pop-in” at specific layers
  - still produced floating cantilevers at corners

**Lesson:** partial support is worse than continuous support.

---

### 3. Open top with miter-only seating (kept)
- Top slot made **identical to side slots**
- Flat slot floor removed
- Plate seats purely on the **45° mitered walls**

**Lesson:** flat ledges are not required for plate seating.

---

### 4. Continuous 45° perimeter ramp (final)
- Added **material only below the top slot floor**
- Ramp starts lower and moves inward gradually
- No layer ever introduces a new unsupported perimeter

**Lesson:**  
> If a feature appears suddenly at one layer, it will fail.  
> If it grows gradually, slicers behave predictably.

---

### Final Principle
> **Design for layer continuity, not just static geometry.**

Every successful feature in this model:
- either grows gradually layer-to-layer  
- or is fully supported by the layer below  

This single principle eliminated all “floating cantilever” failures.

---

## 📜 License
MIT License
