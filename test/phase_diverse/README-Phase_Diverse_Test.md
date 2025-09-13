# Phase-Diverse Ptychography: Simulate → Verify → Reconstruct

This cookbook shows a minimal, repeatable flow to generate defocus-diverse **`.ptyd`** files, sanity-check them, and run a **multi-scan** reconstruction (shared object optional later).

---

## 0) Prerequisites

- A reconstructed probe to seed the simulator, e.g.:
  ```
  out_probe/recons/moonflower_probe_DM_0040.ptyr
  ```
  generated with:
  ```
  make_probe_from_moonflower.py
  ```



- Helper scripts:
  - `simulate_simscan_defocus.py`  ← SimScan generator (one `.ptyd` per defocus)
  - `inspect_ptyd_structure.py`           ← quick HDF5 tree inspector
  - `recon_phase_diverse_multiscan.py` ← multi-scan recon runner

> Tip: For testing on modest hardware, start with smaller frames/shape and fewer iterations.

---

## 1) Simulate one `.ptyd` per defocus (SimScan; per-plane distance)

Encode defocus diversity by setting **`data.detector.distance = base_distance + z_defocus`** for each simulated plane.

```bash
python simulate_simscan_defocus_min.py   --out out_sims2   --defocus-m 0.0 0.2e-3 0.5e-3   --probe-rfile out_probe/recons/moonflower_probe_DM_0040.ptyr   --shape 256   --steps 40   --spacing 50e-9   --psize 55e-6   --distance 0.8   --energy 0.7   --photons 2e7
```
This will output:
```
out_sims2/
  simscan_defocus_+0.000mm.ptyd
  simscan_defocus_+0.200mm.ptyd
  simscan_defocus_+0.500mm.ptyd
```

> Faster test loop: reduce `--steps` (frames = steps²) and `--shape`.

---

## 2) Sanity-check each `.ptyd`

Confirm that the files contain **prepared datasets** (not just metadata) before reconstruction.

```bash
python inspect_ptyd_structure.py out_sims2/simscan_defocus_+0.000mm.ptyd
python inspect_ptyd_structure.py out_sims2/simscan_defocus_+0.200mm.ptyd
python inspect_ptyd_structure.py out_sims2/simscan_defocus_+0.500mm.ptyd
```

**Expected:** a tree of HDF5 groups/datasets (not only `/info`).  
If something looks off, re-run the simulator for that defocus plane.

---

## 3) Multi-scan reconstruction (per-scan probes; shared object optional later)

Treat each defocus plane as a separate scan; start with a stock engine (e.g., **DM**), then try your **phase-diverse** engine.

```bash
python recon_phase_diverse_multiscan.py   --ptyd out_sims2/simscan_defocus_+0.000mm.ptyd          out_sims2/simscan_defocus_+0.200mm.ptyd          out_sims2/simscan_defocus_+0.500mm.ptyd   --engine DM   --iters 300
```

To test phase diverse reconstruction engine (`DM_PD`):

```bash
python recon_phase_diverse_multiscan_v3.py   --ptyd out_sims2/simscan_defocus_+0.000mm.ptyd          out_sims2/simscan_defocus_+0.200mm.ptyd          out_sims2/simscan_defocus_+0.500mm.ptyd   --engine DM_PD   --iters 400
```

**Outputs:** the autosaves/final artifacts your engine writes (e.g. `./recons/*`, `*.ptyr`, images).

---


** Files (reusable inputs/results):**
- Probe used for simulation:
  ```
  out_probe/recons/moonflower_probe_DM_0040.ptyr
  ```
- Simulated data:
  ```
  out_sims2/simscan_defocus_+*.ptyd
  ```
- Reconstruction outputs:
  ```
  recons/*, *.ptyr, diagnostic images/plots
  ```

---

## Minimal Checklist

1. **Probe present** (`*.ptyr`) to drive simulation.
2. **Simulate per defocus** with `simulate_simscan_defocus_min_v7.py` → `.ptyd` files.
3. **Inspect** each `.ptyd` with `inspect_ptyd_structure.py`.
4. **Reconstruct** with `recon_phase_diverse_multiscan_v3.py` (start with DM).
5. **Archive** the `.ptyd`/`.ptyr` and reconstruction outputs; **prune** `*.old` and other cruft.

---

## Troubleshooting Notes

- **Geometry/validation errors during simulation:**  
  The simulator  avoids `illumination.propagation` and encodes defocus by varying `data.detector.distance`.

- **Ptyd reader errors (“contains no data”) during recon:**  
  Re-inspect the `.ptyd` with `inspect_ptyd_structure.py`. If it’s missing datasets, re-run the simulator.
