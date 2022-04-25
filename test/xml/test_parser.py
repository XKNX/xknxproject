import os
from os.path import exists

from xknxproject import KNXProjParser
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


def test_parse_group_addresses():
    """Test parsing of group adresses."""
    extractor = KNXProjExtractor(xknx_test_project_protected_ets6, "test")
    extractor.extract()
    parser = XMLParser(extractor)
    parser.parse()
    extractor.cleanup()

    assert len(parser.group_addresses) == 3
