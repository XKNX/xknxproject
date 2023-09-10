"""Test parsing ETS projects."""

import pytest

from xknxproject import XKNXProj

from . import RESOURCES_PATH
from .conftest import assert_stub


@pytest.mark.parametrize(
    ("file_stem", "password", "language"),
    [
        ("xknx_test_project", "test", None),
        ("test_project-ets4", "test", "de-DE"),
        (
            "module-definition-test",
            None,
            "De",
        ),  # resolves to "de-DE" in parser for knx_master.xml
        (
            "testprojekt-ets6-functions",
            None,
            "De",
        ),  # resolves to "de-DE" in parser for knx_master.xml
        ("ets6_two_level", None, "de-DE"),
        ("ets6_free", None, "de-DE"),
    ],
)
def test_parse_project(file_stem: str, password: str, language: str):
    """Test parsing of various ETS projects (see pytest parameters)."""
    knxproj = XKNXProj(
        RESOURCES_PATH / f"{file_stem}.knxproj", password, language=language
    )
    project = knxproj.parse()
    assert_stub(project, f"{file_stem}.json")
