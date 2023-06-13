"""Project file loader."""
from __future__ import annotations

import re
from xml.etree import ElementTree

from xknxproject.models import (
    ComObjectInstanceRef,
    DeviceInstance,
    SpaceType,
    XMLArea,
    XMLGroupAddress,
    XMLLine,
    XMLProjectInformation,
    XMLSpace,
)
from xknxproject.util import (
    get_dpt_type,
    is_ets4_project,
    parse_dpt_types,
    parse_xml_flag,
)
from xknxproject.zip import KNXProjContents


class ProjectLoader:
    """Load Project file."""

    @staticmethod
    def load(
        knx_proj_contents: KNXProjContents,
        space_usage_names: dict[str, str],
    ) -> tuple[
        list[XMLGroupAddress],
        list[XMLArea],
        list[DeviceInstance],
        list[XMLSpace],
        XMLProjectInformation,
    ]:
        """Load topology mappings."""
        areas: list[XMLArea] = []
        devices: list[DeviceInstance] = []
        group_address_list: list[XMLGroupAddress] = []
        spaces: list[XMLSpace] = []

        with knx_proj_contents.open_project_0() as project_0_file:
            tree = ElementTree.parse(project_0_file)
            for ga_element in tree.findall(
                # `//` to ignore <GroupRange> tags to support different GA level formats
                "{*}Project/{*}Installations/{*}Installation/{*}GroupAddresses//{*}GroupAddress"
            ):
                group_address_list.append(
                    _GroupAddressLoader.load(group_address_element=ga_element),
                )
            for topology_element in tree.findall(
                "{*}Project/{*}Installations/{*}Installation/{*}Topology"
            ):
                areas.extend(
                    _TopologyLoader(knx_proj_contents).load(
                        topology_element=topology_element
                    ),
                )
            for area in areas:
                for line in area.lines:
                    devices.extend(line.devices)
            for location_element in tree.findall(
                "{*}Project/{*}Installations/{*}Installation/{*}Locations"
            ):
                spaces.extend(
                    _LocationLoader(devices, space_usage_names).load(
                        location_element=location_element
                    ),
                )

        with knx_proj_contents.open_project_meta() as project_file:
            tree = ElementTree.parse(project_file)
            project_info = load_project_info(tree)

        return group_address_list, areas, devices, spaces, project_info


class _GroupAddressLoader:
    """Load GroupAddress info from KNX XML."""

    @staticmethod
    def load(group_address_element: ElementTree.Element) -> XMLGroupAddress:
        """Load GroupAddress mappings."""
        project_uid = group_address_element.get("Puid")
        return XMLGroupAddress(
            name=group_address_element.get("Name", ""),
            identifier=group_address_element.get("Id", ""),
            address=group_address_element.get("Address", ""),
            project_uid=int(project_uid) if project_uid else None,
            description=group_address_element.get("Description", ""),
            dpt=get_dpt_type(group_address_element.get("DatapointType")),
        )


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
        device: DeviceInstance = DeviceInstance(
            identifier=device_element.get("Id", ""),
            address=address,
            project_uid=int(project_uid) if project_uid else None,
            name=device_element.get("Name", ""),
            description=device_element.get("Description", ""),
            last_modified=device_element.get("LastModified", ""),
            product_ref=product_ref,
            hardware_program_ref=device_element.get("Hardware2ProgramRefId", ""),
            line=line,
            manufacturer=product_ref.split("_", 1)[0],
        )

        for sub_node in device_element:
            if sub_node.tag.endswith("AdditionalAddresses"):
                for address_node in sub_node:
                    if _address := address_node.get("Address"):
                        device.additional_addresses.append(_address)
            if sub_node.tag.endswith("ComObjectInstanceRefs"):
                for com_object in sub_node:
                    if instance := self._create_com_object_instance(com_object):
                        device.com_object_instance_refs.append(instance)

        return device

    @staticmethod
    def __get_links_from_ets4(com_object: ElementTree.Element) -> str | None:
        # Check if "Connectors" is available. This will always fail for ETS5/6
        if (connectors := com_object.find("{*}Connectors")) is None:
            return None

        # Send GA is the primary GA, Receive GA are additional group addresses
        ga_list = connectors.findall("{*}Send") + connectors.findall("{*}Receive")

        # Remove the project ID from GA
        links = [ga.get("GroupAddressRefId", "").split("_")[1] for ga in ga_list]

        # Return a list of GA as string as for "Links" in ETS5/6
        return " ".join(links)

    def _create_com_object_instance(
        self,
        com_object: ElementTree.Element,
    ) -> ComObjectInstanceRef | None:
        """Create ComObjectInstanceRef."""

        if is_ets4_project(self.__knx_proj_contents.schema_version):
            links = self.__get_links_from_ets4(com_object)
        else:
            links = com_object.get("Links")

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
            links=links.split(" "),
        )


class _LocationLoader:
    """Load location infos from KNX XML."""

    def __init__(
        self,
        devices: list[DeviceInstance],
        space_usage_names: dict[str, str],
    ):
        """Initialize the LocationLoader."""
        self.devices: dict[str, str] = {
            device.identifier: device.individual_address for device in devices
        }
        self.space_usage_names = space_usage_names

    def load(self, location_element: ElementTree.Element) -> list[XMLSpace]:
        """Load Location mappings."""
        return [
            self.parse_space(space) for space in location_element.findall("{*}Space")
        ]

    def parse_space(self, node: ElementTree.Element) -> XMLSpace:
        """Parse a space from the document."""
        usage_id = node.get("Usage")
        usage_text = self.space_usage_names.get(usage_id, "") if usage_id else ""
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
        )

        for sub_node in node:
            if sub_node.tag.endswith("Space"):
                # recursively call parse space since this can be nested for an unbound time in the XSD
                space.spaces.append(self.parse_space(sub_node))
            elif sub_node.tag.endswith("DeviceInstanceRef"):
                if individual_address := self.devices.get(sub_node.get("RefId", "")):
                    space.devices.append(individual_address)

        return space


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
            group_address_style=info_node.get("GroupAddressStyle"),  # type: ignore[arg-type]
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
