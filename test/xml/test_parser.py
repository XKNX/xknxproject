"""Test parser."""
from test import RESOURCES_PATH

import pytest

from xknxproject.xml.parser import XMLParser
from xknxproject.zip import extract

xknx_test_project_protected_ets5 = RESOURCES_PATH / "xknx_test_project.knxproj"
xknx_test_project_module_defs = RESOURCES_PATH / "module-definition-test.knxproj"
xknx_test_project_ets5 = RESOURCES_PATH / "xknx_test_project_no_password.knxproj"
xknx_test_project_protected_ets6 = RESOURCES_PATH / "testprojekt-ets6.knxproj"


def test_parse_project_ets6():
    """Test parsing of group addresses."""
    with extract(xknx_test_project_protected_ets6, "test") as knx_project_contents:
        parser = XMLParser(knx_project_contents)
        parser.parse()

    assert len(parser.group_addresses) == 3
    assert parser.group_addresses[0].address == "0/1/0"
    assert parser.group_addresses[1].address == "0/1/1"
    assert parser.group_addresses[2].address == "0/1/2"

    assert len(parser.areas) == 2
    assert len(parser.areas[1].lines) == 2
    assert len(parser.areas[1].lines[1].devices) == 3
    assert len(parser.areas[1].lines[1].devices[0].additional_addresses) == 4
    assert len(parser.areas[1].lines[1].devices[1].com_object_instance_refs) == 2
    assert parser.areas[1].lines[1].devices[0].manufacturer_name == "MDT technologies"


def test_parse_project_ets5():
    """Test parsing of ETS5 project."""
    with extract(xknx_test_project_protected_ets5, "test") as knx_project_contents:
        parser = XMLParser(knx_project_contents)
        parser.parse()

    assert len(parser.group_addresses) == 19
    parsed_gas = {ga.address for ga in parser.group_addresses}
    assert len(parsed_gas) == len(parser.group_addresses)
    assert parsed_gas == {
        "1/0/0",
        "1/0/1",
        "1/0/2",
        "1/0/3",
        "1/0/4",
        "1/0/5",
        "2/0/0",
        "2/0/1",
        "2/0/6",
        "2/1/1",
        "2/1/2",
        "2/1/10",
        "2/1/21",
        "2/1/22",
        "2/1/23",
        "7/0/0",
        "7/1/0",
        "7/1/1",
        "7/1/2",
    }

    assert len(parser.areas) == 2
    assert len(parser.areas[1].lines) == 2
    assert len(parser.areas[1].lines[1].devices) == 4
    assert len(parser.areas[1].lines[1].devices[0].additional_addresses) == 4
    assert len(parser.areas[1].lines[1].devices[1].com_object_instance_refs) == 7


@pytest.mark.parametrize(
    ("filename", "password"),
    [
        (RESOURCES_PATH / "test_project-ets4-no_password.knxproj", None),
        (RESOURCES_PATH / "test_project-ets4.knxproj", "test"),
    ],
)
def test_parse_project_ets4(filename, password):
    """Test parsing of ETS4 project."""
    with extract(filename, password) as knx_project_contents:
        parser = XMLParser(knx_project_contents)
        parser.parse()

    assert len(parser.group_addresses) == 3
    parsed_gas = {ga.address for ga in parser.group_addresses}
    assert len(parsed_gas) == len(parser.group_addresses)
    assert parsed_gas == {
        "0/0/1",
        "0/0/2",
        "0/0/3",
    }

    assert len(parser.areas) == 1
    assert len(parser.areas[0].lines) == 1
    assert len(parser.areas[0].lines[0].devices) == 2
    assert parser.areas[0].lines[0].devices[0].manufacturer_name == "MDT technologies"
    assert parser.areas[0].lines[0].devices[1].manufacturer_name == "ABB"

    assert len(parser.devices) == 2
    assert parser.devices[0].individual_address == "0.0.1"
    assert parser.devices[1].individual_address == "0.0.2"


def test_parse_project_with_module_defs():
    """Test parsing of ETS5 project with module definitions."""
    with extract(xknx_test_project_module_defs) as knx_project_contents:
        parser = XMLParser(knx_project_contents)
        parser.parse()

    assert len(parser.group_addresses) == 18
    assert parser.group_addresses[0].address == "0/0/1"
    assert parser.group_addresses[1].address == "0/0/2"
    assert parser.group_addresses[2].address == "0/0/3"

    assert len(parser.areas) == 2
    assert len(parser.areas[1].lines) == 2
    assert len(parser.areas[1].lines[1].devices) == 3

    assert len(parser.devices) == 3
