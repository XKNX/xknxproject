"""Project file loader."""

from __future__ import annotations

import re
from xml.etree import ElementTree

from xknxproject.const import ETS_5_7_SCHEMA_VERSION
from xknxproject.exceptions import UnexpectedDataError
from xknxproject.models import (
    ChannelNode,
    ComObjectInstanceRef,
    DeviceInstance,
    GroupAddressStyle,
    KNXMasterData,
    ModuleInstance,
    ModuleInstanceArgument,
    ParameterInstanceRef,
    SpaceType,
    XMLArea,
    XMLFunction,
    XMLGroupAddress,
    XMLGroupAddressRef,
    XMLGroupRange,
    XMLLine,
    XMLProjectInformation,
    XMLSpace,
)
from xknxproject.util import get_dpt_type, parse_dpt_types, parse_xml_flag
from xknxproject.zip import KNXProjContents


class ProjectLoader:
    """Load Project file."""

    @staticmethod
    def load(
        knx_proj_contents: KNXProjContents,
        knx_master_data: KNXMasterData,
    ) -> tuple[
        list[XMLGroupAddress],
        list[XMLGroupRange],
        list[XMLArea],
        list[DeviceInstance],
        list[XMLSpace],
        XMLProjectInformation,
        list[XMLFunction],
    ]:
        """Load topology mappings."""
        areas: list[XMLArea] = []
        devices: list[DeviceInstance] = []
        group_address_list: list[XMLGroupAddress] = []
        group_range_list: list[XMLGroupRange] = []
        spaces: list[XMLSpace] = []
        functions: list[XMLFunction] = []

        with knx_proj_contents.open_project_meta() as project_file:
            tree = ElementTree.parse(project_file)
            project_info = load_project_info(tree)

        with knx_proj_contents.open_project_0() as project_0_file:
            tree = ElementTree.parse(project_0_file)
            for ga_element in tree.findall(
                # `//` to ignore <GroupRange> tags to support different GA level formats
                "{*}Project/{*}Installations/{*}Installation/{*}GroupAddresses//{*}GroupAddress"
            ):
                group_address_list.append(
                    _GroupAddressLoader.load(
                        group_address_element=ga_element,
                        group_address_style=project_info.group_address_style,
                    ),
                )
            for ga_range_l1 in tree.findall(
                "{*}Project/{*}Installations/{*}Installation/{*}GroupAddresses/{*}GroupRanges/{*}GroupRange"
            ):
                group_range_list.append(
                    _GroupAddressRangeLoader.load(
                        ga_range_l1, project_info.group_address_style
                    )
                )
            topology_loader = _TopologyLoader(knx_proj_contents)
            for topology_element in tree.findall(
                "{*}Project/{*}Installations/{*}Installation/{*}Topology"
            ):
                areas.extend(topology_loader.load(topology_element=topology_element))
            for area in areas:
                for line in area.lines:
                    devices.extend(line.devices)

            # ETS4 has a different naming for locations than ETS5/6
            element_name = (
                "Buildings" if knx_proj_contents.is_ets4_project() else "Locations"
            )

            location_loader = _LocationLoader(
                knx_proj_contents,
                knx_master_data,
                devices,
            )
            for location_element in tree.findall(
                f"{{*}}Project/{{*}}Installations/{{*}}Installation/{{*}}{element_name}"
            ):
                spaces.extend(
                    location_loader.load(
                        location_element=location_element, functions=functions
                    )
                )

        for function in functions:
            function.usage_text = (
                knx_master_data.get_function_type_name(function.function_type)
                if function.function_type
                else ""
            )

            for group_address in function.group_addresses:
                try:
                    group_address.address = next(
                        ga.address
                        for ga in group_address_list
                        if ga.identifier == group_address.ref_id
                    )
                except StopIteration:
                    raise UnexpectedDataError(
                        f"Group address {group_address.ref_id} referred in function not found"
                    ) from None

        return (
            group_address_list,
            group_range_list,
            areas,
            devices,
            spaces,
            project_info,
            functions,
        )


class _GroupAddressLoader:
    """Load GroupAddress info from KNX XML."""

    @staticmethod
    def load(
        group_address_element: ElementTree.Element,
        group_address_style: GroupAddressStyle,
    ) -> XMLGroupAddress:
        """Load GroupAddress mappings."""
        project_uid = group_address_element.get("Puid")
        return XMLGroupAddress(
            name=group_address_element.get("Name", ""),
            identifier=group_address_element.get("Id", ""),
            address=group_address_element.get("Address", ""),
            project_uid=int(project_uid) if project_uid else None,
            description=group_address_element.get("Description", ""),
            dpt=get_dpt_type(group_address_element.get("DatapointType")),
            data_secure_key=group_address_element.get("Key"),
            comment=group_address_element.get("Comment", ""),
            style=group_address_style,
        )


