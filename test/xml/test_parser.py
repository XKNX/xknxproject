"""Test parser."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import Mock

import pytest

from xknxproject.loader import (
    ApplicationProgramLoader,
    HardwareLoader,
    KNXMasterLoader,
    ProjectLoader,
)
from xknxproject.models import Product, SpaceType, XMLSpace
from xknxproject.xml.parser import XMLParser, _recursive_convert_spaces
from xknxproject.zip import KNXProjContents, extract

from .. import RESOURCES_PATH
from ..conftest import build_devices

xknx_test_project_protected_ets5 = RESOURCES_PATH / "xknx_test_project.knxproj"
xknx_test_project_module_defs = RESOURCES_PATH / "module-definition-test.knxproj"
xknx_test_project_ets5 = RESOURCES_PATH / "xknx_test_project_no_password.knxproj"
xknx_test_project_protected_ets6 = RESOURCES_PATH / "testprojekt-ets6.knxproj"


def test_parse_project_ets6() -> None:
    """Test parsing of group addresses."""
    with extract(xknx_test_project_protected_ets6, "test") as knx_project_contents:
        parser = XMLParser(knx_project_contents)
        parser.parse()

    assert len(parser.group_addresses) == 3
    assert parser.group_addresses[0].address == "0/1/0"
    assert parser.group_addresses[1].address == "0/1/1"
    assert parser.group_addresses[2].address == "0/1/2"

    assert len(parser.areas) == 2
    assert len(parser.areas[1].lines) == 2
    assert len(parser.areas[1].lines[1].devices) == 3
    assert len(parser.areas[1].lines[1].devices[0].additional_addresses) == 4
    # All instantiated communication objects are exposed, including those with no
    # group address links; the subset that carries links stays at 2.
    _device = parser.areas[1].lines[1].devices[1]
    assert len(_device.com_object_instance_refs) == 8
    _linkless = [c for c in _device.com_object_instance_refs if not c.links]
    assert len(_linkless) == 6
    assert sum(bool(c.links) for c in _device.com_object_instance_refs) == 2
    # The kept link-less objects are usable, not just present: each is merged from the
    # application program (com object number and DPT), which is the point of keeping them.
    assert all(c.number is not None for c in _linkless)
    assert all(c.datapoint_types for c in _linkless)
    assert parser.areas[1].lines[1].devices[0].manufacturer_name == "MDT technologies"


def test_parse_project_ets5() -> None:
    """Test parsing of ETS5 project."""
    with extract(xknx_test_project_protected_ets5, "test") as knx_project_contents:
        parser = XMLParser(knx_project_contents)
        parser.parse()

    assert len(parser.group_addresses) == 19
    parsed_gas = {ga.address for ga in parser.group_addresses}
    assert len(parsed_gas) == len(parser.group_addresses)
    assert parsed_gas == {
        "1/0/0",
        "1/0/1",
        "1/0/2",
        "1/0/3",
        "1/0/4",
        "1/0/5",
        "2/0/0",
        "2/0/1",
        "2/0/6",
        "2/1/1",
        "2/1/2",
        "2/1/10",
        "2/1/21",
        "2/1/22",
        "2/1/23",
        "7/0/0",
        "7/1/0",
        "7/1/1",
        "7/1/2",
    }

    assert len(parser.areas) == 2
    assert len(parser.areas[1].lines) == 2
    assert len(parser.areas[1].lines[1].devices) == 4
    assert len(parser.areas[1].lines[1].devices[0].additional_addresses) == 4
    assert len(parser.areas[1].lines[1].devices[1].com_object_instance_refs) == 7


@pytest.mark.parametrize(
    ("filename", "password"),
    [
        (RESOURCES_PATH / "test_project-ets4-no_password.knxproj", None),
        (RESOURCES_PATH / "test_project-ets4.knxproj", "test"),
    ],
)
def test_parse_project_ets4(filename: Path, password: str | None) -> None:
    """Test parsing of ETS4 project."""
    with extract(filename, password) as knx_project_contents:
        parser = XMLParser(knx_project_contents)
        parser.parse()

    assert len(parser.group_addresses) == 3
    parsed_gas = {ga.address for ga in parser.group_addresses}
    assert len(parsed_gas) == len(parser.group_addresses)
    assert parsed_gas == {
        "0/0/1",
        "0/0/2",
        "0/0/3",
    }

    assert len(parser.areas) == 1
    assert len(parser.areas[0].lines) == 1
    assert len(parser.areas[0].lines[0].devices) == 2
    assert parser.areas[0].lines[0].devices[0].manufacturer_name == "MDT technologies"
    assert parser.areas[0].lines[0].devices[1].manufacturer_name == "ABB"

    assert len(parser.devices) == 2
    assert parser.devices[0].individual_address == "0.0.1"
    assert parser.devices[1].individual_address == "0.0.2"


def test_parse_project_with_module_defs() -> None:
    """Test parsing of ETS5 project with module definitions."""
    with extract(xknx_test_project_module_defs) as knx_project_contents:
        parser = XMLParser(knx_project_contents)
        parser.parse()

    assert len(parser.group_addresses) == 25
    assert parser.group_addresses[0].address == "0/0/1"
    assert parser.group_addresses[1].address == "0/0/2"
    assert parser.group_addresses[2].address == "0/0/3"

    assert len(parser.areas) == 2
    assert len(parser.areas[1].lines) == 2
    assert len(parser.areas[1].lines[1].devices) == 4

    assert len(parser.devices) == 4


def _space(
    identifier: str, name: str, devices: list[str], spaces: list[XMLSpace]
) -> XMLSpace:
    """Build a room space listing the given devices and child spaces."""
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
    """Later same-named siblings are keyed "<name> (<identifier>)" with a warning."""
    spaces = [
        _space("P-1_BP-2", "Flur", ["1.1.1"], []),
        _space(
            "P-1_BP-3",
            "Flur",
            ["1.1.2"],
            [_space("P-1_BP-4", "Abstellraum", ["1.1.3"], [])],
        ),
        _space("P-1_BP-5", "Flur", [], []),
    ]
    with caplog.at_level(logging.WARNING, logger="xknxproject.log"):
        result = _recursive_convert_spaces(spaces)

    assert list(result) == ["Flur", "Flur (P-1_BP-3)", "Flur (P-1_BP-5)"]
    assert result["Flur"]["identifier"] == "P-1_BP-2"
    renamed = result["Flur (P-1_BP-3)"]
    assert renamed["identifier"] == "P-1_BP-3"
    assert renamed["name"] == "Flur"
    assert renamed["devices"] == ["1.1.2"]
    assert renamed["spaces"]["Abstellraum"]["devices"] == ["1.1.3"]
    assert result["Flur (P-1_BP-5)"]["identifier"] == "P-1_BP-5"
    assert [record.levelno for record in caplog.records] == [logging.WARNING] * 2
    assert caplog.messages == [
        "Sibling space P-1_BP-2 already uses the key 'Flur': "
        "space P-1_BP-3 is exported under the key 'Flur (P-1_BP-3)'",
        "Sibling space P-1_BP-2 already uses the key 'Flur': "
        "space P-1_BP-5 is exported under the key 'Flur (P-1_BP-5)'",
    ]


def test_same_space_name_under_different_parents_is_kept(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Spaces sharing a name under different parents keep the plain name as key."""
    spaces = [
        _space("P-1_BP-1", "EG", [], [_space("P-1_BP-2", "Flur", [], [])]),
        _space("P-1_BP-3", "OG", [], [_space("P-1_BP-4", "Flur", [], [])]),
    ]
    with caplog.at_level(logging.WARNING, logger="xknxproject.log"):
        result = _recursive_convert_spaces(spaces)

    assert list(result["EG"]["spaces"]) == ["Flur"]
    assert list(result["OG"]["spaces"]) == ["Flur"]
    assert result["EG"]["spaces"]["Flur"]["identifier"] == "P-1_BP-2"
    assert result["OG"]["spaces"]["Flur"]["identifier"] == "P-1_BP-4"
    assert not caplog.records


