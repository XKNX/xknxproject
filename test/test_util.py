"""Test utilities."""

from __future__ import annotations

from typing import Any

import pytest

from xknxproject import util
from xknxproject.models import DPTType, ParameterInstanceRef


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
def test_get_dpt_type(
    dpt_string: str | list[Any] | None, expected: dict[str, int | None] | None
) -> None:
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
def test_parse_dpt_types(
    dpt_string: str | list[Any] | None, expected: list[DPTType]
) -> None:
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


@pytest.mark.parametrize(
    ("semantics", "expected"),
    [
        ("knx:fb.417", ["417"]),
        (None, None),
        ("Wrong", None),
    ],
)
def test_semantics_functional_blocks(
    semantics: str | None, expected: list[str] | None
) -> None:
    """Test semantics functional blocks."""
    assert util.parse_semantics_functional_blocks(semantics) == expected


@pytest.mark.parametrize(
    ("semantics", "expected"),
    [
        ("knx:dpa.417.73", ["417.73"]),
        ("knx:dpa.800.51 knx:dpa.800.81", ["800.51", "800.81"]),
        (None, None),
        ("Wrong", None),
    ],
)
def test_semantics_dpas(semantics: str | None, expected: list[str] | None) -> None:
    """Test semantics dpas."""
    assert util.parse_semantics_dpas(semantics) == expected


@pytest.mark.parametrize(
    ("application_id", "expected"),
    [
        ("M-0008_A-20E0-21-9997-O000A", "M-000A"),
        ("M-0008_A-20E0-21-9997-o00ef", "M-00EF"),
        ("M-0008_A-20E0-21-9997-OXYZW", None),
        ("M-0083_A-013A-32-DCC1", None),
        ("not-an-application-id", None),
    ],
)
def test_application_id_original_manufacturer(
    application_id: str, expected: str | None
) -> None:
    """Test the original manufacturer of the application id suffix."""
    assert util.application_id_original_manufacturer(application_id) == expected


@pytest.mark.parametrize(
    ("application_id", "original_manufacturer_id", "expected"),
    [
        ("M-0083_A-013A-32-DCC1", None, "M-0083_A-013A-32-DCC1"),
        ("M-0008_A-20E0-21-9997-O000A", None, "M-000A_A-20E0-21-9997"),
        ("M-0008_A-20E0-21-9997-o000a", None, "M-000A_A-20E0-21-9997"),
        ("M-0008_A-20E0-21-9997-O000A", "M-0002", "M-0002_A-20E0-21-9997"),
        ("M-0008_A-20E0-21-9997", "m-000a", "M-000A_A-20E0-21-9997"),
        # a suffix that is not "-O" with 4 hex digits stays part of the program
        ("M-0008_A-20E0-21-9997-OXYZW", None, "M-0008_A-20E0-21-9997-OXYZW"),
        ("not-an-application-id", None, "not-an-application-id"),
    ],
)
def test_canonical_application_id(
    application_id: str, original_manufacturer_id: str | None, expected: str
) -> None:
    """Test the application id independent of rebranding."""
    assert (
        util.canonical_application_id(application_id, original_manufacturer_id)
        == expected
    )


@pytest.mark.parametrize(
    ("instance_id", "search_id", "expected"),
    [
        ("O-334_R-21", "O", "O-334_R-21"),
        ("1.1.1/O-334_R-21", "O", "O-334_R-21"),
        ("1.1.1/MD-2_M-1_MI-1_O-2-1_R-1", "O", "MD-2_O-2-1_R-1"),
        (
            "MD-4_M-15_MI-1_SM-1_M-1_MI-1-1-2_SM-1_O-3-1_R-2",
            "O",
            "MD-4_SM-1_O-3-1_R-2",
        ),
        ("M-0083_A-013A-32-DCC1_O-1_R-1", "O", "O-1_R-1"),
        ("MD-2_M-1_MI-1_CH-1", "CH", "MD-2_CH-1"),
        ("CH-9", "CH", "CH-9"),
    ],
)
def test_instance_definition_id(
    instance_id: str, search_id: str, expected: str
) -> None:
    """Test instance ids of a project resolve to definition ids of the program."""
    assert (
        util.instance_definition_id(instance_id, "M-0083_A-013A-32-DCC1", search_id)
        == expected
    )


def _channel(identifier: str, module: str | None) -> dict[str, Any]:
    return {
        "identifier": identifier,
        "name": identifier,
        "text": None,
        "number": identifier.rsplit("-", maxsplit=1)[1],
        "functional_blocks": None,
        "module_definition_id": module,
        "object_ids": [],
    }


@pytest.mark.parametrize(
    ("object_id", "channel_ids", "expected"),
    [
        ("O-1_R-1", ["CH-1", "MD-2_CH-1"], "CH-1"),
        ("MD-2_O-2-1_R-1", ["CH-1", "MD-2_CH-1"], "MD-2_CH-1"),
        ("MD-2_SM-1_O-3-1_R-2", ["CH-1", "MD-2_CH-1"], "MD-2_CH-1"),
        ("MD-3_O-1-1_R-1", ["CH-1", "MD-2_CH-1"], "CH-1"),
        ("O-1_R-1", ["CH-404"], None),
        ("O-1_R-1", [], None),
    ],
)
def test_object_channel_id(
    object_id: str, channel_ids: list[str], expected: str | None
) -> None:
    """Test the channel an object definition belongs to."""
    definition: dict[str, Any] = {
        "channels": {
            "CH-1": _channel("CH-1", None),
            "MD-2_CH-1": _channel("MD-2_CH-1", "MD-2"),
        }
    }
    object_definition: dict[str, Any] = {
        "identifier": object_id,
        "channel_ids": channel_ids,
    }
    assert util.object_channel_id(definition, object_definition) == expected  # type: ignore[arg-type]


def test_linked_object_definitions() -> None:
    """Test linked object definitions are collected per application program."""
    project: dict[str, Any] = {
        "devices": {
            "1.1.1": {
                "application": "M-0083_A-1",
                "communication_object_ids": [
                    "1.1.1/O-1_R-1",
                    "1.1.1/O-2_R-2",
                    "1.1.1/O-9_R-9",
                ],
            },
            "1.1.2": {
                "application": "M-0083_A-1",
                "communication_object_ids": ["1.1.2/MD-2_M-1_MI-1_O-2-1_R-1"],
            },
            "1.1.3": {
                "application": None,
                "communication_object_ids": ["1.1.3/O-1_R-1"],
            },
        },
        "communication_objects": {
            "1.1.1/O-1_R-1": {"group_address_links": ["1/1/1"]},
            "1.1.1/O-2_R-2": {"group_address_links": []},
            "1.1.2/MD-2_M-1_MI-1_O-2-1_R-1": {"group_address_links": ["1/1/2"]},
            "1.1.3/O-1_R-1": {"group_address_links": ["1/1/3"]},
        },
    }
    assert util.linked_object_definitions(project) == {  # type: ignore[arg-type]
        "M-0083_A-1": {"O-1_R-1", "MD-2_O-2-1_R-1"}
    }
