"""``section_wrap`` travels with every saved design; old saves rebuild planar, exactly as scored (27.4)."""
from __future__ import annotations

import json
import sqlite3
from types import SimpleNamespace

from fansim.cockpit.stock_cache import stock_fingerprint
from fansim.optimize.search_space import blade_from_flat, blade_to_flat, stock_blade_flat
from fansim.optimize.trial_attrs import section_wrap_for_trial, trial_flat


def test_flat_round_trip_keeps_wrap():
    flat = stock_blade_flat()
    assert flat["section_wrap"] == "cylinder"
    legacy = {**flat, "section_wrap": "planar"}
    bp = blade_from_flat(legacy)
    assert bp.section_wrap == "planar" and blade_to_flat(bp)["section_wrap"] == "planar"


def test_unstamped_flat_reads_as_cylinder():
    flat = stock_blade_flat()
    flat.pop("section_wrap")
    assert blade_from_flat(flat).section_wrap == "cylinder"


def test_unstamped_trials_predate_the_switch():
    t = SimpleNamespace(params={"chord_tip": 30.0}, user_attrs={}, datetime_start=None)
    assert section_wrap_for_trial(t) == "planar"
    assert trial_flat(t)["section_wrap"] == "planar"
    t2 = SimpleNamespace(params={}, user_attrs={"section_wrap": "cylinder"}, datetime_start=None)
    assert trial_flat(t2)["section_wrap"] == "cylinder"


def test_suggest_params_stamps_trial():
    import optuna

    from fansim.optimize.search_space import suggest_params

    trial = optuna.create_study(directions=["maximize"] * 3).ask()
    bp = suggest_params(trial)
    assert trial.user_attrs["section_wrap"] == bp.section_wrap == "cylinder"


def test_stock_cache_key_changes_with_wrap():
    flat = stock_blade_flat()
    assert (stock_fingerprint({**flat, "section_wrap": "cylinder"})
            != stock_fingerprint({**flat, "section_wrap": "planar"}))


def test_migration_stamps_old_designs_planar(tmp_path):
    from scripts.migrate_section_wrap import main

    dj = tmp_path / "runs" / "r1" / "cockpit_assess" / "design_1" / "design.json"
    dj.parent.mkdir(parents=True)
    dj.write_text(json.dumps({"trial": 1, "params": {"chord_tip": 30.0}}))
    done = tmp_path / "runs" / "r1" / "cockpit_assess" / "design_2" / "design.json"
    done.parent.mkdir(parents=True)
    done.write_text(json.dumps({"trial": 2, "params": {"chord_tip": 30.0, "section_wrap": "cylinder"}}))
    db = tmp_path / "catalog.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE designs (design_id TEXT, run TEXT, trial TEXT, params TEXT)")
    con.execute("INSERT INTO designs VALUES ('a', 'r1', '1', ?)", (json.dumps({"chord_tip": 30.0}),))
    con.commit()
    con.close()
    assert main(["--runs", str(tmp_path / "runs"), "--catalog", str(db)]) == 0
    assert json.loads(dj.read_text())["params"]["section_wrap"] == "planar"
    assert json.loads(done.read_text())["params"]["section_wrap"] == "cylinder"
    con = sqlite3.connect(db)
    assert json.loads(con.execute("SELECT params FROM designs").fetchone()[0])["section_wrap"] == "planar"
    con.close()
