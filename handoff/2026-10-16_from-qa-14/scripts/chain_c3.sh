#!/bin/bash
# QA r14 C3 after A1 (waits for A1's CHAIN_DONE), resumable. setsid nohup bash chain_c3.sh > data/chain_c3.log 2>&1 &
H=/workspace/fansim/repo-r15/handoff/2026-10-16_from-qa-14
while ! grep -q CHAIN_DONE $H/data/chain_a1.log 2>/dev/null; do sleep 15; done
cd /tmp; export PYTHONPATH=/workspace/fansim/qa/run_r14 PYTHONDONTWRITEBYTECODE=1 FANSIM_CACHE_DIR=/workspace/fansim/qa/r14_cache
/workspace/fansim/repo-r9/.venv/bin/python $H/scripts/c3_build.py $H/data/c3_build.jsonl
echo CHAIN_DONE
