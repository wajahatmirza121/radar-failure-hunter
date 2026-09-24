"""Interactive web app: Scenario Lab API (input -> output) + dashboard hosting.

Run with `python hunter.py serve` or `python -m radar_hunter.server`.

Endpoints:
  GET  /api/atlas        hunt results (atlas.json) for the report view
  POST /api/simulate     one range-Doppler map + per-detector detections for a scenario
  POST /api/evaluate     Monte-Carlo (Pd, FA/map) for the same scenario, every detector
  POST /api/sweep        Pd and FA/map vs target SNR for a user scenario
  POST /api/hunt/start   run the failure search in the background (quick or full budget)
  GET  /api/hunt/status  progress of the running/last background hunt
"""
from __future__ import annotations

import argparse
import json
import threading
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .detectors import CACFAR, OSCFAR, Detector
from .simulator import ND, NR, Scenario, evaluate, make_map, map_stats

ROOT = Path(__file__).resolve().parent.parent
DB_MIN, DB_MAX = -10.0, 45.0            # display range for log-power maps

app = FastAPI(title='radar-failure-hunter')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])


def detectors() -> tuple[Detector, ...]:
    return (CACFAR(), OSCFAR())


def normalize_scenario(body: dict) -> Scenario:
    """Clamp free-form user input into a valid scenario (-60 dB = source absent)."""
    def num(key: str, lo: float, hi: float, default: float) -> float:
        try:
            v = float(body.get(key, default))
        except (TypeError, ValueError):
            v = default
        return max(lo, min(hi, v))

    return Scenario(
        snr_db=num('snr_db', 0, 40, 15),
        r=int(num('r', 8, NR - 8, NR // 2)),
        d=int(num('d', 0, ND - 1, ND // 2)),
        cnr_db=num('cnr_db', -60, 30, -60),
        int_db=num('int_db', -60, 30, -60),
        dr=int(num('dr', -20, 20, 0)),
        dd=int(num('dd', -10, 10, 0)),
    )


def simulate_payload(s: Scenario, seed: int) -> dict:
    """One map, both detectors, same realization: the apples-to-apples single shot."""
    rng = np.random.default_rng(seed)
    P, (ri, di) = make_map(s, rng)
    db = np.clip(10 * np.log10(P + 1e-12), DB_MIN, DB_MAX)
    norm = np.round((db - DB_MIN) / (DB_MAX - DB_MIN), 3)
    out = {
        'scenario': dict(s), 'seed': seed,
        'target': [s['r'], s['d']], 'interferer': [int(ri), int(di)],
        'interferer_present': bool(s['int_db'] > -50 and (s['dr'], s['dd']) != (0, 0)),
        'map': norm.tolist(), 'detectors': [],
    }
    for det in detectors():
        mask = det.detect(P)
        hit, fa = map_stats(mask, s, ri, di)
        out['detectors'].append({'name': det.name, 'hit': bool(hit), 'false_alarms': fa,
                                 'detections': int(mask.sum()), 'mask': mask.astype(int).tolist()})
    return out


def evaluate_payload(s: Scenario, trials: int, seed: int) -> dict:
    """Monte-Carlo (Pd, FA/map) for every detector on identical noise realizations."""
    trials = int(max(1, min(trials, 400)))
    results = []
    for det in detectors():
        pd, fa = evaluate(s, det, trials=trials, seed=seed)
        results.append({'name': det.name, 'pd': pd, 'fa': fa})
    return {'scenario': dict(s), 'trials': trials, 'seed': seed, 'results': results}


@app.get('/api/atlas')
def get_atlas() -> dict:
    path = ROOT / 'atlas.json'
    if not path.exists():
        raise HTTPException(404, "atlas.json not found - run `python hunter.py hunt` first")
    return json.loads(path.read_text())


@app.post('/api/simulate')
def api_simulate(body: dict) -> dict:
    return simulate_payload(normalize_scenario(body), seed=int(body.get('seed', 0)))


@app.post('/api/evaluate')
def api_evaluate(body: dict) -> dict:
    return evaluate_payload(normalize_scenario(body), trials=int(body.get('trials', 60)),
                            seed=int(body.get('seed', 0)))


def sweep_payload(s: Scenario, snrs: list[int], trials: int, seed: int) -> dict:
    """Pd and FA/map versus target SNR for a user scenario (independent seed per point)."""
    trials = int(max(1, min(trials, 100)))
    snrs = sorted({int(v) for v in snrs})[:12]
    series = []
    for det in detectors():
        points = []
        for v in snrs:
            pd, fa = evaluate(dict(s, snr_db=v), det, trials=trials, seed=seed + v)
            points.append({'snr_db': v, 'pd': pd, 'fa': fa})
        series.append({'name': det.name, 'points': points})
    return {'scenario': dict(s), 'trials': trials, 'seed': seed, 'series': series}


@app.post('/api/sweep')
def api_sweep(body: dict) -> dict:
    s = normalize_scenario(body)
    lo, hi = int(body.get('snr_lo', 4)), int(body.get('snr_hi', 32))
    if lo > hi:
        lo, hi = hi, lo
    snrs = list(range(lo, hi + 1, max(1, int(body.get('snr_step', 4)))))
    return sweep_payload(s, snrs, trials=int(body.get('trials', 30)), seed=int(body.get('seed', 0)))


# ---- background hunt (run the failure search from the browser) -------------------------

_HUNT_LOCK = threading.Lock()
_HUNT = {'running': False, 'done': False, 'error': None, 'lines': [], 'quick': None,
         'finished': None}


def _hunt_log(msg: str) -> None:
    with _HUNT_LOCK:
        _HUNT['lines'].append(str(msg).strip())
        del _HUNT['lines'][:-200]                    # keep the tail only


def _hunt_worker(quick: bool) -> None:
    from .cli import run_hunt                        # import here to avoid a module cycle
    try:
        run_hunt(quick=quick, log=_hunt_log, out_dir=ROOT)
        with _HUNT_LOCK:
            _HUNT.update(running=False, done=True, error=None,
                         finished=datetime.now(timezone.utc).isoformat(timespec='seconds'))
    except Exception as exc:                          # a failed hunt must not kill the server
        with _HUNT_LOCK:
            _HUNT.update(running=False, done=False, error=f'{type(exc).__name__}: {exc}')


@app.post('/api/hunt/start')
def hunt_start(body: dict | None = None) -> dict:
    quick = bool((body or {}).get('quick', False))
    with _HUNT_LOCK:
        if _HUNT['running']:
            raise HTTPException(409, 'a hunt is already running')
        _HUNT.update(running=True, done=False, error=None, lines=[], quick=quick, finished=None)
    threading.Thread(target=_hunt_worker, args=(quick,), daemon=True).start()
    return {'started': True, 'quick': quick}


@app.get('/api/hunt/status')
def hunt_status() -> dict:
    with _HUNT_LOCK:
        return dict(_HUNT)


_DIST = ROOT / 'dashboard' / 'dist'
if _DIST.is_dir():                       # serve the built dashboard together with the API
    app.mount('/', StaticFiles(directory=_DIST, html=True), name='dashboard')


def main() -> None:
    parser = argparse.ArgumentParser(description='radar-failure-hunter web app')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == '__main__':
    main()
