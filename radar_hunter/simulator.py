"""Range-Doppler map simulation and Monte-Carlo detector evaluation."""
from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

import numpy as np

if TYPE_CHECKING:                                   # avoid a runtime import cycle
    from .detectors import Detector

NR, ND, G, T, PFA = 128, 64, 2, 8, 1e-4             # map size, guard cells, training cells, design Pfa


class Scenario(TypedDict):
    snr_db: float
    r: int
    d: int
    cnr_db: float
    int_db: float
    dr: int
    dd: int


def cx(rng: np.random.Generator, *shape: int) -> np.ndarray:
    """Unit-power complex Gaussian sample."""
    return (rng.normal(size=shape) + 1j * rng.normal(size=shape)) / np.sqrt(2)


def clean_scenario(snr_db: float, r: int = 64, d: int = 32) -> Scenario:
    """Target-only scenario used for validation against Swerling-I theory."""
    return Scenario(snr_db=snr_db, r=r, d=d, cnr_db=-60, int_db=-60, dr=0, dd=0)


def make_map(s: Scenario, rng: np.random.Generator) -> tuple[np.ndarray, tuple[int, int]]:
    """Simulate one range-Doppler power map. Returns (power map, interferer cell)."""
    x = cx(rng, NR, ND)                                             # noise, power 1
    if s['cnr_db'] > -50:                                           # zero-Doppler clutter ridge (3 bins wide)
        for dd in (-1, 0, 1):
            x[:, dd % ND] += 10 ** (s['cnr_db'] / 20) * cx(rng, NR)
    amp = lambda db: 10 ** (db / 20)
    x[s['r'], s['d']] += amp(s['snr_db']) * cx(rng, 1)[0]          # Rayleigh-fluctuating target
    ri, di = (s['r'] + s['dr']) % NR, (s['d'] + s['dd']) % ND
    if s['int_db'] > -50 and (s['dr'], s['dd']) != (0, 0):
        x[ri, di] += amp(s['int_db']) * cx(rng, 1)[0]              # second strong target / interferer
    return np.abs(x) ** 2, (ri, di)


def box(det: np.ndarray, r: int, d: int, k: int) -> bool:
    """Any detection within +-k of (r, d)."""
    rs, ds = np.arange(r - k, r + k + 1) % NR, np.arange(d - k, d + k + 1) % ND
    return bool(det[np.ix_(rs, ds)].any())


def map_stats(det: np.ndarray, s: Scenario, ri: int, di: int) -> tuple[bool, int]:
    """Single-map (hit, false alarms): hit = any detection within +-1 of the target;
    false alarms exclude 5x5 boxes around the target and the interferer."""
    hit = box(det, s['r'], s['d'], 1)
    keep = det.copy()
    for (r, d) in ((s['r'], s['d']), (ri, di)):                # exclude the two real objects
        keep[np.ix_(np.arange(r - 2, r + 3) % NR, np.arange(d - 2, d + 3) % ND)] = False
    return hit, int(keep.sum())


def evaluate(s: Scenario, detector: Detector, trials: int = 40, seed: int = 0) -> tuple[float, float]:
    """Monte-Carlo estimate of (Pd, false alarms per map) for one scenario."""
    rng, hits, fa = np.random.default_rng(seed), 0, 0.0
    for _ in range(trials):
        P, (ri, di) = make_map(s, rng)
        det = detector.detect(P)
        h, f = map_stats(det, s, ri, di)
        hits += h
        fa += f
    return hits / trials, fa / trials
