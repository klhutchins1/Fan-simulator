#!/bin/bash
# QA r12 A then B, resumable (rerun this script after a suspend). setsid nohup bash chain_ab.sh
cd /tmp
export PYTHONPATH=/workspace/fansim/qa/run_r12
PY=/workspace/fansim/repo-r9/.venv/bin/python
S=/workspace/fansim/repo-r13/handoff/2026-10-14_from-qa-12/scripts
D=/workspace/fansim/repo-r13/handoff/2026-10-14_from-qa-12/data
$PY $S/run_a.py $D/a_results.jsonl
$PY $S/run_b.py $D/b_results.jsonl
echo CHAIN_DONE
