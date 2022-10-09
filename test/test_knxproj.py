from xknxproject import XKNXProj

from . import RESOURCES_PATH
from .conftest import assert_stub

xknx_test_project_protected_ets5 = RESOURCES_PATH / "xknx_test_project.knxproj"


def test_parse_project_ets5():
    """Test parsing of ETS5 project."""
    knxproj = XKNXProj(xknx_test_project_protected_ets5, "test")
    project = knxproj.parse()
    assert_stub(project, "xknx_test_project.json")
