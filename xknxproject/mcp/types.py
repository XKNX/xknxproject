"""
Input/output dataclasses for the xknxproject MCP tools.

All fields are JSON-native, so a consumer can build inputs directly from tool
arguments and serialise outputs with :func:`dataclasses.asdict` without custom
encoders. DPTs are rendered as ``"main"`` or ``"main.sub"`` strings.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GroupAddressFilter:
    """
    Filters for :func:`~xknxproject.mcp.tools.list_group_addresses`.

    ``text`` matches case-insensitively against the address, name, description
    and comment. ``dpts`` accept ``"main"`` or ``"main.sub"`` strings; a bare
    main matches every subtype. Within a category values are OR-ed.
    """

    text: str | None = None
    dpts: list[str] = field(default_factory=list)
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class DeviceFilter:
    """
    Filters for :func:`~xknxproject.mcp.tools.list_devices`.

    ``text`` matches case-insensitively against the individual address, name,
    hardware name, manufacturer and order number.
    """

    text: str | None = None
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class CommunicationObjectFilter:
    """
    Filters for :func:`~xknxproject.mcp.tools.list_communication_objects`.

    Set ``device_address`` to restrict to one device's objects, and/or
    ``group_address`` to only objects linked to that GA. ``text`` matches
    case-insensitively against the name, text, function text and description.
    """

    device_address: str | None = None
    group_address: str | None = None
    text: str | None = None
    limit: int = 100
    offset: int = 0


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
    limit_reached: bool


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


@dataclass(frozen=True)
class CommunicationObjectListResult:
    """Result of :func:`~xknxproject.mcp.tools.list_communication_objects`."""

    communication_objects: list[CommunicationObjectSummary]
    total_count: int
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
class DeviceSummary:
    """A JSON-serialisable view of a topology device."""

    individual_address: str
    name: str
    hardware_name: str
    manufacturer_name: str
    order_number: str
    description: str
    communication_object_ids: list[str]


@dataclass(frozen=True)
class DeviceListResult:
    """Result of :func:`~xknxproject.mcp.tools.list_devices`."""

    devices: list[DeviceSummary]
    total_count: int
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
