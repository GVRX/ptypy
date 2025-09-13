#!/usr/bin/env python3

"""
make_probe_from_moonflower.py
--------------------------------
Create a small `.ptyr` file containing a probe using PtyPy's MoonFlowerScan
tutorial settings. This is useful when you need a valid `--probe-rfile` to
feed the SimScan-based simulator (or other recipes).

It follows the official tutorials:
- Use MoonFlowerScan as synthetic data source
- Configure p.io.rfile and p.io.autosave to create `.ptyr` snapshots
- Run a few DM iterations and save a dump

References:
- Getting started (MoonFlowerScan & engines): https://ptycho.github.io/ptypy/rst/getting_started.html
- I/O & autosave to `.ptyr`: https://ptycho.github.io/tutorials/notebooks/basic_examples/02_input_output_parameters.html

Usage:
  python make_probe_from_moonflower.py \
    --out out_probe \
    --shape 256 \
    --photons 1e8 \
    --num-frames 100 \
    --dm-iters 40 \
    --autosave-interval 20

After it finishes, you'll see a path printed to the last autosave `.ptyr`,
which you can use as `--probe-rfile` in the SimScan simulator.
"""
import argparse
import os
from pathlib import Path

import ptypy
import ptypy.utils as u

def main():
    ap = argparse.ArgumentParser(description="Generate a probe .ptyr from MoonFlowerScan (tutorial settings).")
    ap.add_argument("--out", type=Path, required=True, help="Output directory (used as p.io.home).")
    ap.add_argument("--shape", type=int, default=256, help="Diffraction frame side length (pixels).")
    ap.add_argument("--num-frames", type=int, default=100, help="Number of synthetic frames.")
    ap.add_argument("--photons", type=float, default=1e8, help="Mean photons in empty beam.")
    ap.add_argument("--dm-iters", type=int, default=40, help="DM iterations.")
    ap.add_argument("--autosave-interval", type=int, default=20, help="Autosave interval (iterations).")
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)

    p = u.Param()
    p.verbose_level = "info"
    p.run = "moonflower_probe"

    # I/O
    p.io = u.Param()
    p.io.home = str(args.out)

    # Final ptyr filename (after all iterations). Keep, though we mainly rely on autosaves.
    p.io.rfile = "recons/%(run)s_%(engine)s_%(iterations)04d.ptyr"

    # Autosave (dump) every autosave-interval iterations in "dumps/"
    p.io.autosave = u.Param()
    p.io.autosave.active = True
    p.io.autosave.interval = int(args.autosave_interval)
    p.io.autosave.rfile = "dumps/%(run)s_%(engine)s_%(iterations)04d.ptyr"

    # Turn off threaded plotting
    p.io.autoplot = u.Param()
    p.io.autoplot.active = False
    p.io.interaction = u.Param(active=False)

    # Scan setup: MoonFlowerScan per tutorial
    p.scans = u.Param()
    p.scans.MF = u.Param()
    p.scans.MF.name = "Full"      # 'Full' or 'BlockVanilla' both work in tutorials
    p.scans.MF.data = u.Param()
    p.scans.MF.data.name = "MoonFlowerScan"
    p.scans.MF.data.shape = int(args.shape)
    p.scans.MF.data.num_frames = int(args.num_frames)
    p.scans.MF.data.save = None
    p.scans.MF.data.density = 0.2
    p.scans.MF.data.photons = float(args.photons)
    p.scans.MF.data.psf = 0.0

    # Engine: DM
    p.engines = u.Param()
    p.engines.engine00 = u.Param()
    p.engines.engine00.name = "DM"
    p.engines.engine00.numiter = int(args.dm_iters)
    p.engines.engine00.numiter_contiguous = 5

    # Run
    from ptypy.core import Ptycho
    P = Ptycho(p, level=5)

    # Figure out last autosave path (based on p.io.home, run and iteration count)
    # We attempt the last autosave; if not found, print the final rfile if created.
    autosave_dir = Path(p.io.home) / "dumps"
    # Build the expected filename: moonflower_probe_DM_<iters 4d>.ptyr
    last_dump = autosave_dir / f"moonflower_probe_DM_{args.dm_iters:04d}.ptyr"
    if last_dump.exists():
        print("Probe .ptyr (autosave):", last_dump)
    else:
        final_dir = Path(p.io.home) / "recons"
        final_file = final_dir / f"moonflower_probe_DM_{args.dm_iters:04d}.ptyr"
        if final_file.exists():
            print("Probe .ptyr (final):", final_file)
        else:
            print("Finished, but did not locate expected .ptyr in dumps/ or recons/. Check p.io paths.")

if __name__ == "__main__":
    main()
