import os

from xknxproject import KNXProj

from .conftest import assert_stub

xknx_test_project_protected_ets5 = os.path.join(
    os.path.dirname(__file__), "resources/xknx_test_project.knxproj"
)


async def test_parse_project_ets5():
    """Test parsing of ETS5 project."""
    knxproj = KNXProj(xknx_test_project_protected_ets5, "test")
    project = await knxproj.parse()
    assert_stub(project, "xknx_test_project.json")