class _GroupAddressRangeLoader:
    """Load information of GroupAddress levels (GroupRange)."""

    @staticmethod
    def load(
        group_range_element: ElementTree.Element, group_address_style: GroupAddressStyle
    ) -> XMLGroupRange:
        """Load GroupRange."""

        def create_xml_group_range(elem: ElementTree.Element) -> XMLGroupRange:
            group_range_elems = elem.findall("./{*}GroupRange")
            group_ranges = [
                create_xml_group_range(range_elem) for range_elem in group_range_elems
            ]

            return XMLGroupRange(
                name=elem.get("Name", ""),
                range_start=int(elem.get("RangeStart")),  # type: ignore[arg-type]
                range_end=int(elem.get("RangeEnd")),  # type: ignore[arg-type]
                group_addresses=[
                    int(e.attrib["Address"]) for e in elem.findall("{*}GroupAddress")
                ],
                group_ranges=group_ranges,
                comment=elem.get("Comment", ""),
                style=group_address_style,
            )

        return create_xml_group_range(group_range_element)


class _TopologyLoader:
    """Load topology from KNX XML."""

    def __init__(self, knx_proj_contents: KNXProjContents) -> None:
        self.__knx_proj_contents = knx_proj_contents

    def load(self, topology_element: ElementTree.Element) -> list[XMLArea]:
        """Load topology mappings."""
        areas: list[XMLArea] = []

        for area in topology_element.findall("{*}Area"):
            areas.append(self._create_area(area))

        return areas

    def _create_area(self, area_element: ElementTree.Element) -> XMLArea:
        """Create an Area."""
        address: int = int(area_element.get("Address", ""))
        name: str = area_element.get("Name", "")
        description: str | None = area_element.get("Description")
        area: XMLArea = XMLArea(address, name, description, [])

        for line_element in area_element:
            area.lines.append(self._create_line(line_element, area))

        return area

    def _create_line(self, line_element: ElementTree.Element, area: XMLArea) -> XMLLine:
        """Create a Line."""
        address: int = int(line_element.get("Address", ""))
        name: str = line_element.get("Name", "")
        description: str | None = line_element.get("Description")
        if (segment := line_element.find("{*}Segment")) is not None:
            #  ETS-6 (21) adds "Segment" tags between "Line" and "DeviceInstance" tags
            medium_type = segment.get("MediumTypeRefId", "")
        else:
            medium_type = line_element.get("MediumTypeRefId", "")
        line: XMLLine = XMLLine(address, description, name, medium_type, [], area)

        for device_element in line_element.findall(".//{*}DeviceInstance"):
            if device := self._create_device(device_element, line):
                line.devices.append(device)

        return line

    def _create_device(
        self, device_element: ElementTree.Element, line: XMLLine
    ) -> DeviceInstance | None:
        """Create device."""
        address: str | None = device_element.get("Address")
        #  devices like power supplies do usually not have an IA.
        if address is None:
            return None

        project_uid = device_element.get("Puid")
        product_ref = device_element.get("ProductRefId", "")

        additional_addresses = [
            add_addr
            for address_elem in device_element.findall(
                "{*}AdditionalAddresses/{*}Address"
            )
            if (add_addr := address_elem.get("Address")) is not None
        ]

        com_obj_inst_refs = [
            com_obj_inst_ref
            for elem in device_element.findall(
                "{*}ComObjectInstanceRefs/{*}ComObjectInstanceRef"
            )
            if (com_obj_inst_ref := self._create_com_object_instance(elem)) is not None
        ]

        module_instances = [
            module_instance
            for mi_elem in device_element.findall(
                "{*}ModuleInstances/{*}ModuleInstance"
            )
            if (module_instance := self._create_module_instance(mi_elem)) is not None
        ]

        channels = []
        for channel_node_elem in device_element.findall(
            "{*}GroupObjectTree//{*}Nodes/{*}Node[@Type='Channel']"
        ):
            if not (_gos := channel_node_elem.get("GroupObjectInstances")):
                # parse only used channels
                continue
            channels.append(
                ChannelNode(
                    ref_id=channel_node_elem.get("RefId"),  # type: ignore[arg-type]
                    name=channel_node_elem.get("Text", ""),
                    group_object_instances=_gos.split(" "),
                )
            )

        parameter_instances = {}
        for param_instance_node in device_element.findall(
            "{*}ParameterInstanceRefs/{*}ParameterInstanceRef"
        ):
            pr_ref_id: str = param_instance_node.get("RefId")  # type: ignore[assignment]
            parameter_instances[pr_ref_id] = ParameterInstanceRef(
                ref_id=pr_ref_id,
                value=param_instance_node.get("Value"),
            )

        return DeviceInstance(
            identifier=device_element.get("Id", ""),
            address=int(address),
            project_uid=int(project_uid) if project_uid else None,
            name=device_element.get("Name", ""),
            description=device_element.get("Description", ""),
            last_modified=device_element.get("LastModified", ""),
            product_ref=product_ref,
            hardware_program_ref=device_element.get("Hardware2ProgramRefId", ""),
            line=line,
            manufacturer=product_ref.split("_", 1)[0],
            additional_addresses=additional_addresses,
            channels=channels,
            com_object_instance_refs=com_obj_inst_refs,
            module_instances=module_instances,
            parameter_instance_refs=parameter_instances,
        )

    @staticmethod
    def __get_links_from_schema_1x(com_object: ElementTree.Element) -> list[str]:
        # Check if "Connectors" is available. Schema version <= 14
        if (connectors := com_object.find("{*}Connectors")) is None:
            return []

        # Send GA is the primary GA, Receive GA are additional group addresses
        ga_list = connectors.findall("{*}Send") + connectors.findall("{*}Receive")

        # Remove the project ID from GA
        return [
            ga.get("GroupAddressRefId", "").split("_", maxsplit=1)[1] for ga in ga_list
        ]

    @staticmethod
    def __get_links_from_schema_2x(com_object: ElementTree.Element) -> list[str]:
        # ETS 5.7+ / 6 uses a space-separated string of GA
        links = com_object.get("Links")

        if links is None:
            return []

        return links.split(" ")

    def _create_com_object_instance(
        self,
        com_object: ElementTree.Element,
    ) -> ComObjectInstanceRef | None:
        """Create ComObjectInstanceRef."""

        if self.__knx_proj_contents.schema_version < ETS_5_7_SCHEMA_VERSION:
            links = self.__get_links_from_schema_1x(com_object)
        else:
            links = self.__get_links_from_schema_2x(com_object)

        if not links:
            return None

        return ComObjectInstanceRef(
            identifier=com_object.get("Id"),
            ref_id=com_object.get("RefId"),  # type: ignore[arg-type]
            text=com_object.get("Text"),
            function_text=com_object.get("FunctionText"),
            read_flag=parse_xml_flag(com_object.get("ReadFlag")),
            write_flag=parse_xml_flag(com_object.get("WriteFlag")),
            communication_flag=parse_xml_flag(com_object.get("CommunicationFlag")),
            transmit_flag=parse_xml_flag(com_object.get("TransmitFlag")),
            update_flag=parse_xml_flag(com_object.get("UpdateFlag")),
            read_on_init_flag=parse_xml_flag(com_object.get("ReadOnInitFlag")),
            datapoint_types=parse_dpt_types(com_object.get("DatapointType")),
            description=com_object.get("Description"),
            channel=com_object.get("ChannelId"),
            links=links,
        )

    def _create_module_instance(
        self,
        module_instance_elem: ElementTree.Element,
    ) -> ModuleInstance | None:
        """Create ComObjectInstanceRef."""
        module_arguments = [
            ModuleInstanceArgument(
                ref_id=arg.get("RefId"),  # type: ignore[arg-type]
                value=arg.get("Value"),  # type: ignore[arg-type]
            )
            for arg in module_instance_elem.findall("{*}Arguments/{*}Argument")
        ]
        return ModuleInstance(
            identifier=module_instance_elem.get("Id"),  # type: ignore[arg-type]
            ref_id=module_instance_elem.get("RefId"),  # type: ignore[arg-type]
            arguments=module_arguments,
        )


