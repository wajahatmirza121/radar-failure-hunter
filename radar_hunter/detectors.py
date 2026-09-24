"""CFAR detectors behind one interface: detect(power map) -> boolean detection mask."""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from scipy.ndimage import uniform_filter
from scipy.optimize import brentq
from scipy.special import gammaln

from .simulator import G, PFA, T


class Detector(ABC):
    """Common detector interface."""

    name: str

    @abstractmethod
    def detect(self, P: np.ndarray) -> np.ndarray:
        """Return a boolean detection mask for a power map P."""

    @abstractmethod
    def describe(self) -> dict:
        """Human-readable parameters for reports."""


class CACFAR(Detector):
    """Cell-averaging CFAR over the wrapped 2-D training ring."""

    def __init__(self, pfa: float = PFA) -> None:
        self.name, self.pfa = 'CA-CFAR', pfa

    def detect(self, P: np.ndarray) -> np.ndarray:
        ow, iw = 2 * (G + T) + 1, 2 * G + 1
        n = ow * ow - iw * iw
        tot = (uniform_filter(P, ow, mode='wrap') * ow * ow
               - uniform_filter(P, iw, mode='wrap') * iw * iw)
        return P > n * (self.pfa ** (-1 / n) - 1) * tot / n

    def describe(self) -> dict:
        n = (2 * (G + T) + 1) ** 2 - (2 * G + 1) ** 2
        return {'name': self.name, 'training_cells': n,
                'threshold_factor': float(self.pfa ** (-1 / n) - 1)}


def os_alpha(pfa: float, n: int, k: int) -> float:
    """Threshold multiplier alpha for OS-CFAR with n training cells, k-th smallest statistic:
    Pfa = Gamma(n-k+1+alpha) * Gamma(n+1) / (Gamma(n-k+1) * Gamma(n+1+alpha))."""
    ln_ratio = lambda a: (gammaln(n - k + 1 + a) + gammaln(n + 1)
                          - gammaln(n - k + 1) - gammaln(n + 1 + a) - np.log(pfa))
    return float(brentq(ln_ratio, 0.0, 1e3))


_RING_MASK: np.ndarray | None = None


def _ring_mask() -> np.ndarray:
    """Boolean (win, win) mask of the training ring (outer window minus guard square), cached."""
    global _RING_MASK
    if _RING_MASK is None:
        win, inner = 2 * (G + T) + 1, 2 * G + 1
        m = np.ones((win, win), bool)
        c, h = win // 2, inner // 2
        m[c - h:c + h + 1, c - h:c + h + 1] = False
        _RING_MASK = m
    return _RING_MASK


class OSCFAR(Detector):
    """Ordered-statistic CFAR (Rohling): noise level = k-th smallest training cell, k = 0.75 * N."""

    def __init__(self, pfa: float = PFA, k_frac: float = 0.75) -> None:
        self.name, self.pfa, self.k_frac = 'OS-CFAR', pfa, k_frac
        self.n = (2 * (G + T) + 1) ** 2 - (2 * G + 1) ** 2
        self.k = int(k_frac * self.n)
        self.alpha = os_alpha(pfa, self.n, self.k)

    def detect(self, P: np.ndarray) -> np.ndarray:
        win = 2 * (G + T) + 1
        pad = np.pad(P.astype(np.float32), win // 2, mode='wrap')
        view = sliding_window_view(pad, (win, win))      # wrapped training window for every cell
        ring = view[..., _ring_mask()]                   # (rows, cols, n) training values
        kth = np.sort(ring, axis=-1)[..., self.k - 1]    # k-th smallest per cell
        return P > self.alpha * kth

    def describe(self) -> dict:
        return {'name': self.name, 'training_cells': self.n, 'k': self.k, 'alpha': self.alpha}
