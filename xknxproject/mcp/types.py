"""
Input/output dataclasses for the xknxproject MCP tools.

All fields are JSON-native, so a consumer can build inputs directly from tool
arguments and serialise outputs with :func:`dataclasses.asdict` without custom
encoders. DPTs are rendered as ``"main"`` or ``"main.sub"`` strings.

Input fields carry their human-readable description as :data:`typing.Annotated`
metadata (a plain string). This keeps the library free of any schema/validation
dependency while letting a consumer surface per-parameter descriptions in its
tool schema via ``typing.get_type_hints(..., include_extras=True)``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated


@dataclass(frozen=True)
class GroupAddressFilter:
    """Filters for :func:`~xknxproject.mcp.tools.list_group_addresses`."""

    text: Annotated[
        str | None,
        "Case-insensitive match on the address, name, description and comment.",
    ] = None
    dpts: Annotated[
        list[str],
        'DPTs as "main" or "main.sub" strings; a bare main matches every subtype.',
    ] = field(default_factory=list)
    limit: Annotated[int, "Maximum number of results to return."] = 100
    offset: Annotated[int, "Number of results to skip, for pagination."] = 0


@dataclass(frozen=True)
class DeviceFilter:
    """Filters for :func:`~xknxproject.mcp.tools.list_devices`."""

    text: Annotated[
        str | None,
        "Case-insensitive match on the individual address, name, hardware name, "
        "manufacturer and order number.",
    ] = None
    limit: Annotated[int, "Maximum number of results to return."] = 100
    offset: Annotated[int, "Number of results to skip, for pagination."] = 0


@dataclass(frozen=True)
class CommunicationObjectFilter:
    """Filters for :func:`~xknxproject.mcp.tools.list_communication_objects`."""

    device_address: Annotated[
        str | None, "Restrict to one device's objects by individual address."
    ] = None
    group_address: Annotated[
        str | None, "Restrict to objects linked to this group address."
    ] = None
    text: Annotated[
        str | None,
        "Case-insensitive match on the name, text, function text and description.",
    ] = None
    limit: Annotated[int, "Maximum number of results to return."] = 100
    offset: Annotated[int, "Number of results to skip, for pagination."] = 0


@dataclass(frozen=True)
class GroupAddressSummary:
    """A JSON-serialisable view of a project group address."""

    address: str
    name: str
    dpt: str | None
    description: str
    comment: str
    data_secure: bool
    communication_object_ids: list[str]


@dataclass(frozen=True)
class GroupAddressListResult:
    """Result of :func:`~xknxproject.mcp.tools.list_group_addresses`."""

    group_addresses: list[GroupAddressSummary]
    total_count: int
    offset: int
    next_offset: int | None  # pass as ``offset`` for the next page; ``None`` when exhausted
    limit_reached: bool


@dataclass(frozen=True)
class ModuleRef:
    """
    The module instance a communication object belongs to.

    ``definition`` is the module (channel template) reused across similar
    devices; ``root_number`` is the object's base number within that module —
    the offset used to align the "same" object across instances.
    """

    definition: str
    root_number: int


@dataclass(frozen=True)
class CommunicationObjectSummary:
    """A JSON-serialisable view of a device communication object."""

    number: int
    name: str
    text: str
    function_text: str
    description: str
    device_address: str
    dpts: list[str]
    object_size: str
    flags: list[str]
    group_address_links: list[str]
    channel: str | None  # identifier of the owning channel, if any
    dpas: list[str]  # semantic device parameter addresses, e.g. "417.52"
    module: ModuleRef | None  # module instance + offset, when the object is modular


@dataclass(frozen=True)
class CommunicationObjectListResult:
    """Result of :func:`~xknxproject.mcp.tools.list_communication_objects`."""

    communication_objects: list[CommunicationObjectSummary]
    total_count: int
    offset: int
    next_offset: int | None  # pass as ``offset`` for the next page; ``None`` when exhausted
    limit_reached: bool


@dataclass(frozen=True)
class GroupAddressDetail:
    """
    Result of :func:`~xknxproject.mcp.tools.describe_group_address`.

    ``found`` is ``False`` when no GA with the requested address exists, in
    which case the remaining fields are empty.
    """

    found: bool
    group_address: GroupAddressSummary | None
    communication_objects: list[CommunicationObjectSummary]
    devices: list[str]


@dataclass(frozen=True)
class ChannelSummary:
    """
    A JSON-serialisable view of a device channel.

    ``functional_blocks`` is the channel's semantic type (e.g. ``"417"`` for a
    switch-actuator output); channels sharing it are instances of the same
    function across devices.
    """

    device_address: str
    identifier: str
    name: str
    functional_blocks: list[str]
    communication_object_ids: list[str]


@dataclass(frozen=True)
class DeviceSummary:
    """A JSON-serialisable view of a topology device."""

    individual_address: str
    name: str
    hardware_name: str
    manufacturer_name: str
    order_number: str
    description: str
    communication_object_ids: list[str]
    application: str | None  # same application program => same channel layout
    channels: list[ChannelSummary]


@dataclass(frozen=True)
class DeviceListResult:
    """Result of :func:`~xknxproject.mcp.tools.list_devices`."""

    devices: list[DeviceSummary]
    total_count: int
    offset: int
    next_offset: int | None  # pass as ``offset`` for the next page; ``None`` when exhausted
    limit_reached: bool


@dataclass(frozen=True)
class LineSummary:
    """A JSON-serialisable view of a topology line and its devices."""

    name: str
    medium_type: str
    description: str | None
    devices: list[str]


@dataclass(frozen=True)
class AreaSummary:
    """A JSON-serialisable view of a topology area and its lines."""

    name: str
    description: str | None
    lines: list[LineSummary]


@dataclass(frozen=True)
class TopologyResult:
    """Result of :func:`~xknxproject.mcp.tools.get_topology`."""

    areas: list[AreaSummary]


@dataclass(frozen=True)
class SpaceSummary:
    """A JSON-serialisable, recursive view of a location space."""

    type: str
    name: str
    number: str
    description: str
    devices: list[str]
    functions: list[str]
    spaces: list[SpaceSummary]


@dataclass(frozen=True)
class LocationsResult:
    """Result of :func:`~xknxproject.mcp.tools.list_locations`."""

    spaces: list[SpaceSummary]


@dataclass(frozen=True)
class ProjectInfoResult:
    """Result of :func:`~xknxproject.mcp.tools.get_project_info`."""

    name: str
    group_address_style: str
    last_modified: str | None
    schema_version: str
    tool_version: str
    xknxproject_version: str
    group_address_count: int
    device_count: int
    communication_object_count: int
    area_count: int
    location_count: int
    function_count: int


@dataclass(frozen=True)
class FunctionFilter:
    """Filters for :func:`~xknxproject.mcp.tools.list_functions`."""

    text: Annotated[
        str | None,
        "Case-insensitive match on the identifier, name, function_type and usage_text.",
    ] = None
    space_id: Annotated[
        str | None,
        "Optional parent space identifier to restrict results to a specific floor or room.",
    ] = None
    limit: Annotated[int, "Maximum number of results to return."] = 100
    offset: Annotated[int, "Number of results to skip, for pagination."] = 0


@dataclass(frozen=True)
class FunctionSummary:
    """A JSON-serialisable summary of a functional block (ETS function)."""

    identifier: str
    name: str
    function_type: str
    space_id: str
    usage_text: str
    group_address_count: int


@dataclass(frozen=True)
class FunctionListResult:
    """Result of :func:`~xknxproject.mcp.tools.list_functions`."""

    functions: list[FunctionSummary]
    total_count: int
    offset: int
    next_offset: int | None
    limit_reached: bool


@dataclass(frozen=True)
class GroupAddressRefSummary:
    """A JSON-serialisable summary of a group address reference in a function."""

    address: str
    name: str
    role: str


@dataclass(frozen=True)
class FunctionDetail:
    """Result of :func:`~xknxproject.mcp.tools.describe_function`."""

    found: bool
    function: FunctionSummary | None
    group_addresses: list[GroupAddressRefSummary]



@dataclass(frozen=True)
class ChannelFilter:
    """Filters for :func:`~xknxproject.mcp.tools.list_channels`."""

    device_address: Annotated[
        str | None, "Restrict to channels of this device (individual address)."
    ] = None
    functional_block: Annotated[
        str | None, 'Restrict to channels with this functional block, e.g. "417".'
    ] = None
    text: Annotated[
        str | None, "Case-insensitive match on the channel identifier and name."
    ] = None
    limit: Annotated[int, "Maximum number of results to return."] = 100
    offset: Annotated[int, "Number of results to skip, for pagination."] = 0


@dataclass(frozen=True)
class ChannelListResult:
    """Result of :func:`~xknxproject.mcp.tools.list_channels`."""

    channels: list[ChannelSummary]
    total_count: int
    offset: int
    next_offset: int | None
    limit_reached: bool


@dataclass(frozen=True)
class ChannelDetail:
    """
    Result of :func:`~xknxproject.mcp.tools.describe_channel`.

    ``found`` is ``False`` when the device or channel does not exist, in which
    case the remaining fields are empty.
    """

    found: bool
    channel: ChannelSummary | None
    communication_objects: list[CommunicationObjectSummary]
    group_addresses: list[str]


@dataclass(frozen=True)
class FindSimilarChannelsInput:
    """Input for :func:`~xknxproject.mcp.tools.find_similar_channels`."""

    device_address: Annotated[str, "Individual address of the reference channel's device."]
    channel_identifier: Annotated[str, 'Identifier of the reference channel, e.g. "CH-1".']
    match_functional_blocks: Annotated[
        bool, "Treat channels sharing a functional block as similar."
    ] = True
    match_module_definition: Annotated[
        bool, "Treat channels whose objects share a module definition as similar."
    ] = True


@dataclass(frozen=True)
class SimilarChannel:
    """A channel judged similar to the reference, with the reason it matched."""

    device_address: str
    identifier: str
    name: str
    functional_blocks: list[str]
    match_reason: str  # "reference", "functional_block:<id>" or "module:<definition>"


@dataclass(frozen=True)
class AlignedEntry:
    """One channel's group object at a given semantic slot."""

    device_address: str
    channel_identifier: str
    number: int
    dpas: list[str]
    group_addresses: list[str]


@dataclass(frozen=True)
class AlignedGroupObject:
    """
    A semantic slot aligned across the similar channels.

    ``key`` is the alignment key (a shared DPA, or a module ``root_number``);
    ``entries`` gives the matching group object — and its GAs — per channel.
    """

    key: str
    function_text: str
    entries: list[AlignedEntry]


@dataclass(frozen=True)
class FindSimilarChannelsResult:
    """Result of :func:`~xknxproject.mcp.tools.find_similar_channels`."""

    found: bool
    reference: ChannelSummary | None
    channels: list[SimilarChannel]
    aligned_group_objects: list[AlignedGroupObject]
