#!/bin/bash
# QA r14 A1, resumable (rerun after a suspend). setsid nohup bash chain_a1.sh > data/chain_a1.log 2>&1 &
cd /tmp
export PYTHONPATH=/workspace/fansim/qa/run_r14 PYTHONDONTWRITEBYTECODE=1 FANSIM_CACHE_DIR=/workspace/fansim/qa/r14_cache
PY=/workspace/fansim/repo-r9/.venv/bin/python
H=/workspace/fansim/repo-r15/handoff/2026-10-16_from-qa-14
$PY $H/scripts/a1_run.py $H/data/a1_results.jsonl
$PY $H/scripts/a1_analyse.py $H/data/a1_results.jsonl $H/data/a1_analysis.json
echo CHAIN_DONE
