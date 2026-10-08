"""Design-tab intake overbuild caption reflects the measured depth (2026-10-08)."""

from fansim.cockpit.placement import intake_overbuild_note


def test_off_shows_nothing():
    assert intake_overbuild_note(30.0, 25.0, 0.0) == ("", False)


def test_over_nominal_warns_and_says_how_to_fix():
    text, warn = intake_overbuild_note(31.2, 25.0, 10.0)
    assert warn
    assert "31.2 mm" in text and "+6.2 mm" in text and "won't drop into a stock frame" in text
    assert "turn off" in text and "Fit envelope" in text and "Optimize ignores" in text


def test_within_nominal_says_it_still_fits():
    text, warn = intake_overbuild_note(24.0, 25.0, 10.0)
    assert not warn and "still fits" in text


def test_unknown_depth():
    text, warn = intake_overbuild_note(None, 25.0, 10.0)
    assert warn and "unknown" in text
