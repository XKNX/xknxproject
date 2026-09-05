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
    module_def: ModuleInstanceInfos | None
    channel: str | None
    dpts: list[DPTType]
    object_size: str
    group_address_links: list[str]
    flags: Flags
    dpas: list[str] | None


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
    serial_number: str
    last_download: str | None
    individual_address_loaded: bool
    application_program_loaded: bool
    communication_part_loaded: bool
    medium_config_loaded: bool
    parameters_loaded: bool


class Channel(TypedDict):
    """Channel typed dict."""

    identifier: str
    name: str
    communication_object_ids: list[str]
    functional_blocks: list[str] | None


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


class ProductComObject(TypedDict):
    """
    A communication object of a product application program.

    Values are the ComObjectRef merged onto its base ComObject (ref wins).
    """

    identifier: str
    number: int
    name: str
    text: str
    function_text: str
    object_size: str
    dpts: list[DPTType]
    flags: Flags


class ProductParameter(TypedDict):
    """
    An application parameter of a product application program.

    ``value`` and ``text`` are the effective defaults: overrides of the
    parameters (single) ParameterRef win over the Parameter itself.
    """

    identifier: str
    name: str | None
    text: str | None
    value: str | None  # default value
    segment: str | None  # segment id; None if not stored in memory
    offset: int | None  # octet offset within the segment
    bit_offset: int | None
    size_in_bit: int | None
    type: str  # ParameterType restriction kind
    base: str | None
    minimum: int | float | None
    maximum: int | float | None
    enumerations: dict[int, str]


class ProductSegment(TypedDict):
    """A memory segment of a product application program."""

    identifier: str
    kind: str  # "relative" | "absolute"
    size: int | None
    object_index: int | None  # RelativeSegment LoadStateMachine
    offset: int | None
    address: int | None
    memory_type: str | None


class ProductApplicationProgram(TypedDict):
    """A parsed application program from a product database."""

    identifier: str
    name: str
    application_number: int
    application_version: int
    mask_version: str
    pei_type: int | None
    communication_objects: list[ProductComObject]
    parameters: list[ProductParameter]
    segments: list[ProductSegment]


class KNXProduct(TypedDict):
    """Top-level result of parsing a ``.knxprod`` product database."""

    manufacturer: str
    schema_version: int
    application_programs: dict[str, ProductApplicationProgram]
