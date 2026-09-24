"""radar-failure-hunter: adversarial search for radar detector failure scenarios.

Modules:
  simulator  range-Doppler map simulation and Monte-Carlo (Pd, false-alarm) evaluation
  detectors  CFAR detectors behind one interface: detect(power map) -> boolean mask
  search     cross-entropy adversarial search + random baseline over scenario space
  analysis   rule-based failure tagging, metrics, clustering
  report     atlas.json / report.md writers and explanation hook
  cli        `validate` and `hunt` commands
"""
__version__ = "0.2.0"
