#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/../backend"
python -m app.seed
echo "CloudSense AI demo data seeded."
