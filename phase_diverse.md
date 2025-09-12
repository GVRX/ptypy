# Phase-Diverse Ptychography (multi-z probes)

This engine enables joint reconstruction of datasets acquired at multiple object positions along the optical axis (z). It expands the probe stack to hold `Nm × Nd` modes, where `Nm` is modes per defocus group and `Nd` is the number of z positions. Every few iterations, it enforces that all groups are mutually consistent by Fresnel propagation to a reference plane, averaging there, and back-propagating.

## Data layout

Use a single `.ptyd` and add:

- `entry/data/defocus_index` — `int` array, length = #views, values in `[0 .. Nd-1]`
- `entry/data/defocus_z_m` — `float` array (metres), same length

The helper `load_defocus_from_ptyd` reads these fields and `groups_from_view_z` maps unique z values to contiguous group ids.

## Quick start

1. Build `P = Ptycho(..., level=4)`.
2. Call `expand_probe_layers(P, Nm, defocus_id)` to remap view→probe layers and allocate `Nm×Nd` modes.
3. Call `init_grouped_probes_by_propagation(...)` to seed additional groups from the base group using Fresnel propagation (uses PtyPy’s propagator if available; otherwise FFT angular spectrum).
4. Use engine `PD_DM` and set:

```python
eng.p.pd_enabled = True
eng.p.pd_apply_every = 5
eng.p.pd_Nm = Nm
eng.p.pd_Nd = Nd
eng.p.pd_z_for_group = [z0, z1, ...]   # metres
eng.p.pd_lambda_m = lambda_m           # metres
eng.p.pd_dx = dx; eng.p.pd_dy = dy     # metres per pixel in probe plane
eng.p.pd_reference_group = 0
