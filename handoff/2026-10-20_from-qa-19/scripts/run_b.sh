#!/bin/bash
cd /workspace/fansim/qa/run_r17 && export FANSIM_CACHE_DIR=/workspace/fansim/qa/r19_cache && mkdir -p $FANSIM_CACHE_DIR
D=/workspace/fansim/qa/r19/data
exec .venv/bin/python -u /workspace/fansim/qa/r19/scripts/b_bemt.py $D/tud_geom.txt $D/tud_forces.json /workspace/fansim/qa/r19_src/uiuc $D/sda1075_section.json $D/b_bemt.jsonl
