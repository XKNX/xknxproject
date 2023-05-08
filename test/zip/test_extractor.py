"""Test reading KNX projects."""
from test import RESOURCES_PATH

from pytest import raises

from xknxproject.exceptions import InvalidPasswordException
from xknxproject.zip import extract
from xknxproject.zip.extractor import _generate_ets6_zip_password

xknx_test_project_protected_ets5 = RESOURCES_PATH / "xknx_test_project.knxproj"
xknx_test_project_ets5 = RESOURCES_PATH / "xknx_test_project_no_password.knxproj"
xknx_test_project_protected_ets6 = RESOURCES_PATH / "testprojekt-ets6.knxproj"


def test_extract_knx_project_ets5():
    """Test reading a KNX ETS5 project without an error."""
    with extract(xknx_test_project_ets5) as knx_project_contents:
        assert knx_project_contents.root.read("P-01D2/project.xml")

    with raises(ValueError):
        knx_project_contents.root.read("P-01D2/project.xml")


def test_extract_protected_knx_project_ets5():
    """Test reading a KNX ETS5 project without an error."""
    with extract(xknx_test_project_protected_ets5, "test") as knx_project_contents:
        assert knx_project_contents.root.read("P-0242.signature")
        with knx_project_contents.open_project_0() as proj_0:
            assert '<?xml version="1.0" encoding="utf-8"?>' in proj_0.readline().decode(
                "utf-8"
            )

    with raises(ValueError):
        knx_project_contents.root.read("P-0242.signature")


def test_ets6_password_generation():
    """Test generating ZIP password for ETS6 files."""
    assert (
        _generate_ets6_zip_password("a").decode("utf-8")
        == "+FAwP4iI7/Pu4WB3HdIHbbFmteLahPAVkjJShKeozAA="
    )
    assert (
        _generate_ets6_zip_password("test").decode("utf-8")
        == "2+IIP7ErCPPKxFjJXc59GFx2+w/1VTLHjJ2duc04CYQ="
    )
    assert (
        _generate_ets6_zip_password("Penn¥w1se 🤡").decode("utf-8")
        == "ZjlYlh+eTtoHvFadU7+EKvF4jOdEm7WkP49uanOMMk0="
    )


def test_extract_protected_knx_project_ets6():
    """Test reading a KNX ETS6 project without an error."""
    with extract(xknx_test_project_protected_ets6, "test") as knx_project_contents:
        assert knx_project_contents.root.read("P-04BF.signature")
        with knx_project_contents.open_project_0() as proj_0:
            assert '<?xml version="1.0" encoding="utf-8"?>' in proj_0.readline().decode(
                "utf-8"
            )

    with raises(ValueError):
        knx_project_contents.root.read("P-04BF.signature")


def test_wrong_password_ets5():
    """Test reading a KNX ETS5 project with wrong password."""
    with raises(InvalidPasswordException):
        with extract(xknx_test_project_protected_ets5, "wrong") as knx_project_contents:
            with knx_project_contents.open_project_0():
                pass


def test_wrong_password_ets6():
    """Test reading a KNX ETS6 project with wrong password."""
    with raises(InvalidPasswordException):
        with extract(xknx_test_project_protected_ets6, "wrong") as knx_project_contents:
            with knx_project_contents.open_project_0():
                pass


def test_required_password_ets6():
    """Test reading a KNX ETS6 project with wrong password."""
    with raises(InvalidPasswordException):
        with extract(xknx_test_project_protected_ets6, "") as knx_project_contents:
            with knx_project_contents.open_project_0():
                pass
