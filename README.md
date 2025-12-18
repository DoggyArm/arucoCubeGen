# 🧊 Modular 6-Plate ArUco Cube (Drop-In Assembly)

A **modular, 3D-printable cube** made from **six independent plates**, each carrying a **4×4 ArUco marker**, designed for **high-contrast machine vision**, **fast iteration**, and **support-free printing**.

This project is optimized for:
- **Bambu Lab P2S + AMS**
- **Two-color (Black / White) prints**
- **Vision calibration & robotics experiments**
- **Programmatic generation of multiple cube ID sets**

---

## 📸 Renders (Preview)

> _Rendered images go here — placeholders are intentionally included._

### Fully Assembled Cube
![Assembled Cube](docs/renders/cube_assembled.png)

### Exploded View (6 Plates)
![Exploded View](docs/renders/cube_exploded.png)

### Individual Plates
![Top Plate](docs/renders/plate_top.png)  
![Side Plates](docs/renders/plate_side.png)

### Close-Up: Marker Inlay Detail
![Marker Detail](docs/renders/marker_detail.png)

---

## ✨ Key Design Features

- **6 independent plates** (Top + 4 Sides + Bottom / Reference)
- **Drop-in miter / friction joints** — no glue required
- **Chamfered internal edges** to avoid unsupported overhangs
- **Flush black marker tiles** for AMS reliability
- **Hollow interior** to reduce print time and material
- **Programmatic generation** for batch marker ID creation

---

## 🧩 Plate Overview

| Plate | Filename | Notes |
|-----|--------|------|
| Reference / Base | `plate_white.stl` | White-only plate |
| Top | `plate_black_0.stl` | ArUco ID 0 |
| Side 1 | `plate_black_1.stl` | ArUco ID 1 |
| Side 2 | `plate_black_2.stl` | ArUco ID 2 |
| Side 3 | `plate_black_3.stl` | ArUco ID 3 |
| Side 4 | `plate_black_4.stl` | ArUco ID 4 |

---

## 🛠️ Requirements

### Software
- Python **3.9+**
- OpenCV (with ArUco module)
- Mesh generation dependencies:
  ```bash
  pip install numpy shapely trimesh mapbox-earcut manifold3d
  ```

### Hardware
- **Bambu Lab P2S**
- **AMS**
- 0.4 mm nozzle
- PLA / PLA Matte

---

## 🚀 Generating the STL Files

```bash
python -m src.generate
```

---

## 🖨️ Bambu Studio Workflow (AMS)

- Import all STL files
- Assign White to plates, Black to markers
- Supports: **None**
- Layer height: **0.2 mm**

---

## 🔩 Assembly Instructions

1. Place reference plate flat
2. Insert side plates
3. Insert top plate last
4. Press to seat

---

## 📜 License

MIT License
