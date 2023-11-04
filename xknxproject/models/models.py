"""Define internally used data structures."""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import re

from xknxproject.models.knxproject import DPTType, ModuleInstanceInfos
from xknxproject.models.static import GroupAddressStyle, SpaceType
from xknxproject.zip import KNXProjContents

TranslationsType = dict[str, dict[str, str]]


class XMLGroupAddress:
    """Class that represents a group address."""

    def __init__(
        self,
        name: str,
        identifier: str,
        address: str,
        project_uid: int | None,
        description: str,
        dpt: DPTType | None,
        data_secure_key: str | None,
        comment: str,
        style: GroupAddressStyle,
    ):
        """Initialize a group address."""
        self.name = name
        self.identifier = identifier.split("_")[1]
        self.raw_address = int(address)
        self.project_uid = project_uid
        self.description = description
        self.dpt = dpt
        self.data_secure_key = data_secure_key  # Key as base64 encoded string or None
        self.comment = comment
        self.style = style
        self.address = XMLGroupAddress.str_address(self.raw_address, self.style)

    @staticmethod
    def str_address(raw_address: int, group_address_style: GroupAddressStyle) -> str:
        """Parse a given address and returns a string representation of it."""
        if group_address_style == GroupAddressStyle.FREE:
            return str(raw_address)
        main = (raw_address & 0b1111100000000000) >> 11
        if group_address_style == GroupAddressStyle.THREELEVEL:
            middle = (raw_address & 0b11100000000) >> 8
            sub = raw_address & 0b11111111
            return f"{main}/{middle}/{sub}"
        if group_address_style == GroupAddressStyle.TWOLEVEL:
            sub = raw_address & 0b11111111111
            return f"{main}/{sub}"
        raise ValueError(f"GroupAddressSyste '{group_address_style}' not supported!")

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"{self.address} ({self.name}) - [DPT: {self.dpt}, ID: {self.identifier}]"
        )


@dataclass
class XMLGroupRange:
    """Class that represents a group range."""

    name: str
    range_start: int
    range_end: int
    group_addresses: list[int]
    group_ranges: list[XMLGroupRange]
    comment: str
    style: GroupAddressStyle

    def str_address(self) -> str:
        """Generate a string representation for the range."""
        if self.style == GroupAddressStyle.FREE:
            return f"{self.range_start}...{self.range_end}"
        if self.style == GroupAddressStyle.TWOLEVEL:
            return XMLGroupAddress.str_address(self.range_start, self.style).split("/")[
                0
            ]
        if self.style == GroupAddressStyle.THREELEVEL:
            start_address_token = XMLGroupAddress.str_address(
                self.range_start, self.style
            ).split("/")
            if (self.range_end - self.range_start) >= 2046:
                return start_address_token[0]
            return "/".join(start_address_token[0:2])
        raise ValueError(f"GroupAddressSyste '{self.style}' not supported!")


@dataclass
class XMLArea:
    """Class that represents a area."""

    address: int
    name: str
    description: str | None
    lines: list[XMLLine]


@dataclass
class XMLLine:
    """Class that represents a Line."""

    address: int
    description: str | None
    name: str
    medium_type: str
    devices: list[DeviceInstance]
    area: XMLArea


