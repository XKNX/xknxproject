"""Test parsing ETS projects."""

from xknxproject import XKNXProj

from . import RESOURCES_PATH
from .conftest import assert_stub

import json

def test_parse_project_ets5():
    """Test parsing of ETS5 project."""
    knxproj = XKNXProj(RESOURCES_PATH / "xknx_test_project.knxproj", "test")
    project = knxproj.parse()
    assert_stub(project, "xknx_test_project.json")


def test_parse_project_ets4():
    """Test parsing of ETS4 project."""
    knxproj = XKNXProj(
        RESOURCES_PATH / "test_project-ets4.knxproj", "test", language="de-DE"
    )
    project = knxproj.parse()
    assert_stub(project, "test_project-ets4.json")


def test_parse_project_modules():
    """Test parsing of ETS5 project including 2 identical devices with module definitions."""
    knxproj = XKNXProj(
        RESOURCES_PATH / "module-definition-test.knxproj",
        language="De",  # resolves to "de-DE" in parser for knx_master.xml
    )
    project = knxproj.parse()
    assert_stub(project, "module-definition-test.json")

def test_parse_project_ets6_with_functions():
    """Test parsing of ETS6 project with room functions."""
    knxproj = XKNXProj(
        RESOURCES_PATH / "testprojekt-ets6-functions.knxproj",
        language="De",  # resolves to "de-DE" in parser for knx_master.xml
    )
    project = knxproj.parse()
    assert_stub(project, "testprojekt-ets6-functions.json")
