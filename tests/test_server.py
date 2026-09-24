"""Server payload builders: input normalization, simulate, evaluate, sweep, budget hunt."""
import json

from radar_hunter.cli import run_hunt
from radar_hunter.detectors import CACFAR
from radar_hunter.server import evaluate_payload, normalize_scenario, simulate_payload, sweep_payload
from radar_hunter.simulator import evaluate


def test_normalize_clamps_and_defaults():
    s = normalize_scenario({'snr_db': 999, 'r': -5, 'bogus': 'x'})
    assert s['snr_db'] == 40 and s['r'] == 8 and s['cnr_db'] == -60 and s['dr'] == 0
    ok = normalize_scenario({'snr_db': 15.5, 'int_db': 25, 'dr': 6, 'dd': 3})
    assert ok['snr_db'] == 15.5 and ok['int_db'] == 25 and ok['dr'] == 6


def test_simulate_payload_shapes_and_stats():
    s = normalize_scenario({'snr_db': 20, 'int_db': 30, 'dr': 6, 'dd': 3, 'seed': 7})
    p = simulate_payload(s, seed=7)
    assert len(p['map']) == 128 and len(p['map'][0]) == 64     # 128 range rows x 64 Doppler cols
    assert all(0 <= v <= 1 for row in p['map'] for v in row[:10])
    assert {d['name'] for d in p['detectors']} == {'CA-CFAR', 'OS-CFAR'}
    for d in p['detectors']:
        assert len(d['mask']) == 128 and len(d['mask'][0]) == 64
        assert isinstance(d['hit'], bool) and d['false_alarms'] >= 0
        assert d['detections'] == sum(sum(r) for r in d['mask'])
    assert p['interferer_present'] is True


def test_evaluate_payload_matches_direct_call():
    s = normalize_scenario({'snr_db': 16, 'cnr_db': 18})
    p = evaluate_payload(s, trials=20, seed=5)
    pd, fa = evaluate(s, CACFAR(), trials=20, seed=5)
    ca = next(r for r in p['results'] if r['name'] == 'CA-CFAR')
    assert ca['pd'] == pd and ca['fa'] == fa
    assert len(p['results']) == 2 and p['trials'] == 20


def test_sweep_payload_sweeps_snr_for_every_detector():
    s = normalize_scenario({'snr_db': 15, 'int_db': 25, 'dr': 6, 'dd': 3})
    p = sweep_payload(s, snrs=[10, 20], trials=6, seed=3)
    assert {ser['name'] for ser in p['series']} == {'CA-CFAR', 'OS-CFAR'}
    for ser in p['series']:
        assert [pt['snr_db'] for pt in ser['points']] == [10, 20]
        assert all(0.0 <= pt['pd'] <= 1.0 and pt['fa'] >= 0 for pt in ser['points'])
        # higher SNR must not reduce Pd by much (same scenario otherwise)
        assert ser['points'][1]['pd'] >= ser['points'][0]['pd'] - 0.1


def test_run_hunt_with_tiny_budget_writes_outputs(tmp_path):
    budget = {'iters': 2, 'pop': 4, 'elite': 2, 'rnd_n': 4, 'trials': 4, 'curve_trials': 4}
    lines = []
    payload = run_hunt(budget=budget, log=lines.append, out_dir=tmp_path)
    assert lines and any('CA-CFAR' in m for m in lines)
    atlas = json.loads((tmp_path / 'atlas.json').read_text())
    assert atlas['meta']['budget'] == 'custom'
    assert {d['name'] for d in atlas['detectors']} == {'CA-CFAR', 'OS-CFAR'}
    for d in atlas['detectors']:
        assert len(d['top_failures']) == 2 * 4 + 4      # tiny budget: every evaluated row kept
        for c in d['clusters']:                        # every cluster carries an explanation
            assert c['explanation']
    assert (tmp_path / 'report.md').exists()
    assert payload == atlas
