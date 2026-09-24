# Radar Failure-Hunter Report

_Generated 2026-09-20T17:45:59+00:00 — deterministic given the seeds below._

## Setup

- Range-Doppler map: 128 range x 64 Doppler bins; guard 2 cells, 8 training cells per side (416-cell wrapped ring), design Pfa 0.0001.
- Detectors: CA-CFAR (threshold factor 0.0224 on 416 training cells), OS-CFAR (k = 312 of 416, alpha = 6.777). Both run the identical failure search: same scenario draws, same noise realizations, so their numbers are directly comparable.
- Scenario space (7-D unit cube): target SNR 13-25 dB; zero-Doppler clutter ridge 0-30 dB CNR, 3 bins wide, present in ~70% of draws; interferer 0-30 dB, present in ~80%, displaced by (dr, dd) within +-10 range and +-5 Doppler bins of the target.
- Search: cross-entropy method (8 iters x 20 population, elite 5, seed 1) vs random baseline (n=100, seed 2); 16 Monte-Carlo trials per scenario; failure = Pd < 0.3; KMeans clustering k=5 (seed 0) over standardized scenario parameters.

## Validation (clean scenario)

Single-pulse Swerling-I theory: Pd = Pfa^(1/(1+SNR)), before CFAR loss.

| SNR dB | theory Pd | CA-CFAR Pd (FA/map) | OS-CFAR Pd (FA/map) |
|---|---|---|---|
| 8 | 0.28 | 0.29 (0.70) | 0.27 (0.76) |
| 10 | 0.43 | 0.37 (0.82) | 0.39 (0.82) |
| 12 | 0.58 | 0.51 (0.81) | 0.51 (0.72) |
| 14 | 0.70 | 0.70 (1.02) | 0.70 (1.07) |
| 16 | 0.80 | 0.76 (0.84) | 0.75 (0.89) |
| 18 | 0.87 | 0.90 (0.83) | 0.90 (0.85) |
| 20 | 0.91 | 0.88 (0.62) | 0.88 (0.73) |
| 22 | 0.94 | 0.92 (1.05) | 0.92 (1.04) |

## Failure search — detector comparison

| detector | worst Pd | failure yield (adaptive) | failure yield (random) | FA/map in clutter | dominant failure modes |
|---|---|---|---|---|---|
| CA-CFAR | 0.00 | 42% | 11% | 85 | clutter-ridge leakage into training cells (53), target masking by interferer in training cells (31), low SNR / other (8) |
| OS-CFAR | 0.31 | 0% | 0% | 224 | low SNR / other (6), target masking by interferer in training cells (3), clutter-ridge leakage into training cells (2) |

## CA-CFAR

- Worst Pd found: 0.00 (adaptive) vs 0.00 (random).
- Failure yield (Pd < 0.3): 42% adaptive vs 11% random.
- Mean false alarms/map in clutter scenarios: 85 (the same scenario draws for every detector).

### Top failures

| Pd | FA/map | SNR dB | CNR dB | Int dB | dr | dd | Doppler bin |
|---|---|---|---|---|---|---|---|
| 0.00 | 121.8 | 14.7 | 20 | 13 | -7 | -1 | 7 |
| 0.00 | 125.8 | 16.8 | 22 | 8 | -6 | 0 | 6 |
| 0.00 | 129.5 | 16.0 | 25 | -60 | 6 | -1 | 9 |
| 0.00 | 127.6 | 17.8 | 23 | 22 | -5 | -2 | 7 |
| 0.00 | 119.3 | 15.0 | 22 | 12 | -3 | -2 | 3 |
| 0.00 | 127.2 | 17.9 | 24 | -60 | -8 | -1 | 8 |
| 0.00 | 131.8 | 15.6 | 26 | 0 | -3 | -1 | 11 |
| 0.00 | 119.0 | 16.2 | 21 | 16 | -8 | -4 | 5 |
| 0.00 | 131.6 | 19.5 | 28 | 6 | -5 | -3 | 8 |
| 0.00 | 124.3 | 15.7 | 22 | 30 | 6 | -1 | 8 |

### Failure clusters (KMeans over failing scenarios)