class DeviceInstance:
    """Class that represents a device instance."""

    def __init__(
        self,
        *,
        identifier: str,
        address: int,
        project_uid: int | None,
        name: str,
        description: str,
        last_modified: str,
        product_ref: str,
        hardware_program_ref: str,
        line: XMLLine,
        manufacturer: str,
        additional_addresses: list[str],
        channels: list[ChannelNode],
        com_object_instance_refs: list[ComObjectInstanceRef],
        module_instances: list[ModuleInstance],
        com_objects: list[ComObject] | None = None,
    ):
        """Initialize a Device Instance."""
        self.identifier = identifier
        self.address = address
        self.name = name
        self.description = description
        self.project_uid = project_uid
        self.last_modified = last_modified
        self.product_ref = product_ref
        self.hardware_program_ref = hardware_program_ref
        self.line = line
        self.area_address = line.area.address  # used for sorting
        self.line_address = line.address  # used for sorting
        self.manufacturer = manufacturer
        self.additional_addresses = additional_addresses
        self.channels: list[ChannelNode] = channels
        self.com_object_instance_refs = com_object_instance_refs
        self.module_instances = module_instances
        self.com_objects = com_objects or []
        self.application_program_ref: str | None = None

        self.individual_address = (
            f"{self.area_address}.{self.line_address}.{self.address}"
        )
        self.product_name: str = ""
        self.hardware_name: str = ""
        self.manufacturer_name: str = ""

    def add_additional_address(self, address: str) -> None:
        """Add an additional individual address."""
        self.additional_addresses.append(
            f"{self.line.area.address}/{self.line.address}/{address}"
        )

    def application_program_xml(self) -> str:
        """Obtain the file name to the application program XML."""
        return f"{self.manufacturer}/{self.application_program_ref}.xml"

    def module_instance_arguments(self) -> Iterator[ModuleInstanceArgument]:
        """Iterate ModuleInstance arguments."""
        for _module_instance in self.module_instances:
            yield from _module_instance.arguments

    def _complete_channel_placeholders(self) -> None:
        """Replace placeholders in channel names with module instance arguments."""
        for channel in self.channels:
            if not (
                channel.ref_id.startswith("MD-")  # only applicable if modules used
                and "{{" in channel.name  # placeholders are denoted "{{name}}"
            ):
                continue

            module_instance_ref = channel.ref_id.split("_CH")[0]
            module_instance = next(
                mi
                for mi in self.module_instances
                if mi.identifier == module_instance_ref
            )
            for argument in module_instance.arguments:
                channel.name = channel.name.replace(
                    f"{{{{{argument.name}}}}}", argument.value
                )

    def apply_module_instance_arguments(self) -> None:
        """Apply module instance arguments."""
        self._complete_channel_placeholders()
        for coir in self.com_object_instance_refs:
            coir.apply_module_base_number_argument(self.module_instances)


@dataclass
class ChannelNode:
    """Class that represents a Node with Type Channel."""

    ref_id: str
    name: str


@dataclass
class ModuleInstance:
    """Class that represents a ModuleInstance."""

    identifier: str
    ref_id: str
    arguments: list[ModuleInstanceArgument]


@dataclass
class ModuleInstanceArgument:
    """Class that represents a ModuleInstance Argument."""

    ref_id: str
    value: str
    name: str = ""  # resolved from application by `ref_id` ModuleDefs/ModuleDef/Arguments/Argument

    def complete_ref_id(self, application_program_ref: str) -> None:
        """Prepend the ref_id with the application program ref."""
        self.ref_id = f"{application_program_ref}_{self.ref_id}"


