"""R3.2: pyproject metadata and the fansim-cockpit console script."""
from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"


def _data() -> dict:
    with PYPROJECT.open("rb") as fh:
        return tomllib.load(fh)


def _project() -> dict:
    return _data()["project"]


def test_pyproject_license_authors_and_classifiers():
    project = _project()
    license_value = project["license"]
    if isinstance(license_value, str):
        assert license_value == "MIT"
    else:
        assert license_value.get("text") == "MIT" or license_value.get("file") == "LICENSE"
    authors = project["authors"]
    assert authors == [{"name": "Kimball"}]
    assert project["readme"] == "README.md"
    classifiers = project["classifiers"]
    assert "License :: OSI Approved :: MIT License" in classifiers
    assert "Programming Language :: Python :: 3.12" in classifiers


def test_pyproject_repository_names_the_github_remote():
    urls = _project()["urls"]
    repo = urls["Repository"]
    assert repo == "https://github.com/klhutchins1/Fan-simulator"
    assert urls["Homepage"] == "https://github.com/klhutchins1/Fan-simulator"
    assert urls["Issues"] == "https://github.com/klhutchins1/Fan-simulator/issues"


def test_pyproject_script_entry_wraps_cockpit():
    scripts = _project()["scripts"]
    assert scripts["fansim-cockpit"] == "fansim.cockpit_entry:main"
    entry = ROOT / "fansim" / "cockpit_entry.py"
    assert entry.is_file()
    assert "_bundled_cockpit.py" in entry.read_text(encoding="utf-8")
    force = _data()["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    assert force["scripts/cockpit.py"] == "fansim/_bundled_cockpit.py"


def test_entry_resolves_to_the_checkout_cockpit_script():
    from fansim.cockpit_entry import cockpit_script

    assert cockpit_script() == ROOT / "scripts" / "cockpit.py"


def test_fansim_cockpit_help_exits_zero():
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; sys.argv = ['fansim-cockpit', '--help']; "
                "from fansim.cockpit_entry import main; main()"
            ),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    help_text = proc.stdout + proc.stderr
    assert "usage:" in help_text.lower()
    assert "fansim-cockpit" in help_text
    assert "--port" in help_text
    assert "Uvicorn" not in help_text
