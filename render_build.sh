#!/usr/bin/env bash
# Render build step: install dependencies, then create a fresh demo database and per-install secret.
set -euo pipefail
pip install --upgrade pip
pip install -r requirements-render.txt
rm -f data/shg.db data/.shg_salt
python scripts/make_data.py
python scripts/run_acceptance.py
