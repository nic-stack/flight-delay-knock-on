#!/bin/bash
# Rebuild everything from the raw BTS files (run scripts/download_bts.sh first).
set -euo pipefail
cd "$(dirname "$0")"
PY=.venv/bin/python
$PY src/load.py data/raw data/interim/flights.parquet
$PY src/profile.py data/interim/flights.parquet > outputs/profile.txt
$PY src/trace.py data/interim/flights.parquet data/interim/traced.parquet > outputs/trace_checks.txt
$PY src/analysis.py > outputs/analysis_run.txt
$PY src/validate.py > outputs/validation_run.txt
$PY src/dashboard_data.py
$PY src/tableau_data.py
