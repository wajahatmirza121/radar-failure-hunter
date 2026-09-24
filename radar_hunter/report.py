"""Output writers: atlas.json, report.md rendering, and the cluster explanation hook."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .simulator import G, T

WIN = 2 * (G + T) + 1                     # CFAR window side (for explanation text)


def write_atlas(payload: dict, path: str | Path = 'atlas.json') -> None:
    """Write the hunt payload to atlas.json."""
    with open(path, 'w') as f:
        json.dump(payload, f, indent=1, default=float)


def write_report(payload: dict, path: str | Path = 'report.md') -> str:
    """Render and write report.md; returns the text (also printed by the CLI)."""
    text = render_report(payload)
    Path(path).write_text(text, encoding='utf-8')
    return text


def render_report(payload: dict) -> str:
    """Render the markdown report: setup, validation curve, failure yields, clusters, seeds."""
    lines = ['# Radar Failure-Hunter Report', '',
             f"_Generated {payload['meta']['generated']} — deterministic given the seeds below._", '']
    lines += _setup(payload['meta'])
    lines += _validation(payload['detectors'], payload['meta']['pfa'])
    lines += _comparison(payload['detectors'])
    for det in payload['detectors']:
        lines += _detector_section(det, payload['meta']['failure_pd_threshold'])
    lines += _seeds(payload['meta'])
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------- explanation hook

def explain(cluster_summary: dict) -> str:
    """Natural-language explanation of one failure cluster: LLM if an API key is set,
    deterministic rule-based text otherwise. Never raises, never requires a key."""
    text = _llm_explain(_prompt(cluster_summary))
    return text if text else rule_explain(cluster_summary)


def rule_explain(cluster: dict) -> str:
    """Deterministic explanation built from the cluster's rule-based tag and centroid."""
    c = cluster['centroid']
    where = (f"target SNR ~{c['snr_db']:.0f} dB at Doppler bin ~{c['d']:.0f}, clutter ridge "
             f"~{c['cnr_db']:.0f} dB, interferer ~{c['int_db']:.0f} dB displaced by "
             f"(dr ~{c['dr']:+.0f}, dd ~{c['dd']:+.0f}) bins")
    why = {
        'target masking by interferer in training cells':
            f'the interferer lands inside the {WIN}x{WIN} training ring, so the adaptive noise estimate '
            'is inflated and the threshold rises above the fluctuating target return',
        'clutter-ridge leakage into training cells':
            f'the target sits within ~{G + T} Doppler bins of the zero-Doppler clutter ridge, so '
            'high-CNR ridge cells leak into the training window and inflate the noise estimate',
        'low SNR / other':
            'no single dominant mechanism: the target SNR alone leaves too little margin above the '
            'detection threshold at this Pfa once CFAR loss is paid',
    }[cluster['tag']]
    return (f"**Cluster {cluster['id']}** ({cluster['size']} scenarios, mean Pd "
            f"{cluster['mean_pd']:.2f}): typically {where}; {why}.")


def _prompt(cluster: dict) -> str:
    return ('You are a radar signal-processing engineer. In 3-4 sentences, explain why this cluster '
            'of CFAR detector failure scenarios occurs and what an engineer could do about it.\n'
            + json.dumps(cluster, indent=1))


def _llm_explain(prompt: str) -> str | None:
    """Call an OpenAI-compatible LLM if OPENAI_API_KEY is set; return None on any failure."""
    key = os.environ.get('OPENAI_API_KEY')
    if not key:
        return None
    try:
        from openai import OpenAI                        # optional dependency, never required
        client = OpenAI(api_key=key, timeout=20)
        model = os.environ.get('RADAR_HUNTER_LLM_MODEL', 'gpt-4o-mini')
        out = client.chat.completions.create(model=model, temperature=0.2, max_tokens=250,
                                             messages=[{'role': 'user', 'content': prompt}])
        return str(out.choices[0].message.content).strip() or None
    except Exception:                                    # an optional LLM must never break the report
        return None


# ---------------------------------------------------------------- report sections

def _setup(meta: dict) -> list[str]:
    dets = ', '.join(f"{d['name']} ({_det_params(d)})" for d in meta['detectors'])
    cem, rnd = meta['cem'], meta['random']
    return ['## Setup', '',
            f"- Range-Doppler map: {meta['map'][0]} range x {meta['map'][1]} Doppler bins; guard "
            f"{meta['guard_cells']} cells, {meta['training_cells_per_side']} training cells per side "
            f"({meta['training_ring']}-cell wrapped ring), design Pfa {meta['pfa']:g}.",
            f"- Detectors: {dets}. Both run the identical failure search: same scenario draws, same "
            'noise realizations, so their numbers are directly comparable.',
            f"- Scenario space (7-D unit cube): {meta['scenario_space']}.",
            f"- Search: cross-entropy method ({cem['iters']} iters x {cem['pop']} population, elite "
            f"{cem['elite']}, seed {cem['seed']}) vs random baseline (n={rnd['n']}, seed {rnd['seed']}); "
            f"{meta['trials_per_scenario']} Monte-Carlo trials per scenario; failure = Pd < "
            f"{meta['failure_pd_threshold']}; KMeans clustering k={meta['clusters']['k']} "
            f"(seed {meta['clusters']['seed']}) over standardized scenario parameters.", '']


