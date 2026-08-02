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
    Channel,
    CommunicationObject,
    Device,
    DPTType,
    Function,
    GroupAddress,
    KNXProject,
    Space,
)
from ..models.knxproject import ModuleInstanceInfos
from .types import (
    AlignedEntry,
    AlignedGroupObject,
    AreaSummary,
    ChannelDetail,
    ChannelFilter,
    ChannelListResult,
    ChannelSummary,
    CommunicationObjectFilter,
    CommunicationObjectListResult,
    CommunicationObjectSummary,
    DeviceFilter,
    DeviceListResult,
    DeviceSummary,
    FindSimilarChannelsInput,
    FindSimilarChannelsResult,
    FunctionDetail,
    FunctionFilter,
    FunctionListResult,
    FunctionSummary,
    GroupAddressDetail,
    GroupAddressFilter,
    GroupAddressListResult,
    GroupAddressRefSummary,
    GroupAddressSummary,
    LineSummary,
    LocationsResult,
    ModuleRef,
    ProjectInfoResult,
    SimilarChannel,
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
    return any(
        dpt["main"] == main and sub in (None, dpt["sub"]) for main, sub in wanted
    )


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


def _module_ref(module: ModuleInstanceInfos | None) -> ModuleRef | None:
    """Convert a parsed module-instance dict to a :class:`ModuleRef`, if present."""
    if module is None:
        return None
    return ModuleRef(definition=module["definition"], root_number=module["root_number"])


def _summarize_comobj(comobj: CommunicationObject) -> CommunicationObjectSummary:
    # channel / dpas / module were added to the model later (semantics parsing);
    # read them defensively so older parses and fixtures don't KeyError.
    return CommunicationObjectSummary(
        number=comobj["number"],
        name=comobj["name"],
        text=comobj["text"],
        function_text=comobj["function_text"],
        description=comobj["description"],
        device_address=comobj["device_address"],
        dpts=[
            dpt for dpt in (_format_dpt(d) for d in comobj["dpts"]) if dpt is not None
        ],
        object_size=comobj["object_size"],
        flags=_flag_names(comobj),
        group_address_links=list(comobj["group_address_links"]),
        channel=comobj.get("channel"),
        dpas=list(comobj.get("dpas") or []),
        module=_module_ref(comobj.get("module")),
    )


def _summarize_channel(device_address: str, channel: Channel) -> ChannelSummary:
    return ChannelSummary(
        device_address=device_address,
        identifier=channel["identifier"],
        name=channel["name"],
        functional_blocks=list(channel.get("functional_blocks") or []),
        communication_object_ids=list(channel["communication_object_ids"]),
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
        application=device.get("application"),
        channels=[
            _summarize_channel(device["individual_address"], channel)
            for channel in (device.get("channels") or {}).values()
        ],
    )


_T = TypeVar("_T")


def _paginate(items: list[_T], limit: int, offset: int) -> tuple[list[_T], bool]:
    """Slice ``items`` by ``offset``/``limit`` and report whether the limit was hit."""
    window = items[offset : offset + limit] if limit >= 0 else items[offset:]
    limit_reached = 0 <= limit < len(items) - offset
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
        offset=filters.offset,
        next_offset=filters.offset + len(window) if limit_reached else None,
        limit_reached=limit_reached,
    )


async def describe_group_address(
    project: KNXProject, address: str
) -> GroupAddressDetail:
    """Resolve one group address to its linked communication objects and devices."""
    # ``group_addresses`` is keyed by the address string, so this is O(1).
    target = project["group_addresses"].get(address)
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
        offset=filters.offset,
        next_offset=filters.offset + len(window) if limit_reached else None,
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
        if (
            filters.device_address is not None
            and comobj["device_address"] != filters.device_address
        ):
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
        offset=filters.offset,
        next_offset=filters.offset + len(window) if limit_reached else None,
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


