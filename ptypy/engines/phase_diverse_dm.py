# ptypy/engines/phase_diverse_dm.py 
import numpy as np
from ptypy.engines.DM import DM

try:
    import cupy as cp
    _has_cupy = True
except Exception:
    cp = None
    _has_cupy = False

def _xp_of(arr):
    return cp if (_has_cupy and isinstance(arr, cp.ndarray)) else np

def _fft2(xp, x):   return xp.fft.fftshift(xp.fft.fft2(xp.fft.ifftshift(x)))
def _ifft2(xp, X):  return xp.fft.fftshift(xp.fft.ifft2(xp.fft.ifftshift(X)))

def _make_H(xp, lambda_m, z_m, Nx, Ny, dx, dy):
    fx = (xp.arange(Nx) - Nx//2) / (Nx*dx)
    fy = (xp.arange(Ny) - Ny//2) / (Ny*dy)
    FX, FY = xp.meshgrid(fx, fy, indexing='ij')
    return xp.exp(-1j * xp.pi * lambda_m * z_m * (FX*FX + FY*FY))

class PD_DM(DM):
    """
    Phase-diverse DM: maintains Nm modes per defocus group (Nd groups) and
    every pd_apply_every iterations enforces that all groups are related by
    propagation to a common reference plane (average there; back-prop out).

    Extra engine params (set on engine.p):
      pd_enabled: bool
      pd_apply_every: int
      pd_Nm: int
      pd_Nd: int
      pd_z_for_group: list[float] (metres), len=Nd
      pd_lambda_m: float (metres)
      pd_dx: float (metres)
      pd_dy: float (metres)
      pd_reference_group: int
      pd_blend: float in [0,1] (optional; default 1.0 = full overwrite)
      pd_robust: str in {"mean","median"} (optional; default "mean")
    """
    def __init__(self, ptycho, pars=None):
        super().__init__(ptycho, pars)
        p = self.p
        self.pd_enabled = bool(getattr(p, 'pd_enabled', True))
        self.apply_every = int(getattr(p, 'pd_apply_every', 5))
        self.Nm = int(getattr(p, 'pd_Nm', 1))
        self.Nd = int(getattr(p, 'pd_Nd', 1))
        self.ref_g = int(getattr(p, 'pd_reference_group', 0))
        self.lambda_m = float(getattr(p, 'pd_lambda_m'))
        self.dx = float(getattr(p, 'pd_dx'))
        self.dy = float(getattr(p, 'pd_dy'))
        self.blend = float(getattr(p, 'pd_blend', 1.0))
        self.robust = str(getattr(p, 'pd_robust', 'mean')).lower()

        pr = self.ptycho.probe
        self._A = pr._a  # (Nm*Nd, Nx, Ny); numpy or cupy depending on accel path
        Nm_total, self.Nx, self.Ny = self._A.shape
        assert Nm_total == self.Nm * self.Nd, (Nm_total, self.Nm*self.Nd)
        self.xp = _xp_of(self._A)

        # Precompute transfer functions to/from reference plane
        z_for_group = np.asarray(getattr(p, 'pd_z_for_group'), dtype=float)
        z_ref = float(z_for_group[self.ref_g])
        self.H_to_ref = []
        self.H_from_ref = []
        for g in range(self.Nd):
            dz = z_ref - float(z_for_group[g])
            H = _make_H(self.xp, self.lambda_m, dz, self.Nx, self.Ny, self.dx, self.dy)
            self.H_to_ref.append(H)
            self.H_from_ref.append(self.xp.conj(H))  # inverse for angular spectrum

    def _prop(self, E, H):
        return _ifft2(self.xp, _fft2(self.xp, E) * H)

    def _consensus(self):
        if not self.pd_enabled or self.Nd <= 1:
            return

        pr = self.ptycho.probe
        A = pr._a  # keep live reference (engine may be on GPU)
        xp = _xp_of(A)

        # (Nd, Nm, Nx, Ny)
        G = A.reshape(self.Nd, self.Nm, self.Nx, self.Ny)

        # 1) propagate to ref plane
        Ref = xp.zeros((self.Nm, self.Nx, self.Ny), dtype=G.dtype)
        Stack = xp.empty_like(G)
        for g in range(self.Nd):
            H = self.H_to_ref[g]
            for m in range(self.Nm):
                Eg = G[g, m]
                Er = self._prop(Eg, H)
                Stack[g, m] = Er
                Ref[m] += Er

        # 2) robust combine across groups
        if self.robust == 'median':
            Ref = xp.median(Stack, axis=0)
        else:
            Ref /= float(self.Nd)

        # 3) back-prop and blend into groups
        for g in range(self.Nd):
            Hinv = self.H_from_ref[g]
            for m in range(self.Nm):
                Eg_new = self._prop(Ref[m], Hinv)
                if self.blend >= 1.0:
                    G[g, m] = Eg_new
                elif self.blend <= 0.0:
                    pass
                else:
                    G[g, m] = (1.0 - self.blend) * G[g, m] + self.blend * Eg_new

        # write back
        A[:] = G.reshape(self.Nm * self.Nd, self.Nx, self.Ny)

    def engine_iterate(self, num=1):
        for _ in range(num):
            super().engine_iterate(1)
            if self.pd_enabled and ((self.curiter + 1) % self.apply_every == 0):
                self._consensus()
