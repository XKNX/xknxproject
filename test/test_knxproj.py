import os

from xknxproject import KNXProj
from xknxproject.xml.parser import XMLParser
from xknxproject.zip import KNXProjExtractor

xknx_test_project_protected_ets5 = os.path.join(
    os.path.dirname(__file__), "resources/xknx_test_project.knxproj"
)


def test_parse_project_ets5():
    """Test parsing of ETS5 project."""
    knxproj = KNXProj(xknx_test_project_protected_ets5, "test")
    areas, group_addresses = knxproj.parse()

    assert len(group_addresses) == 7
    assert len(group_addresses) == 7
    assert group_addresses[0].address == "1/0/0"
    assert group_addresses[1].address == "1/0/1"
    assert group_addresses[2].address == "1/0/2"
    assert group_addresses[3].address == "1/0/3"
    assert group_addresses[4].address == "1/0/4"
    assert group_addresses[5].address == "1/0/5"
    assert group_addresses[6].address == "2/0/6"

    assert len(areas) == 2
    assert len(areas[1].lines) == 2
    assert len(areas[1].lines[1].devices) == 2
    assert len(areas[1].lines[1].devices[0].additional_addresses) == 4
    assert len(areas[1].lines[1].devices[1].com_object_instance_refs) == 7
