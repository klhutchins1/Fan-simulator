#!/bin/bash
cd /workspace/fansim/qa/run_r20 && export FANSIM_CACHE_DIR=/workspace/fansim/qa/r20_cache && mkdir -p $FANSIM_CACHE_DIR
D=/workspace/fansim/qa/r20/data
exec .venv/bin/python -u /workspace/fansim/qa/r20/scripts/a_r20.py /workspace/fansim/qa/r18/data/a_selection.json $D/r20-A-feature-designs.json $D/a_r20.jsonl ${W:-2}
