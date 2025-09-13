#!/usr/bin/env python3

"""
simulate_simscan_defocus_min_v7.py
----------------------------------
Generate **one prepared `.ptyd` per defocus** using SimScan, but avoid the
probe-creation propagation path entirely (which was failing on geometry.distance).
Instead, encode defocus diversity by changing the **detector distance** per run:

    distance_eff = base_distance + z_defocus

Thus no `illumination.propagation` block is used.

Descriptor-friendly choices (per your build’s feedback):
  • p.scans.sim.data.name = "SimScan"
  • p.scans.sim.data.{dfile, save, shape, num_frames}
  • p.scans.sim.data.psize = <m>
  • p.scans.sim.data.energy = <keV>
  • p.scans.sim.data.detector.distance = distance_eff
  • p.scans.sim.illumination.model = "recon"; recon.rfile = <.ptyr>
  • p.scans.sim.sample.fill = 1+0j
  • (NO illumination.propagation block at all)

Usage:
  python simulate_simscan_defocus_min_v7.py \
    --out out_sims2 \
    --defocus-m 0.0 0.2e-3 0.5e-3 \
    --probe-rfile out_probe/recons/moonflower_probe_DM_0040.ptyr \
    --shape 256 \
    --steps 40 \
    --spacing 50e-9 \
    --psize 55e-6 \
    --distance 0.8 \
    --energy 0.7 \
    --photons 2e7
"""

import argparse
from pathlib import Path
import ptypy
import ptypy.utils as u
from ptypy.core import Ptycho

def build_param_tree(dfile, shape, steps, spacing, psize, base_distance, energy, photons,
                     z_defocus, probe_rfile):
    p = u.Param()
    p.verbose_level = "info"
    p.io = u.Param(home=str(Path(dfile).parent))

    # Single scan with SimScan
    p.scans = u.Param()
    sc = p.scans.sim = u.Param()
    sc.name = "Full"

    # Data block (all geometry hints live here)
    d = sc.data = u.Param()
    d.name = "SimScan"
    d.dfile = str(dfile)
    d.save  = "append"
    d.shape = int(shape)
    d.num_frames = int(steps*steps)
    d.psize = float(psize)               # detector pixel size [m]
    d.energy = float(energy)             # photon energy [keV]
    d.detector = u.Param()
    d.detector.distance = float(base_distance + z_defocus)  # encode defocus as distance change

    d.xy = u.Param()
    d.xy.model = "raster"
    d.xy.steps = int(steps)
    d.xy.spacing = float(spacing)

    # Illumination from reconstructed probe; NO propagation block
    ill = sc.illumination = u.Param()
    ill.model = "recon"
    ill.recon = u.Param()
    ill.recon.rfile = str(probe_rfile)
    ill.photons = float(photons)
    ill.aperture = None
    # no ill.propagation

    # Uniform sample
    sc.sample = u.Param()
    sc.sample.fill = 1.0 + 0.0j

    return p

def run_one(out_dir, z, shape, steps, spacing, psize, base_distance, energy, photons, probe_rfile):
    sign = "+" if z >= 0 else "-"
    z_mm = abs(z) * 1e3
    dfile = Path(out_dir) / f"simscan_defocus_{sign}{z_mm:0.3f}mm.ptyd"
    p = build_param_tree(dfile, shape, steps, spacing, psize, base_distance, energy, photons,
                         z, probe_rfile)
    P = Ptycho(p, level=2)
    print(f"Wrote {dfile} | frames={steps*steps} | distance={base_distance+z:.6f} m (Δ={z:.3e} m)")
    return dfile

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--defocus-m", type=float, nargs="+", required=True)
    ap.add_argument("--probe-rfile", type=Path, required=True)
    ap.add_argument("--shape", type=int, default=256)
    ap.add_argument("--steps", type=int, default=40, help="Square raster steps (frames=steps^2)")
    ap.add_argument("--spacing", type=float, default=50e-9)
    ap.add_argument("--psize", type=float, default=55e-6)
    ap.add_argument("--distance", type=float, default=0.8)
    ap.add_argument("--energy", type=float, default=0.7)
    ap.add_argument("--photons", type=float, default=2e7)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    wrote = []
    for z in args.defocus_m:
        wrote.append(run_one(args.out, z, args.shape, args.steps, args.spacing,
                             args.psize, args.distance, args.energy, args.photons,
                             args.probe_rfile))
    print("Done. Files:")
    for f in wrote:
        print("  ", f)

if __name__ == "__main__":
    main()
