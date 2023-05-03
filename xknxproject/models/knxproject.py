"""Define output type for parsed KNX project."""
from __future__ import annotations

from typing import TypedDict


class DPTType(TypedDict):
    """DPT type dictionary."""

    main: int
    sub: int | None


class Flags(TypedDict):
    """Flags for the group addresses and KOs."""

    read: bool
    write: bool
    communication: bool
    transmit: bool
    update: bool
    read_on_init: bool


class CommunicationObject(TypedDict):
    """Communication object dictionary."""

    name: str
    number: int
    text: str
    function_text: str
    description: str
    device_address: str
    dpts: list[DPTType]
    object_size: str
    group_address_links: list[str]
    flags: Flags


class Device(TypedDict):
    """Devices dictionary."""

    name: str
    hardware_name: str
    description: str
    manufacturer_name: str
    individual_address: str
    project_uid: int
    communication_object_ids: list[str]


class Line(TypedDict):
    """Line typed dict."""

    name: str
    medium_type: str
    description: str | None
    devices: list[str]


class Area(TypedDict):
    """Area typed dict."""

    name: str
    description: str | None
    lines: dict[str, Line]


class GroupAddress(TypedDict):
    """GroupAddress typed dict."""

    name: str
    identifier: str
    raw_address: int
    address: str
    project_uid: int
    dpt: DPTType | None
    communication_object_ids: list[str]
    description: str


class Space(TypedDict):
    """Space typed dict."""

    type: str
    identifier: str
    name: str
    usage_id: str | None
    usage_text: str
    number: str
    description: str
    project_uid: int
    devices: list[str]
    spaces: dict[str, Space]


class ProjectInfo(TypedDict):
    """Information about the project."""

    project_id: str
    name: str
    last_modified: str | None
    group_address_style: str
    guid: str
    created_by: str
    schema_version: str
    tool_version: str
    xknxproject_version: str
    language_code: str | None


class KNXProject(TypedDict):
    """KNXProject typed dictionary."""

    info: ProjectInfo
    communication_objects: dict[str, CommunicationObject]
    devices: dict[str, Device]
    topology: dict[str, Area]
    locations: dict[str, Space]
    group_addresses: dict[str, GroupAddress]