@dataclass
class ComObjectInstanceRef:
    """Class that represents a ComObjectInstanceRef instance."""

    identifier: str | None  # "Id" - xs:ID
    # "RefId" - knx:RELIDREF - required - points to a ComObjectRef Id
    # initially stripped by the devices application_program_ref
    ref_id: str
    text: str | None  # "Text"
    function_text: str | None  # "FunctionText"
    read_flag: bool | None  # "ReadFlag" - knx:Enable_t
    write_flag: bool | None  # "WriteFlag" - knx:Enable_t
    communication_flag: bool | None  # "CommunicationFlag" - knx:Enable_t
    transmit_flag: bool | None  # "TransmitFlag" - knx:Enable_t
    update_flag: bool | None  # "UpdateFlag" - knx:Enable_t
    read_on_init_flag: bool | None  # "ReadOnInitFlag" - knx:Enable_t
    datapoint_types: list[DPTType]  # "DataPointType" - knx:IDREFS
    description: str | None  # "Description" - language dependent
    channel: str | None  # "ChannelId" - knx:IDREFS
    links: list[str] | None  # "Links" - knx:RELIDREFS

    # resolved via Hardware.xml from the containing DeviceInstance
    com_object_ref_id: str | None = None

    # only available form ComObject and ComObjectRef
    name: str | None = None
    object_size: str | None = None
    # only available form ComObject
    base_number_argument_ref: str | None = None  # optional in ComObject
    number: int | None = None  # required in ComObject
    # assigned when module arguments are applied
    module: ModuleInstanceInfos | None = None

    def resolve_com_object_ref_id(
        self, application_program_ref: str, knx_proj_contents: KNXProjContents
    ) -> None:
        """Prepend the ref_id with the application program ref."""
        # Remove module and ModuleInstance occurrence as they will not be in the application program directly
        ref_id = re.sub(r"(M-\d+?_MI-\d+?_)", "", self.ref_id)
        if knx_proj_contents.is_ets4_project():
            self.com_object_ref_id = ref_id
        else:
            self.com_object_ref_id = f"{application_program_ref}_{ref_id}"

    def merge_from_application(self, com_object: ComObject | ComObjectRef) -> None:
        """Fill missing information with information parsed from the application program."""
        if self.name is None:
            self.name = com_object.name
        if self.text is None:
            self.text = com_object.text
        if self.function_text is None:
            self.function_text = com_object.function_text
        if self.object_size is None:
            self.object_size = com_object.object_size
        if self.read_flag is None:
            self.read_flag = com_object.read_flag
        if self.write_flag is None:
            self.write_flag = com_object.write_flag
        if self.communication_flag is None:
            self.communication_flag = com_object.communication_flag
        if self.transmit_flag is None:
            self.transmit_flag = com_object.transmit_flag
        if self.update_flag is None:
            self.update_flag = com_object.update_flag
        if self.read_on_init_flag is None:
            self.read_on_init_flag = com_object.read_on_init_flag
        if not self.datapoint_types:
            self.datapoint_types = com_object.datapoint_types
        if isinstance(com_object, ComObject):
            self.number = com_object.number
            self.base_number_argument_ref = com_object.base_number_argument_ref

    def apply_module_base_number_argument(
        self, module_instances: list[ModuleInstance]
    ) -> None:
        """Apply module argument of base number."""
        if (
            self.base_number_argument_ref is None
            or not self.ref_id.startswith("MD-")
            or self.number is None  # only for type safety
        ):
            return
        _module_instance = next(
            mi for mi in module_instances if self.ref_id.startswith(f"{mi.identifier}_")
        )
        root_number = self.number
        self.number += next(
            int(arg.value)
            for arg in _module_instance.arguments
            if arg.ref_id == self.base_number_argument_ref
        )
        self.module = ModuleInstanceInfos(
            definition=self.ref_id.split("_")[0],
            root_number=root_number,
        )


@dataclass
class ComObject:
    """Class that represents a ComObject instance."""

    __slots__ = (
        "identifier",
        "name",
        "text",
        "number",
        "function_text",
        "object_size",
        "read_flag",
        "write_flag",
        "communication_flag",
        "transmit_flag",
        "update_flag",
        "read_on_init_flag",
        "datapoint_types",
        "base_number_argument_ref",
    )

    # all items required in the XML
    identifier: str  # "Id" - xs:ID
    name: str  # "Name"
    text: str  # "Text" - language dependent
    number: int  # "Number" - xs:unsignedInt
    function_text: str  # "FunctionText" - language dependent
    object_size: str  # "ObjectSize" - knx:ComObjectSize_t
    read_flag: bool  # "ReadFlag" - knx:Enable_t
    write_flag: bool  # "WriteFlag" - knx:Enable_t
    communication_flag: bool  # "CommunicationFlag" - knx:Enable_t
    transmit_flag: bool  # "TransmitFlag" - knx:Enable_t
    update_flag: bool  # "UpdateFlag" - knx:Enable_t
    read_on_init_flag: bool  # "ReadOnInitFlag" - knx:Enable_t
    datapoint_types: list[DPTType]  # "DataPointType" - knx:IDREFS - optional
    # "BaseNumber" - knx:IDREF - optional - schema version >= 20
    # ModuleArgument identifier that holds value to add for
    # communication object number of ComObjectInstanceRef
    base_number_argument_ref: str | None