def _summarize_function(func: Function) -> FunctionSummary:
    return FunctionSummary(
        identifier=func["identifier"],
        name=func["name"],
        function_type=func["function_type"],
        space_id=func["space_id"],
        usage_text=func["usage_text"],
        group_address_count=len(func["group_addresses"]),
    )


async def list_functions(
    project: KNXProject, filters: FunctionFilter | None = None
) -> FunctionListResult:
    """List project functions, optionally filtered by text and/or space_id."""
    filters = filters or FunctionFilter()
    needle = filters.text.lower() if filters.text else None

    matches: list[FunctionSummary] = []
    functions_dict = project.get("functions", {})
    for func in functions_dict.values():
        if filters.space_id is not None and func["space_id"] != filters.space_id:
            continue
        if needle is not None and needle not in (
            f"{func['identifier']}\n{func['name']}\n{func['function_type']}\n{func['usage_text']}".lower()
        ):
            continue
        matches.append(_summarize_function(func))

    window, limit_reached = _paginate(matches, filters.limit, filters.offset)
    return FunctionListResult(
        functions=window,
        total_count=len(matches),
        offset=filters.offset,
        next_offset=filters.offset + len(window) if limit_reached else None,
        limit_reached=limit_reached,
    )


async def describe_function(project: KNXProject, identifier: str) -> FunctionDetail:
    """Resolve a functional block (ETS function) by its identifier."""
    functions_dict = project.get("functions", {})
    target = functions_dict.get(identifier)
    if target is None:
        return FunctionDetail(found=False, function=None, group_addresses=[])

    ga_refs = [
        GroupAddressRefSummary(
            address=ga_ref["address"],
            name=ga_ref["name"],
            role=ga_ref["role"],
        )
        for ga_ref in target["group_addresses"].values()
    ]
    return FunctionDetail(
        found=True,
        function=_summarize_function(target),
        group_addresses=ga_refs,
    )


def _find_channel(
    project: KNXProject, device_address: str, channel_identifier: str
) -> Channel | None:
    device = project["devices"].get(device_address)
    if device is None:
        return None
    return next(
        (
            ch
            for ch in (device.get("channels") or {}).values()
            if ch["identifier"] == channel_identifier
        ),
        None,
    )


def _module_definitions(project: KNXProject, channel: Channel) -> set[str]:
    """Return the module definitions among a channel's communication objects."""
    definitions: set[str] = set()
    for co_id in channel["communication_object_ids"]:
        comobj = project["communication_objects"].get(co_id)
        module = comobj.get("module") if comobj is not None else None
        if module is not None:
            definitions.add(module["definition"])
    return definitions


def _alignment_key(comobj: CommunicationObject) -> str:
    """
    Return a stable semantic slot key for aligning a group object across channels.

    Prefer the DPA (semantic role), then the module offset, then the raw number.
    """
    dpas = comobj.get("dpas")
    if dpas:
        return dpas[0]
    module = comobj.get("module")
    if module is not None:
        return f"root:{module['root_number']}"
    return f"num:{comobj['number']}"


async def list_channels(
    project: KNXProject, filters: ChannelFilter | None = None
) -> ChannelListResult:
    """List device channels, optionally filtered by device, functional block or text."""
    filters = filters or ChannelFilter()
    needle = filters.text.lower() if filters.text else None

    matches: list[ChannelSummary] = []
    for device in project["devices"].values():
        if (
            filters.device_address is not None
            and device["individual_address"] != filters.device_address
        ):
            continue
        for channel in (device.get("channels") or {}).values():
            summary = _summarize_channel(device["individual_address"], channel)
            if (
                filters.functional_block is not None
                and filters.functional_block not in summary.functional_blocks
            ):
                continue
            if (
                needle is not None
                and needle not in f"{summary.identifier}\n{summary.name}".lower()
            ):
                continue
            matches.append(summary)

    window, limit_reached = _paginate(matches, filters.limit, filters.offset)
    return ChannelListResult(
        channels=window,
        total_count=len(matches),
        offset=filters.offset,
        next_offset=filters.offset + len(window) if limit_reached else None,
        limit_reached=limit_reached,
    )


