"""Radar Failure-Hunter MVP entry point — implementation lives in the radar_hunter package.
Usage:
  python hunter.py validate            # Pd vs SNR sanity check (clean scenario)
  python hunter.py hunt                # cross-entropy failure search + random baseline + report
  python hunter.py serve [--port 8000] # interactive web app: input scenarios, get live output
Outputs: atlas.json, report.md
"""
from radar_hunter.cli import main

if __name__ == '__main__':
    main()
