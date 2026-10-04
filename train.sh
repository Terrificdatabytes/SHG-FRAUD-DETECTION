#!/usr/bin/env bash
set -euo pipefail
python scripts/make_data.py
python -m core.train
python -m core.evaluate
