"""R3.3: the README install section is enough to follow on Windows and Linux."""
from pathlib import Path

README = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")


def test_readme_has_an_install_section_for_windows_and_linux():
    lower = README.lower()
    assert "## install" in lower
    assert "windows" in lower
    assert "linux" in lower
    assert "uv" in lower
    assert "docker desktop" in lower
    assert "opencfd/openfoam-default:2406" in README
    assert "assess" in lower
    assert "wsl2" in lower
    assert "docker not running" in lower
    assert "--extra dev" in README
    assert "pytest_chunks" in README


def test_readme_clone_is_not_a_placeholder():
    assert "<this-repo>" not in README
    assert "<the GitHub URL>" not in README
    assert "https://github.com/klhutchins1/Fan-simulator" in README


def test_readme_cockpit_port_is_8080():
    assert "8080" in README
    assert "localhost:9001" not in README


def test_readme_assess_takes_thirty_to_forty_minutes():
    assert "30–40 min" in README
    assert "takes several minutes" not in README


def test_readme_linux_docker_has_an_engine_link():
    assert "docs.docker.com/engine/install" in README
