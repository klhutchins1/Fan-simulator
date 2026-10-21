#!/bin/bash
cd /workspace/fansim/qa/run_r17 && export FANSIM_CACHE_DIR=/workspace/fansim/qa/r18_cache && mkdir -p $FANSIM_CACHE_DIR
D=/workspace/fansim/qa/r18/data
exec .venv/bin/python -u /workspace/fansim/qa/r18/scripts/a_built.py /workspace/fansim/repo-r15/handoff/2026-10-17_from-qa-16-hang/data/p1_designed.jsonl $D/a_selection.json $D/a_built.jsonl 3 ${SUPP:-}
