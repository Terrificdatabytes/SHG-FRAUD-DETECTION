#!/usr/bin/env bash
set -euo pipefail
if ! find wheelhouse -maxdepth 1 -type f | grep -q .; then
  echo "wheelhouse/ is empty. Run scripts/build_wheelhouse.sh on a networked matching x86_64 host, then copy it with the project." >&2
  exit 2
fi
python -m pip install --no-index --find-links=wheelhouse -r requirements.txt
python scripts/check_env.py
