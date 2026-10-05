"""
Define output types for application program definitions.

Definitions describe what an application program offers, not what a project
instantiates (see `knxproject.py`). Identifiers are relative to the application
program id with module instance parts removed;
`xknxproject.util.instance_definition_id()` maps instance ids of `parse()` to
them.
"""

from __future__ import annotations

from typing import TypedDict

from xknxproject.models.knxproject import DPTType, Flags


class ProductInfo(TypedDict):
    """A product of the project using an application program."""

    # Product "Id" - "M-0064_H-SpaceLogic.20KNX.20Switch.20Secure-1_P-MTN6705.2D0008S"
    product_id: str
    hardware_id: str  # Hardware "Id" - "M-0064_H-SpaceLogic.20KNX.20Switch.20Secure-1"
    hardware_program_id: str  # Hardware2Program "Id" - "M-0064_H-..._HP-5810-12-2E9D"
    hardware_name: str  # Hardware "Name" - not translated
    text: str  # Product "Text" - translated product name
    order_number: str  # Product "OrderNumber"


class ApplicationProgramIdentity(TypedDict):
    """Identity of an application program."""

    application_id: str  # "M-0064_A-5810-12-2E9D" or "M-0008_A-20E0-21-9997-O000A"
    # manufacturer part of the id; for OEM programs the selling manufacturer
    manufacturer_id: str  # "M-0064"
    manufacturer_name: str  # from knx_master.xml
    # OEM programs: "M-000A" - from the program attribute, else the "-Oxxxx" id
    # suffix, else the Hardware of a device using the program; None otherwise
    original_manufacturer_id: str | None
    application_number: int | None  # "ApplicationNumber" - None if missing or invalid
    application_version: int | None  # "ApplicationVersion" - None if missing or invalid
    name: str  # "Name" - translated
    mask_version: str  # "MaskVersion" - "MV-07B0"
    program_hash: str | None  # "Hash" - base64
    # "92.60" from the KIM header of the program's Semantics attribute, else None
    kim_version: str | None
    # products of this project using the program, in device order
    products: list[ProductInfo]


class ChannelDefinition(TypedDict):
    """
    A Channel of an application program (definition, not instance).

    A Channel defined in a ModuleDef exists once per module instance in a
    project; all instances share this definition.
    """

    identifier: str  # "CH-1" or "MD-2_CH-1" - relative to the application program
    name: str  # "Name" - not translated
    # "Text" - translated; may contain unresolved "{{0}}" text parameter and
    # "{{ChNo}}" module argument placeholders
    text: str | None
    number: str  # "Number"
    functional_blocks: list[str] | None  # from "Semantics": ["417"]
    module_definition_id: str | None  # "MD-2" when defined inside a ModuleDef
    # ObjectDefinition identifiers referenced anywhere in the channel (all
    # choose/when branches) in order of first appearance, followed by those of the
    # modules instantiated inside the channel (also through sub-modules) in the
    # order of the channel's Module elements
    object_ids: list[str]


class ModuleDefinition(TypedDict):
    """A ModuleDef or SubModuleDef of an application program."""

    identifier: str  # "MD-2", or "MD-4_SM-1" for a sub-module of MD-4
    name: str  # "Name"
    channel_ids: list[str]  # channels defined inside the module, not its placements


class ObjectDefinition(TypedDict):
    """
    A ComObjectRef merged with its ComObject (definition, not instance).

    Attributes set on the ComObjectRef override those of the ComObject.
    """

    identifier: str  # ComObjectRef id - "O-1_R-1" or "MD-2_O-2-35_R-65"
    com_object_id: str  # ComObject id - "O-1" or "MD-2_O-2-35"
    number: int  # ComObject "Number"; inside modules without the module base number
    name: str  # not translated
    text: str  # translated; may contain unresolved "{{0}}" placeholders
    function_text: str  # translated
    object_size: str  # "1 Bit"
    dpts: list[DPTType]  # empty when neither the ref nor the ComObject sets one
    flags: Flags
    dpas: list[str] | None  # from the ComObjectRef "Semantics": ["417.52"]
    # channels referencing this object, directly or through module instantiation
    channel_ids: list[str]


class ApplicationProgramDefinition(TypedDict):
    """Full definition of one application program."""

    identity: ApplicationProgramIdentity
    channels: dict[str, ChannelDefinition]  # key: ChannelDefinition identifier
    modules: dict[str, ModuleDefinition]  # key: ModuleDefinition identifier
    objects: dict[str, ObjectDefinition]  # key: ObjectDefinition identifier
    # ObjectDefinition identifiers outside any channel, in document order
    channel_independent_object_ids: list[str]


class ApplicationProgramsInfo(TypedDict):
    """Information about the application program definitions of a project."""

    # language of the texts, resolved like `ProjectInfo["language_code"]`
    # ("De" -> "de-DE"); None without a requested or matching language. Texts a
    # program does not translate to it keep the program's default language.
    language_code: str | None
    xknxproject_version: str


class ApplicationPrograms(TypedDict):
    """Application program definitions of a project, `XKNXProj.parse_application_programs()`."""

    info: ApplicationProgramsInfo
    # key: application program id, the same as `Device["application"]` of `parse()`
    application_programs: dict[str, ApplicationProgramDefinition]
