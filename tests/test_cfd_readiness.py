"""R3.4: one plain-language CFD readiness line. Docker is mocked; nothing here calls it."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fansim.cfd.runner import DEFAULT_IMAGE, cfd_readiness, publish_cfd_readiness

ROOT = Path(__file__).resolve().parents[1]
_IMAGE = "opencfd/openfoam-default:2406"


def _proc(code: int = 0, stdout: str = "", stderr: str = ""):
    return SimpleNamespace(returncode=code, stdout=stdout, stderr=stderr)


def test_project_image_is_the_openfoam_tag_already_in_use():
    assert DEFAULT_IMAGE == _IMAGE


def test_cfd_ready_when_docker_is_up_and_the_image_is_present():
    def run(args, **kwargs):
        if list(args[:2]) == ["docker", "info"]:
            return _proc(0, "Server Version: 27\n")
        assert list(args) == ["docker", "images", "-q", _IMAGE]
        return _proc(0, "sha256:abc\n")

    got = cfd_readiness(run=run)
    assert got.state == "ready"
    assert got.line.startswith("CFD ready")
    assert "\n" not in got.line
    low = got.line.lower()
    assert "not running" not in low
    assert "missing" not in low
    assert "not installed" not in low


def test_docker_not_running_when_the_daemon_refuses_info():
    def run(args, **kwargs):
        assert list(args[:2]) == ["docker", "info"]
        return _proc(1, stderr="Cannot connect to the Docker daemon")

    got = cfd_readiness(run=run)
    assert got.state == "docker_not_running"
    assert "Docker not running" in got.line
    assert "Start Docker Desktop" in got.line
    assert "docker pull" not in got.line
    assert "\n" not in got.line


def test_image_missing_when_docker_is_up_but_the_tag_is_absent():
    def run(args, **kwargs):
        if list(args[:2]) == ["docker", "info"]:
            return _proc(0, "ok\n")
        assert list(args) == ["docker", "images", "-q", _IMAGE]
        return _proc(0, "\n")

    got = cfd_readiness(run=run)
    assert got.state == "image_missing"
    assert "image missing" in got.line
    assert "docker pull" in got.line
    assert _IMAGE in got.line
    assert "Start Docker Desktop" not in got.line
    assert "Docker not installed" not in got.line
    assert "\n" not in got.line


def test_docker_not_installed_when_the_cli_is_missing():
    def run(args, **kwargs):
        raise FileNotFoundError(2, "The system cannot find the file", "docker")

    got = cfd_readiness(run=run)
    assert got.state == "docker_not_installed"
    assert "Docker not installed" in got.line
    assert "Install Docker" in got.line
    assert "\n" not in got.line
    assert "FileNotFoundError" not in got.line
    assert "daemon" not in got.line.lower()


def test_readiness_lines_stay_in_plain_words():
    """A first-time hobbyist can act on the line. No solver jargon."""
    samples = [
        cfd_readiness(run=_scripted([(0, "ok"), (0, "abc")])),
        cfd_readiness(run=lambda args, **k: _proc(1, stderr="not running")),
        cfd_readiness(run=_scripted([(0, "ok"), (0, "")])),
        cfd_readiness(run=_missing_cli),
    ]
    assert [s.state for s in samples] == [
        "ready",
        "docker_not_running",
        "image_missing",
        "docker_not_installed",
    ]
    for got in samples:
        assert "MRF" not in got.line
        assert "OpenFOAM" not in got.line or got.state == "image_missing"
        assert "subprocess" not in got.line.lower()


def test_publish_writes_one_line_onto_cockpit_state(monkeypatch):
    from fansim.cfd import runner

    monkeypatch.setattr(
        runner,
        "cfd_readiness",
        lambda *a, **k: SimpleNamespace(
            state="docker_not_installed",
            line="Docker not installed. Install Docker Desktop.",
        ),
    )
    state = SimpleNamespace()
    publish_cfd_readiness(state)
    assert state.cfd_readiness == "Docker not installed. Install Docker Desktop."


def test_fan_tab_shows_the_line_where_assess_is():
    """Simple mode sees the line next to Assess; it is not an Expert-only blurb."""
    ui = (ROOT / "fansim" / "cockpit" / "fan_tab_ui.py").read_text(encoding="utf-8")
    tab = (ROOT / "fansim" / "cockpit" / "fan_tab.py").read_text(encoding="utf-8")
    i = ui.find("{{ cfd_readiness }}")
    assert i >= 0
    widget = ui[max(0, i - 180) : i + 320]
    assert "ui_mode === 'expert'" not in widget
    assess = ui.find('"Assess (~15–30 min)"')
    assert 0 < assess - i < 2500
    assert "publish_cfd_readiness" in tab


def _scripted(steps: list[tuple[int, str]]):
    pending = list(steps)

    def run(args, **kwargs):
        code, stdout = pending.pop(0)
        return _proc(code, stdout)

    return run


def _missing_cli(args, **kwargs):
    raise FileNotFoundError(2, "docker", "docker")
