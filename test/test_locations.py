"""Test location export."""

from __future__ import annotations

import logging

import pytest

from xknxproject.models import SpaceType, XMLSpace
from xknxproject.xml.parser import _device_space_ids, _recursive_convert_spaces


def _space(
    identifier: str, name: str, devices: list[str], spaces: list[XMLSpace]
) -> XMLSpace:
    return XMLSpace(
        identifier=identifier,
        name=name,
        space_type=SpaceType.ROOM,
        usage_id=None,
        usage_text="",
        number="",
        description="",
        project_uid=None,
        spaces=spaces,
        devices=devices,
        functions=[],
    )


def test_sibling_space_name_collision_warns(caplog: pytest.LogCaptureFixture) -> None:
    """Two sibling spaces with the same name log a warning and both are kept."""
    spaces = [
        _space("P-1_BP-2", "Flur", ["1.1.1"], []),
        _space("P-1_BP-3", "Flur", ["1.1.2"], []),
    ]
    with caplog.at_level(logging.WARNING, logger="xknxproject.log"):
        result = _recursive_convert_spaces(spaces)

    assert list(result) == ["Flur", "Flur (P-1_BP-3)"]
    assert result["Flur"]["identifier"] == "P-1_BP-2"
    assert result["Flur (P-1_BP-3)"]["identifier"] == "P-1_BP-3"
    assert result["Flur (P-1_BP-3)"]["name"] == "Flur"
    assert "Flur" in caplog.text
    assert "P-1_BP-2" in caplog.text
    assert "P-1_BP-3" in caplog.text


def test_device_space_ids_use_the_listing_space() -> None:
    """Outer and nested devices map to the identifier of the space listing them."""
    spaces = [
        _space(
            "P-1_BP-1",
            "Haus",
            ["1.1.9"],
            [_space("P-1_BP-2", "Küche", ["1.1.1", "1.1.2"], [])],
        )
    ]
    assert _device_space_ids(spaces) == {
        "1.1.9": "P-1_BP-1",
        "1.1.1": "P-1_BP-2",
        "1.1.2": "P-1_BP-2",
    }
