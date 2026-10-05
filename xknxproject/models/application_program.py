"""Define output type for parsed application programs."""

from __future__ import annotations

from typing import TypedDict

from xknxproject.models.knxproject import DPTType, Flags


class ProductInfo(TypedDict):
    """A product of the project using an application program."""

    product_id: str  # "M-0064_H-SpaceLogic.20KNX.20Switch.20Secure-1_P-MTN6705.2D0008S"
    hardware_id: str  # "M-0064_H-SpaceLogic.20KNX.20Switch.20Secure-1"
    hardware_program_id: str  # "M-0064_H-..._HP-5810-12-2E9D"
    hardware_name: str  # untranslated name from hardware.xml
    text: str  # translated product name
    order_number: str


class ApplicationProgramIdentity(TypedDict):
    """Identity of an application program."""

    application_id: str  # "M-0064_A-5810-12-2E9D" or "M-0008_A-20E0-21-9997-O000A"
    manufacturer_id: str  # "M-0064"
    manufacturer_name: str
    original_manufacturer_id: str | None  # "M-000A" for OEM programs, else None
    application_number: int | None  # ApplicationNumber attribute
    application_version: int | None  # ApplicationVersion attribute
    name: str
    mask_version: str  # "MV-07B0"
    program_hash: str | None  # Hash attribute (base64)
    # "92.60" from the KIM header of the program's Semantics attribute, else None
    kim_version: str | None
    products: list[ProductInfo]  # products of this project using the program


class ChannelDefinition(TypedDict):
    """A channel of an application program (definition, not instance)."""

    identifier: str  # "CH-1" or "MD-2_CH-1" - relative to the application program
    name: str
    text: str | None  # may contain "{{0}}" text parameter placeholders
    number: str
    functional_blocks: list[str] | None
    module_definition_id: str | None  # "MD-2" when defined inside a ModuleDef
    # ObjectDefinition identifiers in order of first appearance, followed by those
    # of the modules instantiated inside the channel (also through sub-modules)
    object_ids: list[str]


class ModuleDefinition(TypedDict):
    """A module definition of an application program."""

    identifier: str  # "MD-2" or "MD-4_SM-1"
    name: str
    channel_ids: list[str]  # channels defined inside the module, not its placements


class ObjectDefinition(TypedDict):
    """A ComObjectRef merged with its ComObject (definition, not instance)."""

    identifier: str  # "O-1_R-1" or "MD-2_O-2-35_R-65"
    com_object_id: str  # "O-1" or "MD-2_O-2-35"
    number: int  # ComObject number before any module base number is added
    name: str
    text: str
    function_text: str
    object_size: str
    dpts: list[DPTType]
    flags: Flags
    dpas: list[str] | None
    # channels referencing this object, directly or through module instantiation
    channel_ids: list[str]


class ApplicationProgramDefinition(TypedDict):
    """Full definition of one application program."""

    identity: ApplicationProgramIdentity
    channels: dict[str, ChannelDefinition]
    modules: dict[str, ModuleDefinition]
    objects: dict[str, ObjectDefinition]
    channel_independent_object_ids: list[str]
    language_code: str | None
    xknxproject_version: str


ApplicationPrograms = dict[str, ApplicationProgramDefinition]  # key: application_id
