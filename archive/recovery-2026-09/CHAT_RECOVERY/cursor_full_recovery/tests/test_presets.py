"""Application load presets (roadmap §3.1) — what the optimizer treats as 'the load'."""

from __future__ import annotations

import pytest

from fansim.optimize.presets import PRESETS, resolve_load


def test_presets_cover_the_three_applications():
    assert set(PRESETS) == {"case", "heatsink", "radiator"}
    assert PRESETS["case"].load_pa == 8.0
    assert PRESETS["heatsink"].load_pa == 20.0
    assert PRESETS["radiator"].load_pa == 35.0
    assert PRESETS["case"].load_pa < PRESETS["heatsink"].load_pa < PRESETS["radiator"].load_pa


def test_resolve_load_defaults_to_mild_free_air():
    pa, name = resolve_load()
    assert pa == 1.0
    assert name is None


def test_resolve_load_uses_preset_when_load_pa_omitted():
    pa, name = resolve_load(preset="heatsink")
    assert pa == 20.0
    assert name == "heatsink"


def test_resolve_load_explicit_load_pa_overrides_preset():
    pa, name = resolve_load(preset="radiator", load_pa=40.0)
    assert pa == 40.0
    assert name == "radiator"


def test_resolve_load_rejects_unknown_preset():
    with pytest.raises(ValueError, match="unknown preset"):
        resolve_load(preset="fridge")
