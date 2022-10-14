"""Project file loader."""
from __future__ import annotations

from xml.etree import ElementTree

from xknxproject.models import (
    ComObjectInstanceRef,
    DeviceInstance,
    SpaceType,
    XMLArea,
    XMLGroupAddress,
    XMLLine,
    XMLSpace,
)
from xknxproject.util import parse_dpt_types, parse_xml_flag
from xknxproject.zip import KNXProjContents


class ProjectLoader:
    """Load Project file."""

    @staticmethod
    def load(
        knx_proj_contents: KNXProjContents,
    ) -> tuple[
        list[XMLGroupAddress], list[XMLArea], list[DeviceInstance], list[XMLSpace]
    ]:
        """Load topology mappings."""
        areas: list[XMLArea] = []
        devices: list[DeviceInstance] = []
        group_address_list: list[XMLGroupAddress] = []
        spaces: list[XMLSpace] = []

        with knx_proj_contents.open_project_0() as project_file:
            tree = ElementTree.parse(project_file)
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
                    _TopologyLoader.load(topology_element=topology_element),
                )
            for area in areas:
                for line in area.lines:
                    devices.extend(line.devices)
            for location_element in tree.findall(
                "{*}Project/{*}Installations/{*}Installation/{*}Locations"
            ):
                spaces.extend(
                    _LocationLoader(devices).load(location_element=location_element),
                )

        return group_address_list, areas, devices, spaces


class _GroupAddressLoader:
    """Load GroupAddress info from KNX XML."""

    @staticmethod
    def load(group_address_element: ElementTree.Element) -> XMLGroupAddress:
        """Load GroupAddress mappings."""

        return XMLGroupAddress(
            name=group_address_element.get("Name", ""),
            identifier=group_address_element.get("Id", ""),
            address=group_address_element.get("Address", ""),
            dpt_type=group_address_element.get("DatapointType"),
            description=group_address_element.get("Description", ""),
        )


class _TopologyLoader:
    """Load topology from KNX XML."""

    @staticmethod
    def load(topology_element: ElementTree.Element) -> list[XMLArea]:
        """Load topology mappings."""
        areas: list[XMLArea] = []

        for area in topology_element.findall("{*}Area"):
            areas.append(_TopologyLoader._create_area(area))

        return areas

    @staticmethod
    def _create_area(area_element: ElementTree.Element) -> XMLArea:
        """Create an Area."""
        address: int = int(area_element.get("Address", ""))
        name: str = area_element.get("Name", "")
        description: str | None = area_element.get("Description")
        area: XMLArea = XMLArea(address, name, description, [])

        for line_element in area_element:
            area.lines.append(_TopologyLoader._create_line(line_element, area))

        return area

    @staticmethod
    def _create_line(line_element: ElementTree.Element, area: XMLArea) -> XMLLine:
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
            if device := _TopologyLoader._create_device(device_element, line):
                line.devices.append(device)

        return line

    @staticmethod
    def _create_device(
        device_element: ElementTree.Element, line: XMLLine
    ) -> DeviceInstance | None:
        """Create device."""
        identifier: str = device_element.get("Id", "")
        address: str | None = device_element.get("Address")

        #  devices like power supplies do usually not have an IA.
        if address is None:
            return None

        name: str = device_element.get("Name", "")
        last_modified: str = device_element.get("LastModified", "")
        _product_ref_parts = device_element.get("ProductRefId", "").split("_")
        hardware_ref = _product_ref_parts[0] + "_" + _product_ref_parts[1]
        hardware_program_ref = device_element.get("Hardware2ProgramRefId", "")
        device: DeviceInstance = DeviceInstance(
            identifier=identifier,
            address=address,
            name=name,
            last_modified=last_modified,
            hardware_ref=hardware_ref,
            hardware_program_ref=hardware_program_ref,
            line=line,
            manufacturer=_product_ref_parts[0],
        )

        for sub_node in device_element:
            if sub_node.tag.endswith("AdditionalAddresses"):
                for address_node in sub_node:
                    if _address := address_node.get("Address"):
                        device.additional_addresses.append(_address)
            if sub_node.tag.endswith("ComObjectInstanceRefs"):
                for com_object in sub_node:
                    if instance := _TopologyLoader._create_com_object_instance(
                        com_object
                    ):
                        device.com_object_instance_refs.append(instance)

        return device

    @staticmethod
    def _create_com_object_instance(
        com_object: ElementTree.Element,
    ) -> ComObjectInstanceRef | None:
        """Create ComObjectInstanceRef."""
        if not (links := com_object.get("Links")):
            return None

        _dpt_type = com_object.get("DatapointType")
        datapoint_type = parse_dpt_types(_dpt_type.split(" ")) if _dpt_type else None

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
            datapoint_type=datapoint_type,
            description=com_object.get("Description"),
            links=links.split(" "),
        )


class _LocationLoader:
    """Load location infos from KNX XML."""

    def __init__(self, devices: list[DeviceInstance]):
        """Initialize the LocationLoader."""
        self.devices: dict[str, str] = {
            device.identifier: device.individual_address for device in devices
        }

    def load(self, location_element: ElementTree.Element) -> list[XMLSpace]:
        """Load Location mappings."""
        return [
            self.parse_space(space) for space in location_element.findall("{*}Space")
        ]

    def parse_space(self, node: ElementTree.Element) -> XMLSpace:
        """Parse a space from the document."""
        name: str = node.get("Name", "")
        space_type = SpaceType(node.get("Type"))
        space: XMLSpace = XMLSpace([], space_type, name, [])

        for sub_node in node:
            if sub_node.tag.endswith("Space"):
                # recursively call parse space since this can be nested for an unbound time in the XSD
                space.spaces.append(self.parse_space(sub_node))
            elif sub_node.tag.endswith("DeviceInstanceRef"):
                if individual_address := self.devices.get(sub_node.get("RefId", "")):
                    space.devices.append(individual_address)

        return space
