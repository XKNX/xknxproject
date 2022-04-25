import os
from os.path import exists

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


def test_extract_protected_knx_project_ets5():
    """Test reading a KNX ETS5 project without an error."""
    reader = KNXProjExtractor(xknx_test_project_protected_ets5, "test")
    reader.extract()

    assert exists(reader.extraction_path + "P-0242/project.xml")

    reader.cleanup()
    assert not exists(reader.extraction_path + "P-0242/project.xml")


def test_extract_knx_project_ets5():
    """Test reading a KNX ETS5 project without an error."""
    reader = KNXProjExtractor(xknx_test_project_protected_ets5, "test")
    reader.extract()

    assert exists(reader.extraction_path + "P-0242/project.xml")

    reader.cleanup()
    assert not exists(reader.extraction_path + "P-0242/project.xml")


def test_ets6_password_generation():
    """Test generating ZIP password for ETS6 files."""
    reader = KNXProjExtractor(xknx_test_project_protected_ets6, "a")
    assert (
        "+FAwP4iI7/Pu4WB3HdIHbbFmteLahPAVkjJShKeozAA="
        == reader.generate_ets6_zip_password().decode("utf-8")
    )
    reader2 = KNXProjExtractor(xknx_test_project_protected_ets6, "test")
    assert (
        "2+IIP7ErCPPKxFjJXc59GFx2+w/1VTLHjJ2duc04CYQ="
        == reader2.generate_ets6_zip_password().decode("utf-8")
    )


def test_extract_protected_knx_project_ets6():
    """Test reading a KNX ETS6 project without an error."""
    reader = KNXProjExtractor(xknx_test_project_protected_ets6, "test")
    reader.extract()
    assert reader.get_project_id() == "P-04BF"
    assert exists(reader.extraction_path + reader.get_project_id() + "/project.xml")
    reader.cleanup()
    assert not exists(reader.extraction_path + "P-04BF/project.xml")
