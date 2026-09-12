# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Tests for the extended search DOFs (hub radius, thickness, camber position)."""

import optuna

from fansim.optimize.search_space import EXTENDED, blade_from_flat, suggest_params

optuna.logging.set_verbosity(optuna.logging.WARNING)
_EXT_KEYS = {"hub_radius", "thickness_root", "thickness_mid", "thickness_tip", "camber_pos"}


def _sample(with_extended):
    st = optuna.create_study()
    st.optimize(lambda t: (suggest_params(t, space="guided", with_extended=with_extended), 0.0)[1],
                n_trials=6)
    return st.trials


def test_extended_adds_and_varies_dofs():
    trials = _sample(with_extended=True)
    assert _EXT_KEYS.issubset(set(trials[0].params))
    hubs = {round(t.params["hub_radius"], 2) for t in trials}
    assert len(hubs) > 1                                   # genuinely searched
    lo, hi = EXTENDED["hub_radius"]
    assert all(lo <= t.params["hub_radius"] <= hi for t in trials)


def test_extended_off_is_unchanged():
    trials = _sample(with_extended=False)
    assert not (_EXT_KEYS & set(trials[0].params))         # no extra keys when off


def test_extended_round_trips_through_blade_from_flat():
    t = _sample(with_extended=True)[0]
    bp = blade_from_flat(t.params)
    assert bp.hub_radius == t.params["hub_radius"]
    assert bp.stations[0].thickness == t.params["thickness_root"]
    assert bp.stations[2].thickness == t.params["thickness_tip"]
    assert bp.stations[1].camber_pos == t.params["camber_pos"]
