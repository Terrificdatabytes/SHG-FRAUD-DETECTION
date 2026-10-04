#!/usr/bin/env bash
set -euo pipefail
# core/privacy.py creates a mode-0600 per-install secret if SHG_SALT is unset.
# An explicit insecure demo default is rejected.
streamlit run app.py \
  --server.headless true \
  --server.address 0.0.0.0 \
  --server.port "${PORT:-8501}" \
  --browser.gatherUsageStats false
