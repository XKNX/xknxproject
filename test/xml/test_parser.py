"""Test parser."""
from test import RESOURCES_PATH

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

    assert len(parser.group_addresses) == 13
    parsed_gas = {ga.address for ga in parser.group_addresses}
    assert len(parsed_gas) == len(parser.group_addresses)
    assert parsed_gas == {
        "1/0/0",
        "1/0/1",
        "1/0/2",
        "1/0/3",
        "1/0/4",
        "1/0/5",
        "2/0/6",
        "2/1/1",
        "2/1/2",
        "2/1/10",
        "2/1/21",
        "2/1/22",
        "2/1/23",
    }

    assert len(parser.areas) == 2
    assert len(parser.areas[1].lines) == 2
    assert len(parser.areas[1].lines[1].devices) == 3
    assert len(parser.areas[1].lines[1].devices[0].additional_addresses) == 4
    assert len(parser.areas[1].lines[1].devices[1].com_object_instance_refs) == 7


def test_parse_project_with_module_defs():
    """Test parsing of ETS5 project with module definitions."""
    with extract(xknx_test_project_module_defs) as knx_project_contents:
        parser = XMLParser(knx_project_contents)
        parser.parse()

    assert len(parser.group_addresses) == 7
    assert parser.group_addresses[0].address == "0/0/1"
    assert parser.group_addresses[1].address == "0/0/2"
    assert parser.group_addresses[2].address == "0/0/3"

    assert len(parser.areas) == 2
    assert len(parser.areas[1].lines) == 2
    assert len(parser.areas[1].lines[1].devices) == 2

    assert len(parser.devices) == 2
