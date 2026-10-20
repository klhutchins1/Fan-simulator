#!/bin/bash
cd /workspace/fansim/qa/run_r17 && export FANSIM_CACHE_DIR=/workspace/fansim/qa/r17_cache
exec .venv/bin/python -u /workspace/fansim/qa/r17/scripts/c_r14.py /workspace/fansim/qa/r17/data/c_r14.json
