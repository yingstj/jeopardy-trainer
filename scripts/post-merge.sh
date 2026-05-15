#!/usr/bin/env bash
# Runs after a task is merged into main. Keep it fast and idempotent.
set -euo pipefail

if [ -f requirements.txt ]; then
  pip install --quiet --disable-pip-version-check -r requirements.txt
fi

echo "post-merge: OK"
