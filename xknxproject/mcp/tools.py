"""
MCP tool functions for parsed ETS projects.

Each function takes a parsed :class:`~xknxproject.models.KNXProject` and,
optionally, a typed input, and returns a JSON-serialisable dataclass. They are
transport- and host-agnostic: no MCP SDK, Home Assistant or web-framework
imports, so every consumer wraps them into its own MCP transport.

The functions are ``async`` for a uniform calling convention across the XKNX
MCP tool libraries, even though project introspection is purely in-memory.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TypeVar

from ..models import (
    Area,
    CommunicationObject,
    Device,
    DPTType,
    GroupAddress,
    KNXProject,
    Space,
)
from .types import (
    AreaSummary,
    CommunicationObjectFilter,
    CommunicationObjectListResult,
    CommunicationObjectSummary,
    DeviceFilter,
    DeviceListResult,
    DeviceSummary,
    GroupAddressDetail,
    GroupAddressFilter,
    GroupAddressListResult,
    GroupAddressSummary,
    LineSummary,
    LocationsResult,
    ProjectInfoResult,
    SpaceSummary,
    TopologyResult,
)


def _format_dpt(dpt: DPTType | None) -> str | None:
    """Render a DPT as ``main.sub`` (sub zero-padded), or just ``main``."""
    if dpt is None:
        return None
    sub = dpt["sub"]
    if sub is None:
        return str(dpt["main"])
    return f"{dpt['main']}.{sub:03d}"


def _parse_dpt(entry: str) -> tuple[int, int | None]:
    """Parse a ``main`` or ``main.sub`` DPT string into a (main, sub|None) pair."""
    main_str, sep, sub_str = entry.strip().partition(".")
    if not main_str.isdigit() or (sep and not sub_str.isdigit()):
        raise ValueError(f"Invalid DPT: {entry!r}")
    return (int(main_str), int(sub_str) if sep else None)


def _dpt_matches(dpt: DPTType | None, wanted: Iterable[tuple[int, int | None]]) -> bool:
    """Whether ``dpt`` matches any ``(main, sub|None)`` selector (sub ``None`` matches any)."""
    if dpt is None:
        return False
    return any(dpt["main"] == main and sub in (None, dpt["sub"]) for main, sub in wanted)


def _flag_names(comobj: CommunicationObject) -> list[str]:
    """Return the names of the enabled flags on a communication object."""
    return [name for name, enabled in comobj["flags"].items() if enabled]


def _summarize_ga(ga: GroupAddress) -> GroupAddressSummary:
    return GroupAddressSummary(
        address=ga["address"],
        name=ga["name"],
        dpt=_format_dpt(ga["dpt"]),
        description=ga["description"],
        comment=ga["comment"],
        data_secure=ga["data_secure"],
        communication_object_ids=list(ga["communication_object_ids"]),
    )


def _summarize_comobj(comobj: CommunicationObject) -> CommunicationObjectSummary:
    return CommunicationObjectSummary(
        number=comobj["number"],
        name=comobj["name"],
        text=comobj["text"],
        function_text=comobj["function_text"],
        description=comobj["description"],
        device_address=comobj["device_address"],
        dpts=[dpt for dpt in (_format_dpt(d) for d in comobj["dpts"]) if dpt is not None],
        object_size=comobj["object_size"],
        flags=_flag_names(comobj),
        group_address_links=list(comobj["group_address_links"]),
    )


def _summarize_device(device: Device) -> DeviceSummary:
    return DeviceSummary(
        individual_address=device["individual_address"],
        name=device["name"],
        hardware_name=device["hardware_name"],
        manufacturer_name=device["manufacturer_name"],
        order_number=device["order_number"],
        description=device["description"],
        communication_object_ids=list(device["communication_object_ids"]),
    )


_T = TypeVar("_T")


def _paginate(items: list[_T], limit: int, offset: int) -> tuple[list[_T], bool]:
    """Slice ``items`` by ``offset``/``limit`` and report whether the limit was hit."""
    window = items[offset : offset + limit] if limit >= 0 else items[offset:]
    limit_reached = limit >= 0 and len(items) - offset > limit
    return window, limit_reached


async def get_project_info(project: KNXProject) -> ProjectInfoResult:
    """Report project metadata and top-level entity counts."""
    info = project["info"]
    area_count = len(project["topology"])
    return ProjectInfoResult(
        name=info["name"],
        group_address_style=info["group_address_style"],
        last_modified=info["last_modified"],
        schema_version=info["schema_version"],
        tool_version=info["tool_version"],
        xknxproject_version=info["xknxproject_version"],
        group_address_count=len(project["group_addresses"]),
        device_count=len(project["devices"]),
        communication_object_count=len(project["communication_objects"]),
        area_count=area_count,
        location_count=len(project["locations"]),
        function_count=len(project["functions"]),
    )


async def list_group_addresses(
    project: KNXProject, filters: GroupAddressFilter | None = None
) -> GroupAddressListResult:
    """List group addresses, optionally filtered by text and/or DPT."""
    filters = filters or GroupAddressFilter()
    wanted_dpts = [_parse_dpt(d) for d in filters.dpts]
    needle = filters.text.lower() if filters.text else None

    matches: list[GroupAddressSummary] = []
    for ga in project["group_addresses"].values():
        if needle is not None and needle not in (
            f"{ga['address']}\n{ga['name']}\n{ga['description']}\n{ga['comment']}".lower()
        ):
            continue
        if wanted_dpts and not _dpt_matches(ga["dpt"], wanted_dpts):
            continue
        matches.append(_summarize_ga(ga))

    window, limit_reached = _paginate(matches, filters.limit, filters.offset)
    return GroupAddressListResult(
        group_addresses=window,
        total_count=len(matches),
        limit_reached=limit_reached,
    )


async def describe_group_address(project: KNXProject, address: str) -> GroupAddressDetail:
    """Resolve one group address to its linked communication objects and devices."""
    target = next(
        (ga for ga in project["group_addresses"].values() if ga["address"] == address),
        None,
    )
    if target is None:
        return GroupAddressDetail(
            found=False, group_address=None, communication_objects=[], devices=[]
        )

    comobjs = [
        project["communication_objects"][co_id]
        for co_id in target["communication_object_ids"]
        if co_id in project["communication_objects"]
    ]
    devices = list(dict.fromkeys(co["device_address"] for co in comobjs))
    return GroupAddressDetail(
        found=True,
        group_address=_summarize_ga(target),
        communication_objects=[_summarize_comobj(co) for co in comobjs],
        devices=devices,
    )


async def list_devices(
    project: KNXProject, filters: DeviceFilter | None = None
) -> DeviceListResult:
    """List topology devices, optionally filtered by text."""
    filters = filters or DeviceFilter()
    needle = filters.text.lower() if filters.text else None

    matches: list[DeviceSummary] = []
    for device in project["devices"].values():
        if needle is not None and needle not in (
            f"{device['individual_address']}\n{device['name']}\n{device['hardware_name']}\n"
            f"{device['manufacturer_name']}\n{device['order_number']}".lower()
        ):
            continue
        matches.append(_summarize_device(device))

    window, limit_reached = _paginate(matches, filters.limit, filters.offset)
    return DeviceListResult(
        devices=window,
        total_count=len(matches),
        limit_reached=limit_reached,
    )


async def list_communication_objects(
    project: KNXProject, filters: CommunicationObjectFilter | None = None
) -> CommunicationObjectListResult:
    """List communication objects, optionally scoped to a device and/or group address."""
    filters = filters or CommunicationObjectFilter()
    needle = filters.text.lower() if filters.text else None

    matches: list[CommunicationObjectSummary] = []
    for comobj in project["communication_objects"].values():
        if filters.device_address is not None and comobj["device_address"] != filters.device_address:
            continue
        if (
            filters.group_address is not None
            and filters.group_address not in comobj["group_address_links"]
        ):
            continue
        if needle is not None and needle not in (
            f"{comobj['name']}\n{comobj['text']}\n{comobj['function_text']}\n"
            f"{comobj['description']}".lower()
        ):
            continue
        matches.append(_summarize_comobj(comobj))

    window, limit_reached = _paginate(matches, filters.limit, filters.offset)
    return CommunicationObjectListResult(
        communication_objects=window,
        total_count=len(matches),
        limit_reached=limit_reached,
    )


def _summarize_area(area: Area) -> AreaSummary:
    return AreaSummary(
        name=area["name"],
        description=area["description"],
        lines=[
            LineSummary(
                name=line["name"],
                medium_type=line["medium_type"],
                description=line["description"],
                devices=list(line["devices"]),
            )
            for line in area["lines"].values()
        ],
    )


async def get_topology(project: KNXProject) -> TopologyResult:
    """Return the bus topology as areas, each with its lines and device addresses."""
    return TopologyResult(
        areas=[_summarize_area(area) for area in project["topology"].values()]
    )


def _summarize_space(space: Space) -> SpaceSummary:
    return SpaceSummary(
        type=space["type"],
        name=space["name"],
        number=space["number"],
        description=space["description"],
        devices=list(space["devices"]),
        functions=list(space["functions"]),
        spaces=[_summarize_space(child) for child in space["spaces"].values()],
    )


async def list_locations(project: KNXProject) -> LocationsResult:
    """Return the building/location tree (spaces, nested, with devices and functions)."""
    return LocationsResult(
        spaces=[_summarize_space(space) for space in project["locations"].values()]
    )
