"""Report rendering and the explanation hook (fallback path — no API key required)."""
from radar_hunter.report import explain, render_report, rule_explain, write_atlas, write_report

CLUSTER = {'id': 0, 'size': 12, 'tag': 'target masking by interferer in training cells',
           'mean_pd': 0.05, 'centroid': {'snr_db': 15.0, 'd': 7.0, 'cnr_db': 20.0,
                                         'int_db': 25.0, 'dr': 5.0, 'dd': 2.0}}


def test_explain_falls_back_to_rules_without_api_key(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    text = explain(CLUSTER)
    assert text == rule_explain(CLUSTER)
    assert 'Cluster 0' in text and 'inflated' in text


def test_rule_explain_covers_every_tag():
    for tag in ('target masking by interferer in training cells',
                'clutter-ridge leakage into training cells', 'low SNR / other'):
        text = rule_explain(dict(CLUSTER, tag=tag))
        assert tag.split(' ')[0] in text.lower() or len(text) > 80


def _payload() -> dict:
    curve = [{'snr_db': s, 'pd': 0.1 * s - 0.5, 'fa': 0.82} for s in (8, 14, 20)]
    det = {'name': 'CA-CFAR', 'describe': {'name': 'CA-CFAR', 'training_cells': 416,
                                           'threshold_factor': 0.0224},
           'curve': curve, 'worst_pd': 0.0, 'worst_pd_random': 0.1,
           'yield_adaptive': 42.0, 'yield_random': 11.0, 'fa_map_in_clutter': 85.0,
           'failure_modes': {'target masking by interferer in training cells': 3},
           'top_failures': [{'pd': 0.0, 'fa': 121.8, 'snr_db': 14.7, 'r': 77, 'd': 7,
                              'cnr_db': 20.0, 'int_db': 13.0, 'dr': -7, 'dd': -1, 'tag': 'x',
                              'cluster': 0}],
           'clusters': [CLUSTER]}
    meta = {'generated': '2026-01-01T00:00:00+00:00', 'map': [128, 64], 'guard_cells': 2,
            'training_cells_per_side': 8, 'training_ring': 416, 'pfa': 1e-4,
            'scenario_space': 'SNR 13-25 dB, ...', 'trials_per_scenario': 16,
            'cem': {'iters': 8, 'pop': 20, 'elite': 5, 'seed': 1},
            'random': {'n': 100, 'seed': 2}, 'failure_pd_threshold': 0.3,
            'clusters': {'k': 5, 'seed': 0},
            'detectors': [{'name': 'CA-CFAR', 'training_cells': 416, 'threshold_factor': 0.0224}]}
    return {'meta': meta, 'detectors': [det]}


def test_render_report_contains_all_sections():
    text = render_report(_payload())
    for section in ('## Setup', '## Validation', '## Failure search', '## CA-CFAR',
                    '### Top failures', '### Failure clusters', '## Reproducibility'):
        assert section in text
    assert 'Swerling-I' in text and 'Cluster 0' in text


def test_write_outputs_roundtrip(tmp_path):
    payload = _payload()
    write_atlas(payload, tmp_path / 'atlas.json')
    write_report(payload, tmp_path / 'report.md')
    assert (tmp_path / 'report.md').read_text(encoding='utf-8').startswith('# Radar Failure-Hunter')
    import json
    assert json.loads((tmp_path / 'atlas.json').read_text())['meta']['pfa'] == 1e-4
