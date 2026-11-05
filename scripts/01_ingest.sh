#!/usr/bin/env bash
# Step 1 - Ingest the YB-42 recording into Mosaico.
#
# Runs the exact command from the challenge brief, after a dry run that checks
# every ROS topic resolves to a Mosaico ontology adapter (nothing is uploaded
# during the dry run).
#
# Usage:  bash scripts/01_ingest.sh            (from the repo root)
# Needs:  a running mosaicod on localhost:6726 and the Python env from
#         requirements.txt activated.
set -euo pipefail

cd "$(dirname "$0")/../Hackathon-challenge"

echo "==> Dry run: checking topic -> adapter mapping"
mosaicolabs.ros_injector spot_yb42.mcap --name spot_yb42 --dry-run

echo "==> Ingesting (exact command from the challenge)"
mosaicolabs.ros_injector spot_yb42.mcap --name spot_yb42 --metadata sequence_metadata.json
