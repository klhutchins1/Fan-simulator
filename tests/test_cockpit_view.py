"""Cockpit unit tests for pure helpers (figures, busy captions, library list).

Do not add source-grep UI tests that assert label strings exist in app.py / tab modules.
"""

from fansim.catalog import CatalogEntry, results_for_hub
from fansim.cockpit.figures import filter_fitting_designs, reject_hint, scatter_figure
from fansim.cockpit.busy import busy_caption, format_elapsed
from fansim.cockpit.library_view import library_list_items
from fansim.cockpit.data import Design
from fansim.cockpit.fan_helpers import append_user_designs, upsert_by_trial
from fansim.fan_spec import get_fan_spec


def test_reject_hint_explains_frame_gap():
    # the ring-to-frame gate rejects instantly with this reason; the user must get a hint, not silence
    hint = reject_hint("Noctua NF-A12x25: tip gap 0.10 mm < min 0.50 mm to 110 mm frame")
    assert hint
    assert "fit envelope" in hint.lower()
    assert "clearance" in hint.lower() or "gap" in hint.lower()


def test_reject_hint_frame_gap_not_confused_with_tip_dia():
    # a genuine tip-DIAMETER rejection keeps its own hint (must not be swallowed by the gap branch)
    hint = reject_hint("tip dia 112 mm > max 110 mm")
    assert "tip diameter" in hint.lower()


def test_reject_hint_explains_resonance():
    hint = reject_hint(
        "blade vibration risk (PETG): bend 384 Hz too close to BPF 333 Hz. Fix: drop Blades to <=9"
    )
    assert hint
    assert "fewer blades" in hint.lower()
    assert "cfd" in hint.lower()


def test_filter_fitting_designs_drops_oversize_tip():
    from fansim.cockpit.placement import fit_envelope

    spec = get_fan_spec("a12x25")
    # Start from a known-good envelope-fitted flat, then an intentionally oversize tip.
    fitted = fit_envelope({
        "n_blades": 7, "hub_radius": 21.5, "tip_radius": 56.5,
        "chord_root": 34, "chord_mid": 40, "chord_tip": 30,
        "stagger_root": 26, "stagger_mid": 26, "stagger_tip": 22,
        "max_camber": 0.05, "sweep_mid": 0.0, "sweep_tip": 0.0,
        "lean_mid": 0.0, "lean_tip": 0.0,
    }, spec).flat
    oversize = {**fitted, "tip_radius": 59.0}
    ok = Design(
        trial=1, params=fitted,
        objectives={"cfm_free": 50.0, "cfm_load": 40.0, "efficiency": 30.0},
        feasible=True, is_pareto=False, stl_path=None,
    )
    big = Design(
        trial=2, params=oversize,
        objectives={"cfm_free": 90.0, "cfm_load": 80.0, "efficiency": 35.0},
        feasible=True, is_pareto=False, stl_path=None,
    )
    kept = filter_fitting_designs([ok, big], spec)
    assert [d.trial for d in kept] == [1]


def test_results_for_hub_hides_foreign_envelope():
    a12 = CatalogEntry(design_id="ok", hub_models=["a12x25"], cfm_free=54.0, cfm_load=50.0)
    big = CatalogEntry(design_id="big", hub_models=[], cfm_free=92.0, cfm_load=87.0)
    hits = results_for_hub([a12, big], "a12x25")
    assert [h.design_id for h in hits] == ["ok"]
    spec = get_fan_spec("a12x25")
    lib = library_list_items([a12, big], spec)
    assert [it["value"] for it in lib if it.get("role") == "row"] == ["ok", "big"]


def test_scatter_colorbar_not_capped_at_22():
    d = Design(trial=1, params={}, objectives={"cfm_free": 50, "cfm_load": 48, "efficiency": 36},
               feasible=True, is_pareto=True, stl_path=None)
    fig = scatter_figure([d])
    cmax = fig.data[0].marker.cmax
    assert cmax is None or cmax >= 36 or cmax >= 45


def test_scatter_stock_ref_is_distinct_marker():
    d = Design(trial=1, params={}, objectives={"cfm_free": 50, "cfm_load": 48, "efficiency": 36},
               feasible=True, is_pareto=True, stl_path=None)
    fig = scatter_figure([d], stock_ref={
        "cfm_free": 60.1, "cfm_load": 55.0, "name": "Noctua NF-A12x25", "kind": "published",
    })
    assert len(fig.data) == 2
    stock = fig.data[-1]
    assert stock.marker.symbol == "x"
    assert list(stock.x) == [60.1]
    assert "stock" in (stock.name or "").lower() or "stock" in str(stock.customdata)


def test_format_elapsed_compact_clock():
    assert format_elapsed(0) == "0:00"
    assert format_elapsed(12) == "0:12"
    assert format_elapsed(3723) == "1:02:03"


def test_busy_caption_includes_note_and_stage():
    cap = busy_caption("Assess", 12, note="timeout 60 min", hint="meshing…")
    assert "Running Assess… 0:12" in cap
    assert "timeout 60 min" in cap
    assert "meshing…" in cap


def _stub_design(trial: int) -> Design:
    return Design(
        trial=trial,
        params={},
        objectives={"cfm_free": 10.0, "cfm_load": 8.0, "efficiency": 20.0},
        feasible=True,
        is_pareto=False,
        stl_path=None,
        extra={"source": "cockpit_opt"},
    )


def test_append_user_designs_updates_by_trial():
    """§9.11 — helper is the single locked mutation path for poll_merge / Assess."""
    import threading

    lock = threading.Lock()
    user: list[Design] = []
    by_trial: dict[int, Design] = {}
    d = _stub_design(9001)
    assert append_user_designs(lock, user, by_trial, d) == 1
    assert user == [d]
    assert by_trial[9001] is d


def test_append_user_designs_concurrent_no_lost_updates():
    """§9.11 — poll_merge executor + UI-style appends must not drop rows."""
    import threading

    lock = threading.Lock()
    user: list[Design] = []
    by_trial: dict[int, Design] = {}

    def worker(base: int) -> None:
        for i in range(40):
            append_user_designs(lock, user, by_trial, _stub_design(base + i))

    threads = [threading.Thread(target=worker, args=(b,)) for b in (0, 1000, 2000, 3000)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(user) == 160
    assert len(by_trial) == 160


def test_upsert_by_trial_replaces_under_lock():
    import threading

    lock = threading.Lock()
    by_trial: dict[int, Design] = {}
    a = _stub_design(42)
    b = _stub_design(42)
    b.objectives = {"cfm_free": 99.0, "cfm_load": 90.0, "efficiency": 40.0}
    upsert_by_trial(lock, by_trial, a)
    upsert_by_trial(lock, by_trial, b)
    assert by_trial[42] is b
    assert by_trial[42].objectives["cfm_free"] == 99.0


def test_load_study_designs_empty_run_is_ok(tmp_path):
    """§11.3 — blank runs/ folder must not SystemExit the cockpit shell."""
    from fansim.cockpit.app import load_study_designs

    assert load_study_designs(tmp_path) == []
    assert load_study_designs(tmp_path / "missing") == []
