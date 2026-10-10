"""The CFD dataset carries every value needed to reproduce a score by hand (QA-14)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def test_raw_columns_come_from_the_eval_result(tmp_path):
    import export_cfd_dataset as ex

    raw = {"shaft_power_rated_w": 0.7747, "derate": 0.9537, "actual_rpm": 1907.4, "p_free_pa": 1.586,
           "p_probe_pa": 7.276, "print_k_cfm": 0.9494, "print_k_eta": 0.9418, "print_k_fsi": 0.9993,
           "free": {"efficiency": 0.069}, "load": {"efficiency": 0.2012}}
    (tmp_path / "_eval_result.json").write_text(json.dumps({"raw": raw}), encoding="utf-8")
    got = ex._raw(tmp_path)
    assert got["derate"] == 0.9537 and got["eta_free_pct"] == 6.9 and got["eta_load_pct"] == 20.12
    assert set(ex.RAW_KEYS) <= set(got) and set(got) <= set(ex.COLUMNS)
    assert ex._raw(tmp_path / "missing") == {}
