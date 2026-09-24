"""Adversarial scenario search: cross-entropy method and random baseline."""
from __future__ import annotations

from typing import Callable

import numpy as np

from .detectors import Detector
from .simulator import ND, NR, Scenario, evaluate

NAMES = ['snr_db', 'r', 'd', 'cnr_db', 'int_db', 'dr', 'dd']
SCENARIO_SPACE = ('target SNR 13-25 dB; zero-Doppler clutter ridge 0-30 dB CNR, 3 bins wide, present in ~70% '
                  'of draws; interferer 0-30 dB, present in ~80%, displaced by (dr, dd) within '
                  '+-10 range and +-5 Doppler bins of the target')


def decode(u: np.ndarray) -> Scenario:
    """u in [0,1]^7 -> scenario dict (same parameterization as the original hunter.py)."""
    return Scenario(snr_db=13 + 12 * u[0], r=int(8 + u[1] * (NR - 16)), d=int(u[2] * (ND - 1)),
                    cnr_db=(u[3] - .3) / .7 * 30 if u[3] > .3 else -60,  # ~30%: no clutter, else 0..30 dB
                    int_db=(u[4] - .2) / .8 * 30 if u[4] > .2 else -60,  # ~20%: none, else 0..30 dB
                    dr=int(round((u[5] - .5) * 20)), dd=int(round((u[6] - .5) * 10)))


def cem_search(detector: Detector, iters: int = 12, pop: int = 40, elite: int = 8, seed: int = 1,
               trials: int = 40, log: Callable[[str], None] = print) -> tuple[list[dict], list[float]]:
    """Cross-entropy method: concentrate sampling where detection probability is lowest.

    Returns (all evaluated scenarios sorted by Pd, all evaluated Pds)."""
    rng, mu, sd, atlas, all_pd = np.random.default_rng(seed), np.full(7, .5), np.full(7, .3), [], []
    for it in range(iters):
        U = np.clip(rng.normal(mu, sd, (pop, 7)), 0, 1)
        res = sorted(((evaluate(decode(u), detector, trials=trials, seed=it * 1000 + i), u)
                      for i, u in enumerate(U)), key=lambda t: t[0][0])
        all_pd += [r[0][0] for r in res]
        E = np.array([u for _, u in res[:elite]]); mu, sd = E.mean(0), E.std(0) + .03
        atlas += [dict(pd=pd, fa=fa, **decode(u)) for (pd, fa), u in res]
        log(f"iter {it:2d}  worst Pd={res[0][0][0]:.2f}  elite mean Pd={np.mean([r[0][0] for r in res[:elite]]):.2f}")
    return sorted(atlas, key=lambda a: a['pd']), all_pd


def random_search(detector: Detector, n: int = 480, seed: int = 2,
                  trials: int = 40) -> tuple[list[dict], list[float]]:
    """Uniform random baseline over the same scenario space (same seeds for every detector)."""
    rng = np.random.default_rng(seed)
    out = sorted((dict(pd=(r := evaluate(decode(u), detector, trials=trials, seed=5000 + i))[0],
                       fa=r[1], **decode(u))
                  for i, u in enumerate(rng.random((n, 7)))), key=lambda a: a['pd'])
    return out, [a['pd'] for a in out]
