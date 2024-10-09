"""Test utilities."""

from __future__ import annotations

import pytest

from xknxproject import util
from xknxproject.models import ParameterInstanceRef


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
    assert util.get_dpt_type(dpt_string) == expected


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
    assert util.parse_dpt_types(dpt_string) == expected


@pytest.mark.parametrize(
    ("text", "parameter", "expected"),
    [
        ("{{0}}", ParameterInstanceRef("id", "test"), "test"),
        ("{{0:default}}", ParameterInstanceRef("id", None), "default"),
        ("{{0:default}}", ParameterInstanceRef("id", "test"), "test"),
        ("{{0}}", None, ""),
        ("{{0:default}}", None, "default"),
        ("Hello {{0}}", ParameterInstanceRef("id", "test"), "Hello test"),
        ("Hi {{0:def}} again", ParameterInstanceRef("id", None), "Hi def again"),
        ("Hi{{0:default}}again", ParameterInstanceRef("id", "test"), "Hitestagain"),
        ("{{1}}", ParameterInstanceRef("id", "test"), "{{1}}"),
        ("{{XY}}:{{0}}{{ZZ}}", ParameterInstanceRef("id", "test"), "{{XY}}:test{{ZZ}}"),
    ],
)
def test_text_parameter_template_replace(
    text: str, parameter: ParameterInstanceRef | None, expected: str
) -> None:
    """Test strip_module_instance."""
    assert util.text_parameter_template_replace(text, parameter) == expected


@pytest.mark.parametrize(
    ("text", "search_id", "expected"),
    [
        ("CH-4", "CH", "CH-4"),
        ("MD-1_M-1_MI-1_CH-4", "CH", "MD-1_CH-4"),
        ("MD-4_M-15_MI-1_SM-1_M-1_MI-1-1-2_SM-1_O-3-1_R-2", "O", "MD-4_SM-1_O-3-1_R-2"),
    ],
)
def test_strip_module_instance(text: str, search_id: str, expected: str) -> None:
    """Test strip_module_instance."""
    assert util.strip_module_instance(text, search_id) == expected


@pytest.mark.parametrize(
    ("ref", "next_id", "expected"),
    [
        ("M-0083_A-0098-12-489B_MD-1_M-1_MI-1_P-43_R-87", "P", "MD-1_M-1_MI-1"),
        ("MD-1_M-1_MI-1_CH-4", "CH", "MD-1_M-1_MI-1"),
        (
            "MD-4_M-15_MI-1_SM-1_M-1_MI-1-1-2_SM-1_O-3-1_R-2",
            "O",
            "MD-4_M-15_MI-1_SM-1_M-1_MI-1-1-2_SM-1",
        ),
        ("M-00FA_A-A228-0A-A6C3_O-2002002_R-200200202", "O", ""),
        ("MD-1_M-1_MI-1_CH-4", "CH", "MD-1_M-1_MI-1"),
        ("CH-SOM03", "CH", ""),
    ],
)
def test_get_module_instance_part(ref: str, next_id: str, expected: str) -> None:
    """Test strip_module_instance."""
    assert util.get_module_instance_part(ref, next_id) == expected


@pytest.mark.parametrize(
    ("instance_ref", "instance_next_id", "text_parameter_ref_id", "expected"),
    [
        (
            "MD-2_M-17_MI-1_O-3-0_R-159",
            "O",
            "M-0083_A-00B0-32-0DFC_MD-2_P-23_R-1",
            "M-0083_A-00B0-32-0DFC_MD-2_M-17_MI-1_P-23_R-1",
        ),
        (
            "MD-2_M-6_MI-1_CH-1",
            "CH",
            "M-0083_A-013A-32-DCC1_MD-2_P-1_R-1",
            "M-0083_A-013A-32-DCC1_MD-2_M-6_MI-1_P-1_R-1",
        ),
        (
            "O-595_R-688",
            "O",
            "M-0004_A-20D3-11-EC49-O000A_P-875_R-2697",  # no module - return same string,
            "M-0004_A-20D3-11-EC49-O000A_P-875_R-2697",
        ),
        (
            "MD-5_M-2_MI-1_O-3-0_R-1",
            "O",
            "M-007C_A-0004-72-F374_MD-5_UP-3_R-3",  # UnionParameter
            "M-007C_A-0004-72-F374_MD-5_M-2_MI-1_UP-3_R-3",
        ),
    ],
)
def test_text_parameter_insert_module_instance(
    instance_ref: str, instance_next_id: str, text_parameter_ref_id: str, expected: str
) -> None:
    """Test strip_module_instance."""
    assert (
        util.text_parameter_insert_module_instance(
            instance_ref, instance_next_id, text_parameter_ref_id
        )
        == expected
    )
