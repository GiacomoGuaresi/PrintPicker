import re
import tomllib
from pathlib import Path

import printpicker
from printpicker import about

ROOT = Path(__file__).resolve().parent.parent


def test_version_is_defined():
    assert re.fullmatch(r"\d+\.\d+\.\d+", printpicker.__version__)


def test_version_is_single_sourced():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert "version" not in project
    assert "version" in project["dynamic"]


def test_links_point_to_the_repository():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["urls"]["Repository"] == about.REPO_URL
    for url in (about.ISSUES_URL, about.RELEASES_URL, about.LICENSE_URL, about.GUIDE_URL):
        assert url.startswith(about.REPO_URL)
    assert about.LATEST_RELEASE_API.endswith(f"/repos/{about.GITHUB_REPO}/releases/latest")


def test_build_info_lists_versions(qapp):
    info = about.build_info()
    assert f"{about.APP_NAME} {printpicker.__version__}" in info
    assert "Python" in info and "Qt" in info and "ONNX Runtime" in info
