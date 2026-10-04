#!/usr/bin/env bash
set -euo pipefail
mkdir -p wheelhouse
python -m pip download -r requirements.txt -d wheelhouse \
  --only-binary=:all: --python-version 3.11 \
  --platform manylinux_2_28_x86_64 \
  --platform manylinux2014_x86_64
printf 'Wheelhouse created at %s/wheelhouse\n' "$PWD"
