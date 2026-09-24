"""Failure-mode tagging, yield metrics, and clustering of failing scenarios."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import numpy as np

# Pin thread pools before sklearn loads: the KMeans problems here are tiny, single-threaded
# OpenMP keeps clustering bit-reproducible, and LOKY_MAX_CPU_COUNT silences a joblib warning.
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('LOKY_MAX_CPU_COUNT', str(os.cpu_count() or 1))

from sklearn.cluster import KMeans          # noqa: E402  (import after the env pinning)
from sklearn.preprocessing import StandardScaler  # noqa: E402

from .search import NAMES
from .simulator import G, ND, T

FAILURE_PD = 0.3        # a scenario counts as a failure below this Pd
TAG_PD = 0.5            # scenarios above this are not tagged at all
FEATURES = [n for n in NAMES if n != 'r']     # range is homogeneous: r cannot influence detection


def tag_scenario(a: dict) -> str:
    """Rule-based failure tag for one scenario row."""
    ridge = min(min((a['d'] - k) % ND, (k - a['d']) % ND) for k in (-1, 0, 1))
    return ('target masking by interferer in training cells' if a['int_db'] > a['snr_db'] + 3
            else 'clutter-ridge leakage into training cells' if a['cnr_db'] > a['snr_db'] and ridge <= G + T
            else 'low SNR / other')


def failure_modes(atlas: list[dict], thr: float = TAG_PD) -> dict[str, int]:
    """Rule-based tagging (swap in an LLM later for natural-language explanations)."""
    tags: dict[str, int] = {}
    for a in atlas:
        if a['pd'] > thr: continue
        m = tag_scenario(a)
        tags[m] = tags.get(m, 0) + 1
    return tags


def failure_yield(pds: list[float] | np.ndarray, thr: float = FAILURE_PD) -> float:
    """Share of scenarios with Pd < thr, in percent."""
    return float(100 * np.mean(np.asarray(pds) < thr))


@dataclass
class ClusterSummary:
    """One KMeans cluster of failing scenarios, labelled with its dominant rule-based tag."""
    id: int
    size: int
    tag: str
    mean_pd: float
    centroid: dict[str, float]
    members: list[dict] = field(repr=False, default_factory=list)

    def to_dict(self) -> dict:
        return {'id': self.id, 'size': self.size, 'tag': self.tag,
                'mean_pd': self.mean_pd, 'centroid': self.centroid}


def cluster_failures(rows: list[dict], k: int = 5, seed: int = 0) -> list[ClusterSummary]:
    """KMeans over standardized scenario parameters of the rows with pd < FAILURE_PD,
    each cluster labelled with the majority rule-based tag of its members."""
    fails = [r for r in rows if r['pd'] < FAILURE_PD]
    if not fails:
        return []
    X = StandardScaler().fit_transform(np.array([[float(r[n]) for n in FEATURES] for r in fails]))
    k = max(1, min(k, len(fails)))
    labels = KMeans(n_clusters=k, n_init=10, random_state=seed).fit_predict(X)
    clusters = []
    for cid in range(k):
        members = [r for r, l in zip(fails, labels) if l == cid]
        tags = [tag_scenario(r) for r in members]
        clusters.append(ClusterSummary(
            id=cid, size=len(members), tag=max(set(tags), key=tags.count),
            mean_pd=float(np.mean([r['pd'] for r in members])),
            centroid={n: float(np.mean([r[n] for r in members])) for n in FEATURES},
            members=members))
    clusters.sort(key=lambda c: -c.size)
    for i, c in enumerate(clusters):                 # renumber: 0 = biggest cluster
        c.id = i
    return clusters
