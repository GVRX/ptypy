# ptypy/utils/phase_diverse.py 
import numpy as _np

try:
    import h5py as _h5
except Exception:
    _h5 = None

# -----------------------------
# Defocus metadata (Option A)
# -----------------------------
def load_defocus_from_ptyd(ptyd_path, idx_path="entry/data/defocus_index", z_path="entry/data/defocus_z_m"):
    """
    Read defocus groups and z offsets from a single .ptyd HDF5.
    Returns: defocus_id (int array, len=#views), z_m_per_view (float array, metres).
    """
    if _h5 is None:
        raise RuntimeError("h5py not available; cannot read defocus metadata.")
    with _h5.File(ptyd_path, "r") as f:
        defocus_id = _np.array(f[idx_path], dtype=_np.int64)
        z_m = _np.array(f[z_path], dtype=_np.float64)
    if defocus_id.shape != z_m.shape:
        raise ValueError(f"Shape mismatch: {defocus_id.shape} vs {z_m.shape}")
    return defocus_id, z_m


def groups_from_view_z(z_m_per_view, atol=1e-12):
    """
    Map each unique z to a compact group id in [0..Nd-1], preserving order of first appearance.
    Returns: defocus_id (per view), z_for_group (list length Nd)
    """
    uniq = []
    gid = _np.zeros_like(z_m_per_view, dtype=_np.int64)
    for i, z in enumerate(z_m_per_view):
        found = False
        for g, zref in enumerate(uniq):
            if abs(z - zref) <= atol:
                gid[i] = g
                found = True
                break
        if not found:
            gid[i] = len(uniq)
            uniq.append(z)
    return gid, _np.array(uniq, dtype=_np.float64)


# -----------------------------
# Probe layer expansion
# -----------------------------
def expand_probe_layers(P, Nm, defocus_id, Nd=None):
    """
    Remap per-view probe mode index from [0..Nm-1] to [0..Nm*Nd-1] by
    pr_layer <- g*Nm + old_mode, where g is the defocus group for that view.
    Then call P.probe.reformat() to allocate the expanded stack.
    """
    views = list(P.diff.views.values())
    if Nd is None:
        Nd = int(_np.max(defocus_id)) + 1

    for i, dv in enumerate(views):
        g = int(defocus_id[i])
        for _, pod in dv.pods.items():
            pod.pr_view.layer = g * Nm + pod.pr_view.layer

    P.probe.reformat()
    return Nd


# -----------------------------
# Propagation: prefer PtyPy’s own if present, else angular spectrum
# -----------------------------
def _fft2(x):   return _np.fft.fftshift(_np.fft.fft2(_np.fft.ifftshift(x)))
def _ifft2(X):  return _np.fft.fftshift(_np.fft.ifft2(_np.fft.ifftshift(X)))

def _make_H(lambda_m, z_m, Nx, Ny, dx, dy):
    fx = (_np.arange(Nx) - Nx//2) / (Nx*dx)
    fy = (_np.arange(Ny) - Ny//2) / (Ny*dy)
    FX, FY = _np.meshgrid(fx, fy, indexing='ij')
    return _np.exp(-1j * _np.pi * lambda_m * z_m * (FX*FX + FY*FY))

def _propagate_fft(E, H):
    return _ifft2(_fft2(E) * H)

def _get_ptypy_propagator_or_none():
    """
    Try to retrieve a PtyPy propagator that can do near-field propagation
    on the probe grid. If unavailable, return None.
    """
    try:
        # Fresnel / angular-spectrum live behind the Propagator registry
        from ptypy.core.propagator import Propagator
        # "fresnel" or "nearfield" names vary by recipe; try 'fresnel'
        if 'fresnel' in Propagator.D:  # registry dict
            return Propagator.D['fresnel']
        if 'Fresnel' in Propagator.D:
            return Propagator.D['Fresnel']
        # Fallbacks: some builds have "Fraunhofer" only; not suitable for small z.
        return None
    except Exception:
        return None

def init_grouped_probes_by_propagation(P, Nm, Nd, z_for_group, lambda_m, dx, dy, base_group=0):
    """
    Seed extra groups’ Nm modes by propagating base_group modes to each group's z.
    Prefers a PtyPy propagator if available; otherwise uses angular spectrum FFT.
    """
    pr = P.probe
    arr = pr._a  # shape (Nm*Nd, Nx, Ny)
    Nm_total, Nx, Ny = arr.shape
    assert Nm_total == Nm*Nd, (Nm_total, Nm*Nd)

    prop_class = _get_ptypy_propagator_or_none()

    if prop_class is None:
        # FFT angular-spectrum path
        H = []
        z0 = z_for_group[base_group]
        for g in range(Nd):
            dz = float(z_for_group[g] - z0)
            H.append(_make_H(lambda_m, dz, Nx, Ny, dx, dy))
        for m in range(Nm):
            Eb = arr[base_group*Nm + m]
            for g in range(Nd):
                if g == base_group:
                    continue
                arr[g*Nm + m] = _propagate_fft(Eb, H[g])
        pr._a[:] = arr
        return 'fft'

    else:
        # PtyPy propagator path; construct once per dz and reuse
        # Propagator signature: prop_class(pars) then .propagate(field, pars)
        # We emulate minimal pars required by Fresnel in PtyPy.
        pars_template = dict(wavelength=lambda_m, dx=dx, dy=dy)
        props = []
        z0 = float(z_for_group[base_group])
        for g in range(Nd):
            dz = float(z_for_group[g] - z0)
            pars = dict(pars_template)
            pars['z'] = dz
            props.append(prop_class(pars))

        for m in range(Nm):
            Eb = arr[base_group*Nm + m]
            for g in range(Nd):
                if g == base_group:
                    continue
                arr[g*Nm + m] = props[g].propagate(Eb)
        pr._a[:] = arr
        return 'ptypy-propagator'