async def describe_channel(
    project: KNXProject, device_address: str, channel_identifier: str
) -> ChannelDetail:
    """Resolve one channel to its communication objects and their group addresses."""
    channel = _find_channel(project, device_address, channel_identifier)
    if channel is None:
        return ChannelDetail(
            found=False, channel=None, communication_objects=[], group_addresses=[]
        )

    comobjs = [
        project["communication_objects"][co_id]
        for co_id in channel["communication_object_ids"]
        if co_id in project["communication_objects"]
    ]
    group_addresses = list(
        dict.fromkeys(ga for co in comobjs for ga in co["group_address_links"])
    )
    return ChannelDetail(
        found=True,
        channel=_summarize_channel(device_address, channel),
        communication_objects=[_summarize_comobj(co) for co in comobjs],
        group_addresses=group_addresses,
    )


def _match_reason(
    request: FindSimilarChannelsInput,
    reference_fbs: set[str],
    reference_defs: set[str],
    project: KNXProject,
    channel: Channel,
) -> str | None:
    if request.match_functional_blocks:
        shared = reference_fbs & set(channel.get("functional_blocks") or [])
        if shared:
            return f"functional_block:{min(shared)}"
    if request.match_module_definition:
        shared_defs = reference_defs & _module_definitions(project, channel)
        if shared_defs:
            return f"module:{min(shared_defs)}"
    return None


async def find_similar_channels(
    project: KNXProject, request: FindSimilarChannelsInput
) -> FindSimilarChannelsResult:
    """
    Find channels like the reference and align their group objects (and GAs).

    Channels are "similar" when they share a functional block or a module
    definition. Group objects are aligned into semantic slots (keyed by DPA or
    module offset) so a consumer can read off, per slot, which GA each similar
    channel uses.
    """
    reference = _find_channel(
        project, request.device_address, request.channel_identifier
    )
    if reference is None:
        return FindSimilarChannelsResult(
            found=False, reference=None, channels=[], aligned_group_objects=[]
        )

    reference_fbs = set(reference.get("functional_blocks") or [])
    reference_defs = _module_definitions(project, reference)

    matches: list[SimilarChannel] = []
    to_align: list[tuple[str, Channel]] = [(request.device_address, reference)]
    for device in project["devices"].values():
        for channel in (device.get("channels") or {}).values():
            if (
                device["individual_address"] == request.device_address
                and channel["identifier"] == request.channel_identifier
            ):
                continue
            reason = _match_reason(
                request, reference_fbs, reference_defs, project, channel
            )
            if reason is None:
                continue
            matches.append(
                SimilarChannel(
                    device_address=device["individual_address"],
                    identifier=channel["identifier"],
                    name=channel["name"],
                    functional_blocks=list(channel.get("functional_blocks") or []),
                    match_reason=reason,
                )
            )
            to_align.append((device["individual_address"], channel))

    entries_by_key: dict[str, list[AlignedEntry]] = {}
    label_by_key: dict[str, str] = {}
    for device_address, channel in to_align:
        for co_id in channel["communication_object_ids"]:
            comobj = project["communication_objects"].get(co_id)
            if comobj is None:
                continue
            key = _alignment_key(comobj)
            label_by_key.setdefault(key, comobj["function_text"])
            entries_by_key.setdefault(key, []).append(
                AlignedEntry(
                    device_address=device_address,
                    channel_identifier=channel["identifier"],
                    number=comobj["number"],
                    dpas=list(comobj.get("dpas") or []),
                    group_addresses=list(comobj["group_address_links"]),
                )
            )

    aligned = [
        AlignedGroupObject(
            key=key, function_text=label_by_key[key], entries=entries_by_key[key]
        )
        for key in sorted(entries_by_key)
    ]
    return FindSimilarChannelsResult(
        found=True,
        reference=_summarize_channel(request.device_address, reference),
        channels=matches,
        aligned_group_objects=aligned,
    )