@pytest.mark.parametrize(
    ("spaces", "expected_keys"),
    [
        (  # the literal name is taken first, the disambiguated key collides with it
            [
                _space("P-1_BP-9", "Flur (P-1_BP-3)", [], []),
                _space("P-1_BP-2", "Flur", [], []),
                _space("P-1_BP-3", "Flur", [], []),
            ],
            {
                "Flur (P-1_BP-3)": "P-1_BP-9",
                "Flur": "P-1_BP-2",
                "Flur (P-1_BP-3) (P-1_BP-3)": "P-1_BP-3",
            },
        ),
        (  # the disambiguated key is taken first, the literal name collides with it
            [
                _space("P-1_BP-2", "Flur", [], []),
                _space("P-1_BP-3", "Flur", [], []),
                _space("P-1_BP-9", "Flur (P-1_BP-3)", [], []),
            ],
            {
                "Flur": "P-1_BP-2",
                "Flur (P-1_BP-3)": "P-1_BP-3",
                "Flur (P-1_BP-3) (P-1_BP-9)": "P-1_BP-9",
            },
        ),
    ],
)
def test_sibling_named_like_a_disambiguated_key_is_kept(
    spaces: list[XMLSpace], expected_keys: dict[str, str]
) -> None:
    """A sibling literally named "<name> (<identifier>)" never displaces a space."""
    result = _recursive_convert_spaces(spaces)

    assert {key: space["identifier"] for key, space in result.items()} == (
        expected_keys
    )


def test_load_sets_hardware_id_of_resolved_products(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A device gets the Hardware Id of its product, "" if the product is unknown."""
    devices = build_devices(("P-1_DI-1", 1), ("P-1_DI-2", 2))
    # product found, but its hardware2program is not: the hardware id is still set
    devices[0].product_ref = "M-0083_H-1_P-1"
    devices[0].hardware_program_ref = "M-0083_H-1_HP-unknown"
    devices[1].product_ref = "M-0083_H-2_P-unknown"
    product = Product(
        identifier="M-0083_H-1_P-1",
        text="Schaltaktor",
        order_number="4711",
        hardware_name="Schaltaktor 8fach",
        hardware_id="M-0083_H-1",
    )
    monkeypatch.setattr(KNXMasterLoader, "load", lambda **_: (Mock(), None))
    monkeypatch.setattr(
        ProjectLoader,
        "load",
        lambda **_: ([], [], [], devices, [], Mock(), []),
    )
    monkeypatch.setattr(HardwareLoader, "get_hardware_files", lambda **_: [Mock()])
    monkeypatch.setattr(
        HardwareLoader, "load", lambda **_: ({product.identifier: product}, {})
    )
    monkeypatch.setattr(
        ApplicationProgramLoader,
        "get_application_program_files_for_devices",
        lambda **_: {},
    )

    project_contents = Mock(spec=KNXProjContents, root_path=Path("project"))
    XMLParser(project_contents)._load(language=None)

    assert devices[0].hardware_id == "M-0083_H-1"
    assert devices[0].application_program_ref is None
    assert devices[1].hardware_id == ""
