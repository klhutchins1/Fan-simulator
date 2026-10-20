#!/bin/bash
cd /workspace/fansim/qa/run_r17 && export FANSIM_CACHE_DIR=/workspace/fansim/qa/r17_cache
H=/workspace/fansim/repo-r15/handoff/2026-10-17_from-qa-16-hang/data; D=/workspace/fansim/qa/r17/data
exec .venv/bin/python -u /workspace/fansim/qa/r17/scripts/c300_built.py $H/p1_designed.jsonl $D/c300_analytic.jsonl $D/c300_built.jsonl 3