class _LocationLoader:
    """Load location infos from KNX XML."""

    def __init__(
        self,
        knx_proj_contents: KNXProjContents,
        knx_master_data: KNXMasterData,
        devices: list[DeviceInstance],
    ) -> None:
        """Initialize the LocationLoader."""
        self.knx_master_data = knx_master_data
        self._element_name = (
            "BuildingPart" if knx_proj_contents.is_ets4_project() else "Space"
        )
        self.devices: dict[str, str] = {
            device.identifier: device.individual_address for device in devices
        }

    def load(
        self, location_element: ElementTree.Element, functions: list[XMLFunction]
    ) -> list[XMLSpace]:
        """Load Location mappings."""
        return [
            self.parse_space(space, functions)
            for space in location_element.findall(f"{{*}}{self._element_name}")
        ]

    def parse_space(
        self, node: ElementTree.Element, functions: list[XMLFunction]
    ) -> XMLSpace:
        """Parse a space from the document."""
        usage_id = node.get("Usage")
        usage_text = (
            self.knx_master_data.get_space_usage_name(usage_id) if usage_id else ""
        )
        project_uid = node.get("Puid")
        space: XMLSpace = XMLSpace(
            identifier=node.get("Id"),  # type: ignore[arg-type]
            name=node.get("Name"),  # type: ignore[arg-type]
            space_type=SpaceType(node.get("Type")),
            usage_id=usage_id,
            usage_text=usage_text,
            number=node.get("Number", ""),
            description=node.get("Description", ""),
            project_uid=int(project_uid) if project_uid else None,
            spaces=[],
            devices=[],
            functions=[],
        )

        for sub_node in node:
            if sub_node.tag.endswith(self._element_name):
                # recursively call parse space since this can be nested for an unbound time in the XSD
                space.spaces.append(self.parse_space(sub_node, functions))
            elif sub_node.tag.endswith("DeviceInstanceRef"):
                if individual_address := self.devices.get(sub_node.get("RefId", "")):
                    space.devices.append(individual_address)
            elif sub_node.tag.endswith("Function"):
                function = self.parse_functions(sub_node)
                function.space_id = space.identifier
                functions.append(function)
                space.functions.append(function.identifier)

        return space

    def parse_functions(self, node: ElementTree.Element) -> XMLFunction:
        """Parse a functions from the document."""
        identifier = node.get("Id", "").split("_", 1)[1]
        project_uid = node.get("Puid")
        function_type = node.get("Type", "")

        functions: XMLFunction = XMLFunction(
            identifier=identifier,
            name=node.get("Name"),  # type: ignore[arg-type]
            function_type=function_type,
            project_uid=int(project_uid) if project_uid else None,
            group_addresses=[],
            usage_text="",
            space_id="",
        )

        for sub_node in node:
            if sub_node.tag.endswith("GroupAddressRef"):
                project_uid = sub_node.get("Puid")
                ref_id = sub_node.get("RefId", "").split("_", 1)[1]

                group_address_ref: XMLGroupAddressRef = XMLGroupAddressRef(
                    ref_id=ref_id,
                    identifier=sub_node.get("Id"),  # type: ignore[arg-type]
                    name=sub_node.get("Name"),  # type: ignore[arg-type]
                    role=sub_node.get("Role", ""),
                    project_uid=int(project_uid) if project_uid else None,
                    address="",
                )
                functions.group_addresses.append(group_address_ref)

        return functions


def load_project_info(tree: ElementTree.ElementTree) -> XMLProjectInformation:
    """Load project information."""
    knx_root = tree.getroot()
    _namespace_match = re.match(r"{.+\/project\/(.+)}", knx_root.tag)
    schema_version = _namespace_match.group(1) if _namespace_match else ""
    created_by = knx_root.get("CreatedBy", "")
    tool_version = knx_root.get("ToolVersion", "")

    try:
        project_node: ElementTree.Element = tree.find("{*}Project")  # type: ignore[assignment]
        identifier = project_node.get("Id", "")
        info_node: ElementTree.Element = project_node.find("{*}ProjectInformation")  # type: ignore[assignment]
        return XMLProjectInformation(
            project_id=identifier,
            name=info_node.get("Name", ""),
            last_modified=info_node.get("LastModified"),
            group_address_style=GroupAddressStyle(info_node.get("GroupAddressStyle")),
            guid=info_node.get("Guid"),  # type: ignore[arg-type]
            created_by=created_by,
            schema_version=schema_version,
            tool_version=tool_version,
        )
    except AttributeError:
        # Project or ProjectInformation tag not found
        return XMLProjectInformation(
            created_by=created_by,
            schema_version=schema_version,
            tool_version=tool_version,
        )
