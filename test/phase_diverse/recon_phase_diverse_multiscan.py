#!/usr/bin/env python3

"""
recon_phase_diverse_multiscan_v3.py
-----------------------------------
Multi-scan reconstruction from prepared `.ptyd` files.
Compatible with PtyPy 0.9-style descriptors (per docs: use PtydScan + source='file' + dfile).

Usage:
  python recon_phase_diverse_multiscan_v3.py \
    --ptyd out_sims/moonflower_defocus_+0.000mm.ptyd \
           out_sims/moonflower_defocus_+0.200mm.ptyd \
           out_sims/moonflower_defocus_+0.500mm.ptyd \
    --engine DM \
    --iters 300
"""

import argparse
from ptypy import utils as u
from ptypy.core import Ptycho

def build_params(ptyd_paths, engine_name="DM", iters=300):
    p = u.Param()

    # Quiet plotting/interaction
    p.io = u.Param()
    p.io.autoplot = u.Param(active=False)
    p.io.interaction = u.Param(active=False)

    # Scans
    p.scans = u.Param()
    for i, f in enumerate(ptyd_paths):
        label = f"d{i:02d}"
        s = u.Param()
        s.name = "Full"                 # any standard scan model
        s.data = u.Param()
        s.data.name = "PtydScan"        # <- reader for prepared data
        s.data.source = "file"          # <- tell it we're reading from file
        s.data.dfile = f                # <- path to .ptyd
        p.scans.__setattr__(label, s)

    # Engine
    p.engines = u.Param()
    e = u.Param()
    e.name = engine_name               # "DM" or custom (e.g., "DM_PD")
    e.numiter = int(iters)
    # Use canonical key name to satisfy older descriptors
    p.engines.engine00 = e

    return p

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ptyd", nargs="+", required=True,
                    help="List of .ptyd files (one per defocus plane).")
    ap.add_argument("--engine", default="DM",
                    help="Engine name (e.g., DM, ML, or custom DM_PD).")
    ap.add_argument("--iters", type=int, default=300,
                    help="Total iterations.")
    args = ap.parse_args()

    p = build_params(args.ptyd, engine_name=args.engine, iters=args.iters)
    P = Ptycho(p, level=5)

if __name__ == "__main__":
    main()
