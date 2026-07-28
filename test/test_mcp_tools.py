"""Tests for the host-agnostic xknxproject MCP tool functions."""

import asyncio
import json
from typing import cast

import pytest

from xknxproject.mcp import (
    ChannelFilter,
    CommunicationObjectFilter,
    DeviceFilter,
    FindSimilarChannelsInput,
    FunctionFilter,
    GroupAddressFilter,
    describe_channel,
    describe_function,
    describe_group_address,
    find_similar_channels,
    get_project_info,
    get_topology,
    list_channels,
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

    # A non-matching space_id excludes the function.
    other_space = asyncio.run(
        list_functions(project_with_functions, FunctionFilter(space_id="does-not-exist"))
    )
    assert other_space.total_count == 0

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



@pytest.fixture(name="smart")
def smart_linking_fixture() -> KNXProject:
    """Load the parsed ``smart_linking`` stub (rich channels/functional-blocks/DPAs)."""
    with (STUBS_PATH / "smart_linking.json").open(encoding="utf-8") as stub:
        return cast(KNXProject, json.load(stub))


def test_device_summary_exposes_channels(smart: KNXProject) -> None:
    """Devices now carry their application id and channel list."""
    result = asyncio.run(list_devices(smart, DeviceFilter(text="1.0.1")))
    device = result.devices[0]
    assert device.application == "M-00E1_A-2036-40-865C"
    identifiers = {ch.identifier for ch in device.channels}
    assert {"CH-1", "CH-2", "CH-3"} <= identifiers
    ch1 = next(ch for ch in device.channels if ch.identifier == "CH-1")
    assert ch1.functional_blocks == ["417"]


def test_communication_object_summary_exposes_semantics(smart: KNXProject) -> None:
    """Communication objects now carry channel and DPA semantics."""
    result = asyncio.run(
        list_communication_objects(smart, CommunicationObjectFilter(group_address="0/0/1"))
    )
    comobj = result.communication_objects[0]
    assert comobj.channel == "CH-1"
    assert comobj.dpas == ["417.52"]


def test_list_channels_filters(smart: KNXProject) -> None:
    """Channels are listed and filterable by device, functional block and text."""
    everything = asyncio.run(list_channels(smart))
    assert everything.total_count == 12
    assert all(ch.device_address for ch in everything.channels)

    by_fb = asyncio.run(list_channels(smart, ChannelFilter(functional_block="417")))
    assert by_fb.total_count == 7

    by_device = asyncio.run(list_channels(smart, ChannelFilter(device_address="1.0.1")))
    assert {ch.identifier for ch in by_device.channels} == {"CH-1", "CH-2", "CH-3"}

    by_text = asyncio.run(list_channels(smart, ChannelFilter(text="Ausgang A")))
    assert [ch.identifier for ch in by_text.channels] == ["CH-1"]


def test_describe_channel(smart: KNXProject) -> None:
    """A channel resolves to its communication objects and their GAs."""
    detail = asyncio.run(describe_channel(smart, "1.0.1", "CH-1"))
    assert detail.found
    assert detail.channel is not None
    assert detail.channel.functional_blocks == ["417"]
    assert detail.group_addresses == ["0/0/1"]
    assert detail.communication_objects[0].dpas == ["417.52"]


def test_describe_channel_missing(smart: KNXProject) -> None:
    """An unknown device or channel returns a not-found result."""
    assert not asyncio.run(describe_channel(smart, "1.0.1", "CH-999")).found
    assert not asyncio.run(describe_channel(smart, "9.9.9", "CH-1")).found


def test_find_similar_channels(smart: KNXProject) -> None:
    """Similar channels are found by functional block and their GAs aligned by DPA."""
    result = asyncio.run(
        find_similar_channels(smart, FindSimilarChannelsInput(device_address="1.0.1", channel_identifier="CH-1"))
    )
    assert result.found
    assert result.reference is not None
    assert result.reference.identifier == "CH-1"

    # The other six 417 channels (2 same-device, 4 on 1.0.2) match by functional block.
    assert len(result.channels) == 6
    assert all(sc.match_reason == "functional_block:417" for sc in result.channels)

    # The reference's "417.52" object aligns with the same slot on the other channels.
    slot = next(a for a in result.aligned_group_objects if a.key == "417.52")
    ref_entry = next(e for e in slot.entries if e.device_address == "1.0.1" and e.channel_identifier == "CH-1")
    assert ref_entry.group_addresses == ["0/0/1"]
    assert any(e.device_address == "1.0.2" for e in slot.entries)


def test_find_similar_channels_missing(smart: KNXProject) -> None:
    """An unknown reference channel returns an empty, not-found result."""
    result = asyncio.run(
        find_similar_channels(smart, FindSimilarChannelsInput(device_address="1.0.1", channel_identifier="CH-999"))
    )
    assert not result.found
    assert result.reference is None
    assert result.channels == []
    assert result.aligned_group_objects == []


def _module_project() -> KNXProject:
    """Build a tiny synthetic project where channels align by module, not DPA."""
    flags = {
        "read": False,
        "write": True,
        "communication": True,
        "transmit": True,
        "update": False,
        "read_on_init": False,
    }

    def comobj(number: int, device: str, channel: str, module: object, dpas: object) -> dict:
        return {
            "name": f"CO{number}",
            "number": number,
            "text": "",
            "function_text": "Switch",
            "description": "",
            "device_address": device,
            "device_application": None,
            "module": module,
            "channel": channel,
            "dpts": [],
            "object_size": "1 Bit",
            "group_address_links": [f"1/0/{number}"],
            "flags": flags,
            "dpas": dpas,
        }

    def device(addr: str, channel_id: str, co_ids: list[str]) -> dict:
        return {
            "name": f"Dev {addr}",
            "hardware_name": "HW",
            "order_number": "ORD",
            "description": "",
            "manufacturer_name": "ACME",
            "individual_address": addr,
            "application": "APP-1",
            "project_uid": None,
            "communication_object_ids": co_ids,
            "channels": {
                channel_id: {
                    "identifier": channel_id,
                    "name": f"Channel {channel_id}",
                    "communication_object_ids": co_ids,
                    "functional_blocks": [],  # force module-based matching
                }
            },
        }

    mod = {"definition": "MOD-1", "root_number": 0}
    return cast(
        KNXProject,
        {
            "info": {
                "project_id": "P", "name": "mod", "last_modified": None,
                "group_address_style": "ThreeLevel", "guid": "g", "created_by": "ETS",
                "schema_version": "21", "tool_version": "6", "xknxproject_version": "3.9.0",
                "language_code": None,
            },
            "communication_objects": {
                "A/O-1": comobj(1, "1.1.1", "CH-A", mod, []),
                "B/O-1": comobj(1, "1.1.2", "CH-B", mod, []),
                "B/O-2": comobj(2, "1.1.2", "CH-B", None, []),  # no module, no dpa -> num key
            },
            "devices": {
                "1.1.1": device("1.1.1", "CH-A", ["A/O-1", "A/O-missing"]),  # dangling id
                "1.1.2": device("1.1.2", "CH-B", ["B/O-1", "B/O-2"]),
            },
            "topology": {}, "locations": {}, "group_addresses": {},
            "group_ranges": {}, "functions": {},
        },
    )


def test_find_similar_channels_by_module() -> None:
    """Channels align by module definition/offset when they carry no DPAs."""
    project = _module_project()

    # describe_channel surfaces the module ref on the summarized comobj.
    detail = asyncio.run(describe_channel(project, "1.1.1", "CH-A"))
    assert detail.communication_objects[0].module is not None
    assert detail.communication_objects[0].module.definition == "MOD-1"

    result = asyncio.run(
        find_similar_channels(
            project, FindSimilarChannelsInput(device_address="1.1.1", channel_identifier="CH-A")
        )
    )
    assert result.found
    assert [sc.match_reason for sc in result.channels] == ["module:MOD-1"]

    keys = {a.key for a in result.aligned_group_objects}
    assert "root:0" in keys  # module offset key
    assert "num:2" in keys  # the object with neither DPA nor module
    root_slot = next(a for a in result.aligned_group_objects if a.key == "root:0")
    assert {e.device_address for e in root_slot.entries} == {"1.1.1", "1.1.2"}
