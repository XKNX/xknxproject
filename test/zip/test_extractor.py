import os
from os.path import exists

from xknxproject.zip import KNXProjExtractor

xknx_test_project_protected_ets5 = os.path.join(
    os.path.dirname(__file__), "resources/xknx_test_project.knxproj"
)

xknx_test_project_protected_ets6 = os.path.join(
    os.path.dirname(__file__), "resources/testprojekt-ets6.knxproj"
)


def test_extract_knx_project_ets5():
    """Test reading a KNX project without an error."""
    reader = KNXProjExtractor(xknx_test_project_protected_ets5, "test")
    reader.extract()

    assert exists(reader.extraction_path + "P-0242/project.xml")

    reader.cleanup()
    assert not exists(reader.extraction_path + "P-0242/project.xml")
