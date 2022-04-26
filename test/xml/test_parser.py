import os

from xknxproject.xml.parser import XMLParser
from xknxproject.zip import KNXProjExtractor

xknx_test_project_protected_ets5 = os.path.join(
    os.path.dirname(__file__), "../resources/xknx_test_project.knxproj"
)

xknx_test_project_ets5 = os.path.join(
    os.path.dirname(__file__), "../resources/xknx_test_project_no_password.knxproj"
)

xknx_test_project_protected_ets6 = os.path.join(
    os.path.dirname(__file__), "../resources/testprojekt-ets6.knxproj"
)


def test_parse_project_ets6():
    """Test parsing of group adresses."""
    extractor = KNXProjExtractor(xknx_test_project_protected_ets6, "test")
    extractor.extract()
    parser = XMLParser(extractor)
    parser.parse()
    extractor.cleanup()

    assert len(parser.group_addresses) == 3
    assert parser.group_addresses[0].address == "0/1/0"
    assert parser.group_addresses[1].address == "0/1/1"
    assert parser.group_addresses[2].address == "0/1/2"

    assert len(parser.areas) == 2
    assert len(parser.areas[1].lines) == 2
    assert len(parser.areas[1].lines[1].devices) == 3
    assert len(parser.areas[1].lines[1].devices[0].additional_addresses) == 4
    assert len(parser.areas[1].lines[1].devices[1].com_object_instance_refs) == 8


def test_parse_project_ets5():
    """Test parsing of ETS5 project."""
    extractor = KNXProjExtractor(xknx_test_project_protected_ets5, "test")
    extractor.extract()
    parser = XMLParser(extractor)
    parser.parse()
    extractor.cleanup()

    assert len(parser.group_addresses) == 7
    assert len(parser.group_addresses) == 7
    assert parser.group_addresses[0].address == "1/0/0"
    assert parser.group_addresses[1].address == "1/0/1"
    assert parser.group_addresses[2].address == "1/0/2"
    assert parser.group_addresses[3].address == "1/0/3"
    assert parser.group_addresses[4].address == "1/0/4"
    assert parser.group_addresses[5].address == "1/0/5"
    assert parser.group_addresses[6].address == "2/0/6"

    assert len(parser.areas) == 2
    assert len(parser.areas[1].lines) == 2
    assert len(parser.areas[1].lines[1].devices) == 2
    assert len(parser.areas[1].lines[1].devices[0].additional_addresses) == 4
    assert len(parser.areas[1].lines[1].devices[1].com_object_instance_refs) == 7
