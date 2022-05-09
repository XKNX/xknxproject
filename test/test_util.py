"""Test utilities."""
import pytest

from xknxproject.util import parse_dpt_types


@pytest.mark.parametrize(
    "dpt_types,expected",
    [
        (["DPT-1"], {"main": 1}),
        (["DPT-1", "DPST-1-1"], {"main": 1, "sub": 1}),
        (["DPT-7", "DPST-7-1"], {"main": 7, "sub": 1}),
        (["DPST-5-1"], {"main": 5, "sub": 1}),
        (["DPT-1", "DPT-5"], {"main": 5}),
        (["DPT-14", "DPST-14-1"], {"main": 14, "sub": 1}),
        (["DPST-6-10"], {"main": 6, "sub": 10}),
        (["Wrong"], {}),
        ([], {}),
    ],
)
def test_parse_dpt_types(dpt_types: list[str], expected: dict[str, int]):
    """Test parsing of ETS5 project."""
    assert parse_dpt_types(dpt_types) == expected
