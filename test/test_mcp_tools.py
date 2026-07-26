"""Tests for the host-agnostic xknxproject MCP tool functions."""

import asyncio
import json
from typing import cast

import pytest

from xknxproject.mcp import (
    CommunicationObjectFilter,
    DeviceFilter,
    FunctionFilter,
    GroupAddressFilter,
    describe_group_address,
    describe_function,
    get_project_info,
    get_topology,
    list_communication_objects,
    list_devices,
    list_functions,
    list_group_addresses,
    list_locations,
)
from xknxproject.models import KNXProject

from . import STUBS_PATH


@pytest.fixture(name="project")
def project_fixture() -> KNXProject:
    """Load the parsed ``xknx_test_project`` stub as a KNXProject."""
    with (STUBS_PATH / "xknx_test_project.json").open(encoding="utf-8") as stub:
        return cast(KNXProject, json.load(stub))


def test_get_project_info(project: KNXProject) -> None:
    """Project info reports metadata and the top-level entity counts."""
    info = asyncio.run(get_project_info(project))
    assert info.name == "xknx test project"
    assert info.group_address_style == "ThreeLevel"
    assert info.group_address_count == 19
    assert info.device_count == 4
    assert info.communication_object_count == 17
    assert info.area_count == 2
    assert info.location_count == 1


def test_list_group_addresses_unfiltered(project: KNXProject) -> None:
    """Without a filter every group address is returned."""
    result = asyncio.run(list_group_addresses(project))
    assert result.total_count == 19
    assert len(result.group_addresses) == 19
    assert not result.limit_reached


def test_list_group_addresses_pagination(project: KNXProject) -> None:
    """A limit truncates the window and flags that more matched."""
    result = asyncio.run(list_group_addresses(project, GroupAddressFilter(limit=5)))
    assert result.total_count == 19
    assert len(result.group_addresses) == 5
    assert result.limit_reached
    # Pagination is self-describing: next_offset points past the returned window.
    assert result.offset == 0
    assert result.next_offset == 5
    full = asyncio.run(list_group_addresses(project, GroupAddressFilter(limit=1000)))
    assert full.next_offset is None


def test_list_group_addresses_text_and_dpt_filters(project: KNXProject) -> None:
    """Text matches the address; a bare DPT main matches every subtype."""
    by_text = asyncio.run(list_group_addresses(project, GroupAddressFilter(text="1/0/0")))
    assert by_text.total_count == 1
    assert by_text.group_addresses[0].address == "1/0/0"
    assert by_text.group_addresses[0].dpt == "1.008"

    by_dpt = asyncio.run(list_group_addresses(project, GroupAddressFilter(dpts=["9"])))
    assert by_dpt.total_count == 8
    assert all(ga.dpt is not None and ga.dpt.startswith("9") for ga in by_dpt.group_addresses)


def test_describe_group_address(project: KNXProject) -> None:
    """A known GA resolves to its communication object and device."""
    detail = asyncio.run(describe_group_address(project, "1/0/0"))
    assert detail.found
    assert detail.group_address is not None
    assert detail.group_address.address == "1/0/0"
    assert detail.devices == ["1.1.5"]
    assert len(detail.communication_objects) == 1
    flags = set(detail.communication_objects[0].flags)
    assert {"write", "communication"} <= flags
    assert "read" not in flags


def test_describe_group_address_missing(project: KNXProject) -> None:
    """An unknown address returns an empty, not-found result."""
    detail = asyncio.run(describe_group_address(project, "9/9/9"))
    assert not detail.found
    assert detail.group_address is None
    assert detail.communication_objects == []
    assert detail.devices == []


def test_list_devices(project: KNXProject) -> None:
    """Devices are listed and filterable by their individual address."""
    everything = asyncio.run(list_devices(project))
    assert everything.total_count == 4

    filtered = asyncio.run(list_devices(project, DeviceFilter(text="1.1.5")))
    assert filtered.total_count == 1
    assert filtered.devices[0].individual_address == "1.1.5"


def test_list_communication_objects_filters(project: KNXProject) -> None:
    """Communication objects scope to a device and/or a linked group address."""
    by_device = asyncio.run(
        list_communication_objects(project, CommunicationObjectFilter(device_address="1.1.5"))
    )
    assert by_device.total_count > 0
    assert all(co.device_address == "1.1.5" for co in by_device.communication_objects)

    by_ga = asyncio.run(
        list_communication_objects(project, CommunicationObjectFilter(group_address="1/0/0"))
    )
    assert by_ga.total_count == 1
    assert "1/0/0" in by_ga.communication_objects[0].group_address_links


def test_get_topology(project: KNXProject) -> None:
    """Topology exposes areas, each with lines and device addresses."""
    topology = asyncio.run(get_topology(project))
    names = {area.name for area in topology.areas}
    assert names == {"Backbone Bereich", "Neuer Bereich"}
    assert any(line.devices for area in topology.areas for line in area.lines)


def test_list_locations(project: KNXProject) -> None:
    """Locations expose the building/space tree."""
    locations = asyncio.run(list_locations(project))
    assert len(locations.spaces) == 1
    assert locations.spaces[0].type == "Building"


@pytest.fixture(name="project_with_functions")
def project_with_functions_fixture() -> KNXProject:
    """Load the parsed ``testprojekt-ets6-functions`` stub as a KNXProject."""
    with (STUBS_PATH / "testprojekt-ets6-functions.json").open(encoding="utf-8") as stub:
        return cast(KNXProject, json.load(stub))


def test_list_functions(project_with_functions: KNXProject) -> None:
    """Functions are listed and filterable."""
    everything = asyncio.run(list_functions(project_with_functions))
    assert everything.total_count == 1
    assert everything.functions[0].identifier == "F-1"
    assert everything.functions[0].name == "LivingroomLight"
    assert everything.functions[0].function_type == "FT-1"
    assert everything.functions[0].group_address_count == 2

    # Test filtering by text
    by_text = asyncio.run(
        list_functions(project_with_functions, FunctionFilter(text="Livingroom"))
    )
    assert by_text.total_count == 1

    # Test filtering by space_id
    by_space = asyncio.run(
        list_functions(project_with_functions, FunctionFilter(space_id="P-05C0-0_BP-2"))
    )
    assert by_space.total_count == 1

    # Test missing match
    no_match = asyncio.run(
        list_functions(project_with_functions, FunctionFilter(text="Nonexistent"))
    )
    assert no_match.total_count == 0


def test_describe_function(project_with_functions: KNXProject) -> None:
    """A known function resolves to its detail and GA refs."""
    detail = asyncio.run(describe_function(project_with_functions, "F-1"))
    assert detail.found
    assert detail.function is not None
    assert detail.function.identifier == "F-1"
    assert len(detail.group_addresses) == 2
    roles = {ref.role: ref.address for ref in detail.group_addresses}
    assert roles == {"SwitchOnOff": "0/0/1", "InfoOnOff": "0/0/2"}


def test_describe_function_missing(project_with_functions: KNXProject) -> None:
    """An unknown function returns an empty, not-found result."""
    detail = asyncio.run(describe_function(project_with_functions, "F-999"))
    assert not detail.found
    assert detail.function is None
    assert detail.group_addresses == []

