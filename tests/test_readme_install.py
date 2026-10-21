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