@dataclass
class ComObjectRef:
    """Class that represents a ComObjectRef instance."""

    __slots__ = (
        "identifier",
        "ref_id",
        "name",
        "text",
        "function_text",
        "object_size",
        "read_flag",
        "write_flag",
        "communication_flag",
        "transmit_flag",
        "update_flag",
        "read_on_init_flag",
        "datapoint_types",
    )

    identifier: str  # "Id" - xs:ID - required
    ref_id: str  # "RefId" - knx:IDREF - required - points to a ComObject Id
    name: str | None  # "Name"
    text: str | None  # "Text" - language dependent
    function_text: str | None  # "FunctionText" - language dependent
    object_size: str | None  # "ObjectSize" - knx:ComObjectSize_t
    read_flag: bool | None  # "ReadFlag" - knx:Enable_t
    write_flag: bool | None  # "WriteFlag" - knx:Enable_t
    communication_flag: bool | None  # "CommunicationFlag" - knx:Enable_t
    transmit_flag: bool | None  # "TransmitFlag" - knx:Enable_t
    update_flag: bool | None  # "UpdateFlag" - knx:Enable_t
    read_on_init_flag: bool | None  # "ReadOnInitFlag" - knx:Enable_t
    datapoint_types: list[DPTType]  # "DataPointType" - knx:IDREFS


@dataclass
class KNXMasterData:
    """KNX Master data needed for parsing other project files."""

    function_type_names: dict[str, str]
    manufacturer_names: dict[str, str]
    space_usage_mapping: dict[str, str]
    translations: TranslationsType

    def _get_translation_item(
        self, ref_id: str, attribute_name: str = "Text"
    ) -> str | None:
        """Get translation item from the translations dict."""
        if self.translations:
            try:
                return self.translations[ref_id][attribute_name]
            except KeyError:
                return None
        return None

    def get_function_type_name(self, function_type_id: str) -> str:
        """Get space usage name from space usage id."""
        if translated := self._get_translation_item(function_type_id):
            return translated
        return self.function_type_names.get(function_type_id, "")

    def get_space_usage_name(self, space_usage_id: str) -> str:
        """Get space usage name from space usage id."""
        if translated := self._get_translation_item(space_usage_id):
            return translated
        return self.space_usage_mapping.get(space_usage_id, "")


@dataclass
class XMLSpace:
    """A space in the location XML."""

    identifier: str
    name: str
    space_type: SpaceType
    usage_id: str | None  # SU-<int> resolved from knx_master.xml (with translation)
    usage_text: str  # default to "" - translated
    number: str  # default to ""
    description: str  # default to ""
    project_uid: int | None
    spaces: list[XMLSpace]
    devices: list[str]  # [DeviceInstance.individual_address]
    functions: list[str]


@dataclass
class XMLFunction:
    """A functions in the space XML."""

    function_type: str
    group_addresses: list[XMLGroupAddressRef]
    identifier: str
    name: str
    project_uid: int | None
    space_id: str
    usage_text: str


@dataclass
class XMLGroupAddressRef:
    """A GroupAddressRef in the functions XML."""

    address: str
    identifier: str
    name: str
    project_uid: int | None
    ref_id: str
    role: str


@dataclass
class Product:
    """Model a Product instance."""

    identifier: str
    text: str
    hardware_name: str = ""


HardwareToPrograms = dict[str, str]


@dataclass
class XMLProjectInformation:
    """Model a ProjectInformation instance."""

    # ProjectInformation tag is not required in XSD, thus everything is optional
    project_id: str = ""
    name: str = ""
    last_modified: str | None = None
    group_address_style: GroupAddressStyle = GroupAddressStyle.THREELEVEL
    guid: str = ""
    created_by: str = ""
    schema_version: str = ""
    tool_version: str = ""
