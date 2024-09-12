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
    device_application: str | None
    module: ModuleInstanceInfos | None
    channel: str | None
    dpts: list[DPTType]
    object_size: str
    group_address_links: list[str]
    flags: Flags


class ModuleInstanceInfos(TypedDict):
    """Information about module association for CommunicationObjects."""

    definition: str
    root_number: (
        int  # `Number` assigned by ComObject - without Module base object number added
    )


class Device(TypedDict):
    """Devices dictionary."""

    name: str
    hardware_name: str
    order_number: str
    description: str
    manufacturer_name: str
    individual_address: str
    application: str | None
    project_uid: int | None
    communication_object_ids: list[str]
    channels: dict[str, Channel]  # id: Channel


class Channel(TypedDict):
    """Channel typed dict."""

    identifier: str
    name: str
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
    project_uid: int | None
    dpt: DPTType | None
    data_secure: bool
    communication_object_ids: list[str]
    description: str
    comment: str


class GroupRange(TypedDict):
    """GroupRange holding the actual GAs but no children (e.g. 'middle' in THREELEVEL)."""

    name: str
    address_start: int
    address_end: int
    comment: str
    group_addresses: list[str]
    group_ranges: dict[str, GroupRange]


class Space(TypedDict):
    """Space typed dict."""

    type: str
    identifier: str
    name: str
    usage_id: str | None
    usage_text: str
    number: str
    description: str
    project_uid: int | None
    devices: list[str]
    spaces: dict[str, Space]
    functions: list[str]


class Function(TypedDict):
    """Function typed dict."""

    function_type: str
    group_addresses: dict[str, GroupAddressRef]
    identifier: str
    name: str
    project_uid: int | None
    space_id: str
    usage_text: str


class GroupAddressRef(TypedDict):
    """GroupAddressRef typed dict."""

    address: str
    name: str
    project_uid: int | None
    role: str


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
    group_ranges: dict[str, GroupRange]
    functions: dict[str, Function]
