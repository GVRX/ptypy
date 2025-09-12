#  examples/phase_diverse/run_pd_dm.py
import numpy as np
from ptypy.core import Ptycho
from ptypy.utils.phase_diverse import (
    load_defocus_from_ptyd,
    groups_from_view_z,
    expand_probe_layers,
    init_grouped_probes_by_propagation,
)

# ---- user inputs ----
ptyd_path = "data/phase_diverse_example.ptyd"   # your single file
photon_E_eV = 1000.0                            # set correctly!
lambda_m = 1.239841984e-6 / photon_E_eV         # hc=1239.841984 eV*nm → metres
Nm = 3                                          # modes per z-group
dx = dy = 20e-9                                 # probe-plane pixel pitch (m)

# ---- ingest defocus metadata (Option A) ----
defocus_id_per_view, z_m_per_view = load_defocus_from_ptyd(ptyd_path)
defocus_id, z_for_group = groups_from_view_z(z_m_per_view)
Nd = int(np.max(defocus_id)) + 1

# ---- build Ptycho up to level 4 (no iterations yet) ----
P = Ptycho(p={'io': {'autoplot': False, 'autoplot_interval': 0},
              'verbose_level': 3,
              'run': 'R000',
              'scan': {'scan00': {'name': 'BlockFull',
                                  'data': {'name': 'PtydScan', 'source': ptyd_path}}}},
           level=4)

# ---- expand layers and seed grouped probes ----
Nd = expand_probe_layers(P, Nm=Nm, defocus_id=defocus_id, Nd=Nd)
seed_mode = init_grouped_probes_by_propagation(
    P, Nm=Nm, Nd=Nd, z_for_group=z_for_group, lambda_m=lambda_m, dx=dx, dy=dy, base_group=0
)
print(f"Initialised grouped probes via: {seed_mode}")

# ---- switch engine to PD_DM and set params ----
from ptypy.engines.phase_diverse_dm import PD_DM
eng = PD_DM(P, pars=P.p.engine)
eng.p.pd_enabled = True
eng.p.pd_apply_every = 5
eng.p.pd_Nm = Nm
eng.p.pd_Nd = Nd
eng.p.pd_z_for_group = list(map(float, z_for_group))
eng.p.pd_lambda_m = float(lambda_m)
eng.p.pd_dx = float(dx)
eng.p.pd_dy = float(dy)
eng.p.pd_reference_group = 0
eng.p.pd_blend = 1.0
eng.p.pd_robust = "mean"

P.engine = eng
P.run()   # go time