| cluster | size | tag | mean Pd | SNR dB | CNR dB | Int dB | dr | dd | Doppler bin |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 24 | clutter-ridge leakage into training cells | 0.00 | 15.9 | 26 | 12 | +0.5 | -2.5 | 7 |
| 1 | 23 | clutter-ridge leakage into training cells | 0.04 | 16.7 | 24 | 17 | -7.8 | -2.0 | 7 |
| 2 | 15 | clutter-ridge leakage into training cells | 0.08 | 17.0 | 22 | -60 | -5.5 | -1.3 | 7 |
| 3 | 10 | target masking by interferer in training cells | 0.01 | 17.6 | 27 | 23 | -4.9 | +2.3 | 7 |
| 4 | 7 | clutter-ridge leakage into training cells | 0.10 | 18.1 | 22 | -10 | -2.0 | -0.6 | 57 |

Explanations (rule-based unless an LLM API key is set):

**Cluster 0** (24 scenarios, mean Pd 0.00): typically target SNR ~16 dB at Doppler bin ~7, clutter ridge ~26 dB, interferer ~12 dB displaced by (dr ~+1, dd ~-2) bins; the target sits within ~10 Doppler bins of the zero-Doppler clutter ridge, so high-CNR ridge cells leak into the training window and inflate the noise estimate.

**Cluster 1** (23 scenarios, mean Pd 0.04): typically target SNR ~17 dB at Doppler bin ~7, clutter ridge ~24 dB, interferer ~17 dB displaced by (dr ~-8, dd ~-2) bins; the target sits within ~10 Doppler bins of the zero-Doppler clutter ridge, so high-CNR ridge cells leak into the training window and inflate the noise estimate.

**Cluster 2** (15 scenarios, mean Pd 0.08): typically target SNR ~17 dB at Doppler bin ~7, clutter ridge ~22 dB, interferer ~-60 dB displaced by (dr ~-5, dd ~-1) bins; the target sits within ~10 Doppler bins of the zero-Doppler clutter ridge, so high-CNR ridge cells leak into the training window and inflate the noise estimate.

**Cluster 3** (10 scenarios, mean Pd 0.01): typically target SNR ~18 dB at Doppler bin ~7, clutter ridge ~27 dB, interferer ~23 dB displaced by (dr ~-5, dd ~+2) bins; the interferer lands inside the 21x21 training ring, so the adaptive noise estimate is inflated and the threshold rises above the fluctuating target return.

**Cluster 4** (7 scenarios, mean Pd 0.10): typically target SNR ~18 dB at Doppler bin ~57, clutter ridge ~22 dB, interferer ~-10 dB displaced by (dr ~-2, dd ~-1) bins; the target sits within ~10 Doppler bins of the zero-Doppler clutter ridge, so high-CNR ridge cells leak into the training window and inflate the noise estimate.

## OS-CFAR

- Worst Pd found: 0.31 (adaptive) vs 0.56 (random).
- Failure yield (Pd < 0.3): 0% adaptive vs 0% random.
- Mean false alarms/map in clutter scenarios: 224 (the same scenario draws for every detector).

### Top failures

| Pd | FA/map | SNR dB | CNR dB | Int dB | dr | dd | Doppler bin |
|---|---|---|---|---|---|---|---|
| 0.31 | 326.2 | 13.4 | 19 | 8 | -7 | 1 | 51 |
| 0.38 | 357.9 | 13.5 | 23 | 10 | -10 | 2 | 42 |
| 0.44 | 9.1 | 14.5 | 2 | 7 | 3 | -1 | 15 |
| 0.44 | 15.8 | 13.0 | 4 | 26 | -9 | 0 | 31 |
| 0.44 | 247.7 | 13.0 | 15 | -60 | -7 | 3 | 24 |
| 0.44 | 315.1 | 13.0 | 18 | 24 | -8 | -1 | 54 |
| 0.44 | 373.4 | 13.1 | 26 | 1 | -10 | -2 | 59 |
| 0.50 | 305.2 | 13.0 | 17 | -60 | -8 | 2 | 56 |
| 0.50 | 53.3 | 14.0 | 7 | 24 | -6 | 3 | 48 |
| 0.50 | 18.9 | 14.0 | 4 | 9 | -10 | 1 | 32 |

### Failure clusters

No scenarios with Pd < 0.3 were found for OS-CFAR — nothing to cluster.

## Reproducibility

- Cross-entropy search: seed 1; per-scenario Monte-Carlo seeds are derived deterministically from the iteration and population index (see `radar_hunter/search.py`).
- Random baseline: seed 2; per-scenario Monte-Carlo seeds 5000+i.
- KMeans clustering: k=5, seed 0, standardized scenario features.
- Both detectors consume identical scenario draws and noise realizations, so their failure yields and FA costs are directly comparable.
- Regenerate everything with `python hunter.py hunt`; physics checks with `python hunter.py validate`; tests with `python -m pytest`.
