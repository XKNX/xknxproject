"""Test utilities."""
import pytest

from xknxproject.util import get_dpt_type, parse_dpt_types


@pytest.mark.parametrize(
    ("dpt_string", "expected"),
    [
        ("DPT-1", {"main": 1, "sub": None}),
        ("DPT-1 DPST-1-1", {"main": 1, "sub": None}),
        ("DPT-7 DPST-7-1", {"main": 7, "sub": None}),
        ("DPST-5-1", {"main": 5, "sub": 1}),
        ("DPT-1 DPT-5", {"main": 1, "sub": None}),
        ("DPT-14 DPST-14-1", {"main": 14, "sub": None}),
        ("DPST-6-10", {"main": 6, "sub": 10}),
        ("Wrong", None),
        ("DPT-Wrong", None),
        ("DPST-1-Wrong", None),
        ("DPST-5", None),
        ([], None),
        (None, None),
    ],
)
def test_get_dpt_type(dpt_string, expected):
    """Test parsing single DPT from ETS project."""
    assert get_dpt_type(dpt_string) == expected


@pytest.mark.parametrize(
    ("dpt_string", "expected"),
    [
        ("DPT-1", [{"main": 1, "sub": None}]),
        ("DPT-1 DPST-1-1", [{"main": 1, "sub": None}, {"main": 1, "sub": 1}]),
        ("DPT-7 DPST-7-1", [{"main": 7, "sub": None}, {"main": 7, "sub": 1}]),
        ("DPST-5-1", [{"main": 5, "sub": 1}]),
        ("DPT-1 DPT-5", [{"main": 1, "sub": None}, {"main": 5, "sub": None}]),
        ("DPT-14 DPST-14-1", [{"main": 14, "sub": None}, {"main": 14, "sub": 1}]),
        ("DPST-6-10", [{"main": 6, "sub": 10}]),
        ("Wrong", []),
        ("DPT-Wrong", []),
        ("DPST-1-Wrong", []),
        ("DPST-5", []),
        ([], []),
        (None, []),
    ],
)
def test_parse_dpt_types(dpt_string, expected):
    """Test parsing list of DPT from ETS project."""
    assert parse_dpt_types(dpt_string) == expected
