"""Pytest suite: physics sanity, false-alarm calibration, interferer masking, reproducibility."""
import numpy as np
import pytest
from scipy.special import gammaln

from radar_hunter.analysis import tag_scenario
from radar_hunter.detectors import CACFAR, OSCFAR
from radar_hunter.search import cem_search
from radar_hunter.simulator import ND, NR, PFA, clean_scenario, evaluate

SNRS = (8, 12, 16, 20)


@pytest.mark.parametrize('detector', [CACFAR(), OSCFAR()], ids=['ca', 'os'])
def test_clean_pd_monotonic_in_snr(detector):
    """Clean-scenario Pd must be non-decreasing in SNR (and clearly rise overall)."""
    pds = [evaluate(clean_scenario(snr), detector, trials=120, seed=10)[0] for snr in SNRS]
    assert all(a <= b for a, b in zip(pds, pds[1:])), pds
    assert pds[0] < pds[-1]


@pytest.mark.parametrize('detector', [CACFAR(), OSCFAR()], ids=['ca', 'os'])
def test_false_alarms_stay_near_pfa_times_cells(detector):
    """In homogeneous noise, FA/map ~ Pfa * (cells - excluded ~25), i.e. ~0.82 here."""
    expected = PFA * (NR * ND - 25)
    _, fa = evaluate(clean_scenario(16), detector, trials=150, seed=7)
    assert abs(fa - expected) < 0.4


def test_strong_interferer_in_training_window_lowers_ca_pd():
    """A +20 dB interferer inside the CA training ring inflates the noise estimate."""
    clean = clean_scenario(15)
    masked = dict(clean, int_db=35, dr=6, dd=3)          # interferer inside the training ring
    pd_clean = evaluate(clean, CACFAR(), trials=60, seed=3)[0]
    pd_masked = evaluate(masked, CACFAR(), trials=60, seed=3)[0]
    assert pd_masked < pd_clean - 0.2


def test_os_cfar_robust_to_same_interferer():
    """OS-CFAR (k = 0.75N) shrugs off a single strong training-cell outlier."""
    masked = dict(clean_scenario(15), int_db=35, dr=6, dd=3)
    pd_ca = evaluate(masked, CACFAR(), trials=60, seed=3)[0]
    pd_os = evaluate(masked, OSCFAR(), trials=60, seed=3)[0]
    assert pd_os > pd_ca + 0.2


def test_same_seed_identical_results():
    """Identical seeds must reproduce identical (Pd, FA) and identical search atlases."""
    s = dict(clean_scenario(14), cnr_db=10, int_db=20, dr=4, dd=2)
    assert (evaluate(s, OSCFAR(), trials=30, seed=99)
            == evaluate(s, OSCFAR(), trials=30, seed=99))
    silent = lambda *_: None
    a1, _ = cem_search(CACFAR(), iters=2, pop=4, elite=2, seed=5, trials=5, log=silent)
    a2, _ = cem_search(CACFAR(), iters=2, pop=4, elite=2, seed=5, trials=5, log=silent)
    assert a1 == a2


def test_os_alpha_hits_design_pfa():
    """The OS threshold multiplier must satisfy the exact order-statistic Pfa formula."""
    det = OSCFAR()
    ln_pfa = (gammaln(det.n - det.k + 1 + det.alpha) + gammaln(det.n + 1)
              - gammaln(det.n - det.k + 1) - gammaln(det.n + 1 + det.alpha))
    assert abs(ln_pfa - np.log(PFA)) < 1e-6


def test_failure_tags():
    """Rule-based tagging picks the dominant mechanism for each constructed scenario."""
    base = dict(pd=0.1, snr_db=15.0, r=64, d=32, cnr_db=-60.0, int_db=-60.0, dr=0, dd=0)
    assert tag_scenario(dict(base, int_db=25.0, dr=6, dd=3)) == \
        'target masking by interferer in training cells'
    assert tag_scenario(dict(base, cnr_db=20.0, d=1)) == \
        'clutter-ridge leakage into training cells'
    assert tag_scenario(dict(base, snr_db=13.5)) == 'low SNR / other'