def _det_params(d: dict) -> str:
    if 'k' in d:
        return f"k = {d['k']} of {d['training_cells']}, alpha = {d['alpha']:.3f}"
    return f"threshold factor {d['threshold_factor']:.4f} on {d['training_cells']} training cells"


def _validation(detectors: list[dict], pfa: float) -> list[str]:
    by_snr = [{r['snr_db']: r for r in d['curve']} for d in detectors]
    header = (['## Validation (clean scenario)', '',
               'Single-pulse Swerling-I theory: Pd = Pfa^(1/(1+SNR)), before CFAR loss.', '',
               '| SNR dB | theory Pd | '
               + ' | '.join(f"{d['name']} Pd (FA/map)" for d in detectors) + ' |',
               '|' + '---|' * (2 + len(detectors))])
    for snr in sorted(by_snr[0]):
        theory = pfa ** (1 / (1 + 10 ** (snr / 10)))
        cells = ' | '.join(f"{c[snr]['pd']:.2f} ({c[snr]['fa']:.2f})" for c in by_snr)
        header.append(f'| {snr} | {theory:.2f} | {cells} |')
    return header + ['']


def _comparison(detectors: list[dict]) -> list[str]:
    lines = ['## Failure search — detector comparison', '',
             '| detector | worst Pd | failure yield (adaptive) | failure yield (random) | '
             'FA/map in clutter | dominant failure modes |',
             '|---|---|---|---|---|---|']
    for d in detectors:
        modes = ', '.join(f'{t} ({c})' for t, c in sorted(d['failure_modes'].items(), key=lambda kv: -kv[1]))
        lines.append(f"| {d['name']} | {d['worst_pd']:.2f} | {d['yield_adaptive']:.0f}% | "
                     f"{d['yield_random']:.0f}% | {d['fa_map_in_clutter']:.0f} | {modes} |")
    return lines + ['']


def _detector_section(det: dict, failure_pd: float) -> list[str]:
    lines = [f"## {det['name']}", '',
             f"- Worst Pd found: {det['worst_pd']:.2f} (adaptive) vs {det['worst_pd_random']:.2f} (random).",
             f"- Failure yield (Pd < {failure_pd}): {det['yield_adaptive']:.0f}% adaptive vs "
             f"{det['yield_random']:.0f}% random.",
             f"- Mean false alarms/map in clutter scenarios: {det['fa_map_in_clutter']:.0f} "
             '(the same scenario draws for every detector).', '',
             '### Top failures', '',
             '| Pd | FA/map | SNR dB | CNR dB | Int dB | dr | dd | Doppler bin |',
             '|---|---|---|---|---|---|---|---|']
    lines += [f"| {a['pd']:.2f} | {a['fa']:.1f} | {a['snr_db']:.1f} | {a['cnr_db']:.0f} | "
              f"{a['int_db']:.0f} | {a['dr']} | {a['dd']} | {a['d']} |"
              for a in det['top_failures'][:10]]
    lines += ['']
    lines += _clusters(det, failure_pd)
    return lines


def _clusters(det: dict, failure_pd: float) -> list[str]:
    if not det['clusters']:
        return ['### Failure clusters', '',
                f'No scenarios with Pd < {failure_pd} were found for {det["name"]} — nothing to cluster.', '']
    lines = ['### Failure clusters (KMeans over failing scenarios)', '',
             '| cluster | size | tag | mean Pd | SNR dB | CNR dB | Int dB | dr | dd | Doppler bin |',
             '|---|---|---|---|---|---|---|---|---|---|']
    for c in det['clusters']:
        m = c['centroid']
        lines.append(f"| {c['id']} | {c['size']} | {c['tag']} | {c['mean_pd']:.2f} | "
                     f"{m['snr_db']:.1f} | {m['cnr_db']:.0f} | {m['int_db']:.0f} | "
                     f"{m['dr']:+.1f} | {m['dd']:+.1f} | {m['d']:.0f} |")
    lines += ['', 'Explanations (rule-based unless an LLM API key is set):', '']
    for c in det['clusters']:
        lines += [explain(c), '']
    return lines


def _seeds(meta: dict) -> list[str]:
    cem, rnd, clu = meta['cem'], meta['random'], meta['clusters']
    return ['## Reproducibility', '',
            f"- Cross-entropy search: seed {cem['seed']}; per-scenario Monte-Carlo seeds are derived "
            'deterministically from the iteration and population index (see `radar_hunter/search.py`).',
            f"- Random baseline: seed {rnd['seed']}; per-scenario Monte-Carlo seeds 5000+i.",
            f"- KMeans clustering: k={clu['k']}, seed {clu['seed']}, standardized scenario features.",
            '- Both detectors consume identical scenario draws and noise realizations, so their '
            'failure yields and FA costs are directly comparable.',
            '- Regenerate everything with `python hunter.py hunt`; physics checks with '
            '`python hunter.py validate`; tests with `python -m pytest`.']
