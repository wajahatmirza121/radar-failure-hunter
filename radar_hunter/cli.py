"""Command-line interface: `validate` (theory check) and `hunt` (failure search + report)."""
from __future__ import annotations

import argparse
import shutil
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .analysis import FAILURE_PD, TAG_PD, cluster_failures, failure_modes, failure_yield, tag_scenario
from .detectors import CACFAR, OSCFAR
from .report import render_report, rule_explain, write_atlas, write_report
from .search import SCENARIO_SPACE, cem_search, random_search
from .simulator import G, ND, NR, PFA, T, clean_scenario, evaluate

VALIDATE_TRIALS = 400    # Monte-Carlo trials per SNR point in `validate`
CURVE_TRIALS = 100       # trials per SNR point for the validation curve embedded in the report
HUNT_TRIALS = 16         # trials per scenario during the failure search
CEM_ITERS, CEM_POP, CEM_ELITE, CEM_SEED = 8, 20, 5, 1
RANDOM_N, RANDOM_SEED = 100, 2
CLUSTERS_K, CLUSTER_SEED = 5, 0
TOP_N = 200               # worst scenarios kept per detector in atlas.json

FULL_BUDGET = {'iters': CEM_ITERS, 'pop': CEM_POP, 'elite': CEM_ELITE,
               'rnd_n': RANDOM_N, 'trials': HUNT_TRIALS, 'curve_trials': CURVE_TRIALS}
QUICK_BUDGET = {'iters': 6, 'pop': 12, 'elite': 4, 'rnd_n': 40, 'trials': 8, 'curve_trials': 40}


def validation_curve(detector, trials: int) -> list[dict]:
    """Clean-scenario (Pd, FA) vs SNR; one independent seed per SNR point
    (a shared seed would correlate the residuals from theory across points)."""
    curve = []
    for snr in range(8, 24, 2):
        pd, fa = evaluate(clean_scenario(snr), detector, trials=trials, seed=snr)
        curve.append({'snr_db': snr, 'pd': pd, 'fa': fa})
    return curve


def validate() -> None:
    print("Clean scenario, Rayleigh target, Pfa design 1e-4 (theory for Swerling I: "
          "Pd = Pfa^(1/(1+SNR)); e.g. ~0.43 at 10 dB, ~0.70 at 14 dB, before CFAR loss):")
    for det in (CACFAR(), OSCFAR()):
        print(f"  {det.name} {det.describe()}")
        for row in validation_curve(det, VALIDATE_TRIALS):
            print(f"    SNR {row['snr_db']:2d} dB   Pd={row['pd']:.2f}   false alarms/map={row['fa']:.2f}")


def hunt() -> None:
    """CLI entry: full-budget hunt with progress output and the rendered report."""
    payload = run_hunt(log=print)
    print('\n' + render_report(payload))


def run_hunt(quick: bool = False, budget: dict | None = None,
             log: Callable[[str], None] = lambda _m: None, out_dir: str | Path = '.') -> dict:
    """Run the failure search for every detector and write atlas.json + report.md into out_dir.

    `quick` selects a smaller (still deterministic) budget; `budget` overrides individual keys.
    Returns the payload (also what gets serialized)."""
    b = dict(QUICK_BUDGET if quick else FULL_BUDGET)
    if budget:
        b.update(budget)
    out = Path(out_dir)
    detectors = (CACFAR(), OSCFAR())
    entries = [_hunt_detector(det, b, log) for det in detectors]
    payload = {
        'meta': {
            'generated': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'budget': 'custom' if budget else ('quick' if quick else 'full'),
            'map': [NR, ND], 'guard_cells': G, 'training_cells_per_side': T,
            'training_ring': detectors[0].describe()['training_cells'], 'pfa': PFA,
            'scenario_space': SCENARIO_SPACE,
            'detectors': [d.describe() for d in detectors],
            'trials_per_scenario': b['trials'],
            'cem': {'iters': b['iters'], 'pop': b['pop'], 'elite': b['elite'], 'seed': CEM_SEED},
            'random': {'n': b['rnd_n'], 'seed': RANDOM_SEED},
            'failure_pd_threshold': FAILURE_PD,
            'clusters': {'k': CLUSTERS_K, 'seed': CLUSTER_SEED},
        },
        'detectors': entries,
    }
    write_atlas(payload, out / 'atlas.json')
    write_report(payload, out / 'report.md')
    _sync_dashboard(out)
    return payload


def _sync_dashboard(out_dir: Path) -> None:
    """Copy atlas.json into the dashboard's public/ dir so the dev server serves fresh data."""
    atlas = out_dir / 'atlas.json'
    public = out_dir / 'dashboard' / 'public'
    if atlas.exists() and public.is_dir():
        shutil.copy(atlas, public / 'atlas.json')


def _hunt_detector(det, b: dict, log: Callable[[str], None]) -> dict:
    """Run the same failure search (identical seeds/scenarios) for one detector."""
    log(f"=== {det.name} ===")
    sub = lambda m: log(f"  {m}")
    atlas, cem_pds = cem_search(det, b['iters'], b['pop'], b['elite'], seed=CEM_SEED,
                                trials=b['trials'], log=sub)
    base, rnd_pds = random_search(det, b['rnd_n'], seed=RANDOM_SEED, trials=b['trials'])
    rows = sorted(atlas + base, key=lambda r: r['pd'])
    clusters = cluster_failures(rows, k=CLUSTERS_K, seed=CLUSTER_SEED)
    cid = {id(m): c.id for c in clusters for m in c.members}
    top = [dict(r, tag=tag_scenario(r) if r['pd'] < TAG_PD else 'none',
                cluster=cid.get(id(r), -1)) for r in rows[:TOP_N]]
    in_clutter = [r['fa'] for r in base if r['cnr_db'] > -50]   # same scenarios for every detector
    return {
        'name': det.name, 'describe': det.describe(),
        'curve': validation_curve(det, b['curve_trials']),
        'worst_pd': rows[0]['pd'], 'worst_pd_random': base[0]['pd'],
        'yield_adaptive': failure_yield(cem_pds), 'yield_random': failure_yield(rnd_pds),
        'fa_map_in_clutter': float(np.mean(in_clutter)),
        'failure_modes': failure_modes(rows), 'top_failures': top,
        'clusters': [dict(c.to_dict(), explanation=rule_explain(c.to_dict())) for c in clusters],
    }


def main() -> None:
    ap = argparse.ArgumentParser(prog='hunter.py', description='radar-failure-hunter MVP')
    ap.add_argument('cmd', choices=['validate', 'hunt', 'serve'])
    ap.add_argument('--port', type=int, default=8000, help='port for `serve`')
    args = ap.parse_args()
    if args.cmd == 'serve':
        serve(args.port)
    else:
        {'validate': validate, 'hunt': hunt}[args.cmd]()


def serve(port: int = 8000) -> None:
    """Start the interactive web app (Scenario Lab API + dashboard)."""
    import uvicorn
    from .server import app
    print(f"radar-failure-hunter web app -> http://127.0.0.1:{port}  (Ctrl+C to stop)")
    uvicorn.run(app, host='127.0.0.1', port=port, log_level='warning')
